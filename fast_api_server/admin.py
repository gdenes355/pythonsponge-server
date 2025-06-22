from fastapi import APIRouter, Depends, HTTPException

from shared.db import database
from shared.server_settings import server_settings
from fast_api_server.auth import get_current_user

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
def test_role(teacher_user=Depends(get_teacher_user)):
    return {'res': 'succ'}
