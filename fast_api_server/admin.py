from fastapi import APIRouter, Depends, HTTPException

from shared.db import database
from shared.server_settings import server_settings
from fast_api_server.auth import get_current_user
import pathlib
from typing import Optional, Union, List
from pydantic import BaseModel, Field

admin_router = APIRouter(
    prefix='/admin'
)

db: database.Database = database.get_database()

def get_teacher_user(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=403, detail='you need to be logged in')
    if user.lower() not in server_settings.admin_accounts:
        raise HTTPException(status_code=403, detail='you need to be an admin')
    return user

@admin_router.get('/token-test')
async def test_role(teacher_user=Depends(get_teacher_user)):
    return {'res': 'succ'}

## --------
## classes
## --------
@admin_router.get('/classes')
async def get_classes(active: Optional[bool] = None, teacher_user=Depends(get_teacher_user)):
    return {
        'res': 'succ',
        'data': await db.get_classes(active),
    }

class ClassCreationDto(BaseModel):
    class_name: str = Field(..., alias="class")
    class Config:
        allow_population_by_field_name = True
@admin_router.post('/classes')
async def add_class(body: ClassCreationDto):
    await db.add_class(body.class_name)
    return {'res': 'succ'}

class ClassPatchDto(BaseModel):
    active: bool
@admin_router.patch('/classes/{class_name}')
async def patch_class(class_name: str, body: ClassPatchDto):
    await db.patch_class_active(class_name=class_name, is_active=body.active)
    return {'res': 'succ'}

@admin_router.delete('/classes/{class_name}')
async def patch_class(class_name: str):
    await db.delete_class(class_name=class_name)
    return {'res': 'succ'}

# class-student mapping
class AddStudentDto(BaseModel):
    user: Union[str, List[str]]
@admin_router.post('/classes/{class_name}/students')
async def add_student_to_class(class_name: str, body: AddStudentDto):
    students = [body.user] if type(body.user) == str else body.user
    await db.add_students_to_class(class_name=class_name, students=students)
    return {'res': 'succ'}

@admin_router.delete('/classes/{class_name}/students/{student}')
async def remove_student_from_class(class_name: str, student: str):
    await db.delete_student_from_class(class_name=class_name, student=student)
    return {'res': 'succ'}

# class-book mapping
class AddBookDto(BaseModel):
    book: str
    enabled: bool = True
@admin_router.post('/classes/{class_name}/books')
async def add_book_to_class(class_name: str, body: AddBookDto):
    await db.add_book_to_class(class_name=class_name, book=body.book, is_enabled=body.enabled)
    return {'res': 'succ'}

# results
@admin_router.get('/classes/{class_name}/books/{book:path}/results')
async def get_class_results_for_book(class_name: str, book: str):
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
@admin_router.patch('/students/{student}/books/{book:path}/results/{challenge:path}/comment')
async def patch_result_with_comment(student: str, book: str, challenge: str, body: PatchResultDto):
    await db.add_result_comment(user=student, book=book, challenge=challenge, comment=body.comment)
    return {'res': 'succ'}

    


## --------
## books
## --------
@admin_router.get('/books')
async def get_books():
    book_paths = ['/'.join(b.parts) for b in pathlib.Path('./books').rglob('book.json')]
    return {
        'res': 'succ',
        'data': book_paths,
    }
    
## --------
## name cache
## --------
@admin_router.get('/cache/name')
async def get_name_cache_size():
    return {
        'res': 'succ',
        'data': {'cache-size': db.get_user_name_cache_size()},
    }

@admin_router.post('/cache/name')
async def refresh_cached_names():
    await db.refresh_user_name_cache()
    return {
        'res': 'succ',
        'data': {'cache-size': db.get_user_name_cache_size()},
    }


