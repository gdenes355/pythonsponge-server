import pathlib
from typing import List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from shared.db import database
from shared.server_settings import server_settings
from fast_api_server.auth import get_current_user
from fast_api_server.utils.excel_export_utils import write_results_to_xlsx

admin_router = APIRouter(
    prefix='/admin'
)

db: database.Database = database.get_database()

def is_admin(user: str) -> bool:
    return user.lower() in server_settings.admin_accounts

def get_teacher_user(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=403, detail='you need to be logged in')
    if not is_admin(user):
        raise HTTPException(status_code=403, detail='you need to be an admin')
    return user

@admin_router.get('/token-test', tags=['Misc'], summary='Test token')
async def test_role(teacher_user=Depends(get_teacher_user)):
    """Test if the token is a valid admin token"""
    return {'res': 'succ'}

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
## books
## --------
@admin_router.get('/books', tags=['Misc'], summary='Retrieve list of book URLs')
async def get_books(teacher_user=Depends(get_teacher_user)):
    """Retrieve list of book URLs"""
    book_paths = ['/'.join(b.parts) for b in pathlib.Path('./books').rglob('book.json')]
    return {
        'res': 'succ',
        'data': book_paths,
    }
    
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
