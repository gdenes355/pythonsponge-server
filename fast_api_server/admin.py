import json
import uuid
import zipfile
import io
import pathlib
import os
import shutil
from collections import deque
from datetime import datetime, timezone
from typing import List, Optional, Union
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from shared.db import database
from shared.server_settings import server_settings
from fast_api_server.auth import get_current_user, is_admin
from fast_api_server.utils.excel_export_utils import write_results_to_xlsx

admin_router = APIRouter(
    prefix='/admin'
)

db: database.Database = database.get_database()


def get_teacher_user(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=403, detail='you need to be logged in')
    if not is_admin(user):
        raise HTTPException(status_code=403, detail='you need to be an admin')
    return user

@admin_router.get('/token-test/', tags=['Misc'], summary='Test token')
async def test_role(teacher_user=Depends(get_teacher_user)):
    """Test if the token is a valid admin token"""
    return {
        'res': 'succ',
    }


## --------
## classes
## --------
@admin_router.get('/classes', tags=['Class management'], summary='Retrieve all classes')
async def get_classes(active: Optional[bool] = None, teacher_user=Depends(get_teacher_user)):
    """Retrieve all classes and their students"""
    return {
        'res': 'succ',
        'data': await db.get_classes(active),
    }

class ClassCreationDto(BaseModel):
    class_name: str = Field(..., alias="class")
    class Config:
        validate_by_name = True
@admin_router.post('/classes', tags=['Class management'], summary='Create class')
async def add_class(body: ClassCreationDto, teacher_user=Depends(get_teacher_user)):
    """Create a new class. New class defaults to being active with no students or books."""
    await db.add_class(body.class_name)
    return {'res': 'succ'}

class ClassPatchDto(BaseModel):
    active: bool
@admin_router.patch('/classes/{class_name}', tags=['Class management'], summary='Update class')
async def patch_class(class_name: str, body: ClassPatchDto, teacher_user=Depends(get_teacher_user)):
    """Update a class's active status"""
    await db.patch_class_active(class_name=class_name, is_active=body.active)
    return {'res': 'succ'}

@admin_router.delete('/classes/{class_name}', tags=['Class management'], summary='Delete class')
async def patch_class(class_name: str, teacher_user=Depends(get_teacher_user)):
    """Delete a class (but keep results and students)"""
    await db.delete_class(class_name=class_name)
    return {'res': 'succ'}

# class-student mapping
class AddStudentDto(BaseModel):
    user: Union[str, List[str]]
@admin_router.post('/classes/{class_name}/students', tags=['Class management'], summary='Add student')
async def add_student_to_class(class_name: str, body: AddStudentDto, teacher_user=Depends(get_teacher_user)):
    """Add a student or multiple students to a class"""
    students = [body.user] if type(body.user) == str else body.user
    await db.add_students_to_class(class_name=class_name, students=students)
    return {'res': 'succ'}

@admin_router.delete('/classes/{class_name}/students/{student}', tags=['Class management'], summary='Delete student')
async def remove_student_from_class(class_name: str, student: str, teacher_user=Depends(get_teacher_user)):
    """Remove a student from a class (keep results etc.)"""
    await db.delete_student_from_class(class_name=class_name, student=student)
    return {'res': 'succ'}

# class-book mapping
class AddBookDto(BaseModel):
    book: str
    enabled: bool = True
@admin_router.post('/classes/{class_name}/books', tags=['Class management'], summary='Add book')
async def add_book_to_class(class_name: str, body: AddBookDto, teacher_user=Depends(get_teacher_user)):
    """Idempontent operation to update the association between class and book, and to set to either enabled or disabled"""
    await db.add_book_to_class(class_name=class_name, book=body.book, is_enabled=body.enabled)
    return {'res': 'succ'}

# results
@admin_router.get('/classes/{class_name}/books/{book:path}/results', tags=['Results management'], summary='Get results')
async def get_class_results_for_book(class_name: str, book: str, teacher_user=Depends(get_teacher_user)):
    """Retrieve all student progress for a book in a class"""
    klass = await db.get_class(class_name=class_name)
    if not klass:
        raise HTTPException(status_code=404, detail='class not found')
    if not book or book not in klass.books+klass.disabled_books:
        raise HTTPException(status_code=404, detail='book not found in class')
    
    return {
        'res': 'succ', 
        'data': await db.get_results_for_users(book=book, users=klass.students)
    }

class PatchResultDto(BaseModel):
    comment: str = ""
@admin_router.post('/students/{student}/books/{book:path}/results/{challenge:path}/comment', tags=['Results management'], summary='Amend results')
async def patch_result_with_comment(student: str, book: str, challenge: str, body: PatchResultDto, teacher_user=Depends(get_teacher_user)):
    """Add a comment to a student's results as feedback"""
    await db.add_result_comment(user=student, book=book, challenge=challenge, comment=body.comment)
    return {'res': 'succ'}

    
## --------
## name cache
## --------
@admin_router.get('/cache/name', tags=['Name cache'], summary='Retrieve local cache info')
async def get_name_cache_size(teacher_user=Depends(get_teacher_user)):
    """Retrieve the size of the local student name cache"""
    return {
        'res': 'succ',
        'data': {'cache-size': db.get_user_name_cache_size()},
    }

@admin_router.post('/cache/name', tags=['Name cache'], summary='Invalidate local cache')
async def refresh_cached_names(teacher_user=Depends(get_teacher_user)):
    """Invalidate the local cache and refetch from remote db"""
    await db.refresh_user_name_cache()
    return {
        'res': 'succ',
        'data': {'cache-size': db.get_user_name_cache_size()},
    }

@admin_router.delete('/cache/name', tags=['Name cache'], summary='Invalidate local cache')
async def refresh_cached_names(teacher_user=Depends(get_teacher_user)):
    """Invalidate the local cache and refetch from remote db"""
    await db.delete_user_names()
    return {
        'res': 'succ',
        'data': {'cache-size': db.get_user_name_cache_size()},
    }

@admin_router.get('/classes/{class_name}/results/export', tags=['Results management'], summary='Export grade book')
async def export_results(class_name: str, teacher_user=Depends(get_teacher_user)):
    """Export test case progress for all students for all books in a class"""
    klass = await db.get_class(class_name=class_name)
    if not klass:
        raise HTTPException(status_code=404, detail="class not found")
    
    results_buffer = await write_results_to_xlsx(klass=klass)
    results_buffer.seek(0)
    headers = {
        "Content-Disposition": f'attachment; filename="{klass.name}.xlsx"',
    }
    return StreamingResponse(
        results_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )


## --------
## books
## --------
def _get_node_count_in_book(book: dict) -> int:
    count = 1
    q = deque([book])
    while q:
        node = q.popleft()
        children = node.get('children', [])
        if children:
            q.extend(children)
            count += len(children)
    return count

def _get_node_ids_in_book(book: dict) -> List[str]:
    ids = set()
    q = deque([book])
    while q:
        node = q.popleft()
        ids.add(node.get('id'))
        children = node.get('children', [])
        if children:
            q.extend(children)
    return list(ids)

def _sanitise_book_path(path: str, allow_new: bool = False) -> str:
    if path.startswith(server_settings.site_url):
        path = path[len(server_settings.site_url):]
    if ".." in path or "~" in path or not path.endswith('book.json'):
        raise HTTPException(status_code=400, detail='invalid path')
    if path.startswith('books/'):
        local_path = f'./{path}'
    elif path.startswith('./books/'):
        local_path = path
    else:
        raise HTTPException(status_code=400, detail='invalid path')
    
    if not allow_new and not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail='book not found')

    return local_path

def _back_up_book(path: str):
    local_path = _sanitise_book_path(path)
    folder_containing_book_json = pathlib.Path(os.path.dirname(local_path))
    path_uri_encoded = quote(path, safe="")
    file_path = f"./books-bck/{path_uri_encoded}--{int(datetime.now().timestamp())}.zip"
    with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in folder_containing_book_json.rglob("*"):  # recursively include all files/subfolders
            if file_path.is_file():
                # Arcname ensures relative paths inside the zip
                zipf.write(file_path, arcname=file_path.relative_to(folder_containing_book_json))
    return file_path

def _wipe_book(path: str, leave_blank_folder: bool = False):
    local_path = _sanitise_book_path(path)
    folder_containing_book_json = pathlib.Path(os.path.dirname(local_path))
    shutil.rmtree(folder_containing_book_json)
    os.makedirs(folder_containing_book_json)

def _restore_book_from_zip(local_path: str, zip_file):   
    folder_containing_book_json = pathlib.Path(os.path.dirname(local_path))
    with zipfile.ZipFile(zip_file, 'r') as zipf:
        zipf.extractall(folder_containing_book_json)

def create_example_book(local_path: str):
    folder_containing_book_json = pathlib.Path(os.path.dirname(local_path))
    # ensure folders exist all the way down
    folder_containing_book_json.mkdir(parents=True, exist_ok=True)
    with open(folder_containing_book_json / 'book.json', 'w') as f:
        f.write(json.dumps({
            'name': 'New book',
            'id': str(uuid.uuid4()),
            'children': [{
                'id': str(uuid.uuid4()),
                'name': 'Challenge 1',
                'guide': 'c01.md',
                'py': 'c01.py',
            }],
        }))
    with open(folder_containing_book_json /  'c01.md', 'w') as f:
        f.write('## Challenge 1\nAdd task here. Any valid markdown is fine.')
    with open(folder_containing_book_json / 'c01.py', 'w') as f:
        f.write('print("Hello, world!")')


@admin_router.get('/books', tags=['Misc'], summary='Retrieve list of book URLs')
async def get_books(teacher_user=Depends(get_teacher_user)):
    """Retrieve list of book URLs"""
    book_paths = ['/'.join(b.parts) for b in pathlib.Path('./books').rglob('book.json')]
    return {
        'res': 'succ',
        'data': book_paths,
    }

@admin_router.get('/books/{path:path}/history', tags=['Misc'], summary='Retrieve book versions on the server')
async def get_book_history(path: str, teacher_user=Depends(get_teacher_user)):
    """Retrieve book versions on the server"""
    local_path = _sanitise_book_path(path)

    # load the book.json file
    book_name = None
    with open(local_path, 'r') as f:
        book = json.load(f)
        book_name = book.get('name')

    history = []

    # for history, start with the current revision
    date_modified = datetime.fromtimestamp(os.path.getmtime(local_path), timezone.utc)
    history.append({
        'date': date_modified,
        'version': 'current',
        'nodeCount': _get_node_count_in_book(book),
        'nodeIds': _get_node_ids_in_book(book),
    })

    # then get the previous revisions
    backup_folder = pathlib.Path('./books-bck')
    path_uri_encoded = quote(path, safe="")
    zips = backup_folder.glob(f'{path_uri_encoded}-*.zip')
    zips = sorted(zips, key=lambda x: int(x.stem.split('--')[1].split('.')[0]), reverse=True)
    for zip in zips:
        timestamp = int(zip.stem.split('--')[1].split('.')[0])
        history.append({
            'date': datetime.fromtimestamp(timestamp, timezone.utc),
            'version': str(timestamp)   ,
            'nodeCount': _get_node_count_in_book(book),
        })

    # return the data
    return {
        'res': 'succ',
        'name': book_name,
        'history': history,
    }

@admin_router.post('/books/{path:path}/history/{version}/download', tags=['Misc'], summary='Download current book version as zip')
async def download_current_book_version(path: str, version: str, teacher_user=Depends(get_teacher_user)):
    local_path = _sanitise_book_path(path)
    folder_containing_book_json = pathlib.Path(os.path.dirname(local_path))

    if version == 'current':
        """Download current book version as zip"""
        filename = f'{folder_containing_book_json.name}--current.zip'
        zip_buffer = io.BytesIO()
        # Create the in-memory ZIP
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in folder_containing_book_json.rglob("*"):  # recursively include all files/subfolders
                if file_path.is_file():
                    # Arcname ensures relative paths inside the zip
                    zipf.write(file_path, arcname=file_path.relative_to(folder_containing_book_json))

        # Move the buffer position back to the start
        zip_buffer.seek(0)
        
    else:
        filename = f'{folder_containing_book_json.name}--{version}.zip'
        path_uri_encoded = quote(path, safe="")
        backup_folder = pathlib.Path('./books-bck')
        zip_path = backup_folder / f'{path_uri_encoded}--{version}.zip'
        if not zip_path.exists():
            raise HTTPException(status_code=404, detail='zip file not found')
        zip_buffer = zip_path.open('rb')
        zip_buffer.seek(0)

    # Return as streaming response
    return StreamingResponse(
        zip_buffer,
        media_type="application/x-zip-compressed",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        },
    )
    
@admin_router.post('/books/{path:path}/history/new', tags=['Misc'], summary='Create a new book version')
async def create_new_book_version(path: str, file: UploadFile, teacher_user=Depends(get_teacher_user)):
    _back_up_book(path)
    local_path = _sanitise_book_path(path)
    _wipe_book(path, leave_blank_folder=True)
    _restore_book_from_zip(local_path, file.file)
    return {'res': 'succ'}

@admin_router.post('/books/{path:path}', tags=['Misc'], summary='Create a new book')
async def create_new_book(path: str, teacher_user=Depends(get_teacher_user)):
    local_path = _sanitise_book_path(path, allow_new=True)
    if os.path.exists(local_path):
        raise HTTPException(status_code=400, detail='book already exists')
    create_example_book(local_path)
    return {'res': 'succ'}

@admin_router.delete('/books/{path:path}', tags=['Misc'], summary='Delete a book')
async def delete_book(path: str, teacher_user=Depends(get_teacher_user)):
    _back_up_book(path)
    local_path = _sanitise_book_path(path)
    if not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail='book not found')
    _wipe_book(path)
    return {'res': 'succ'}
