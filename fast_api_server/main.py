from datetime import datetime, timedelta, timezone
import os
from typing import List

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from fast_api_server.admin import admin_router
from fast_api_server.auth import (
    auth_router,
    get_current_user,
    get_current_user_roles,
    register_auth_exception_handlers,
    is_admin
)
from fast_api_server.utils.open_api_utils import customise_open_api

from shared.ai.client_factory import get_llm_client
from shared.ai.clients.llm_client import LlmPriceTier
from shared.ai.prompts import student_helper
from shared.db import database
from shared.books_repository import BooksRepository
from shared.server_settings import server_settings

app = FastAPI()

app.openapi_tags = [
    {"name": "Teacher", "description": "Administrative routes"},
    {"name": "Students", "description": "Student endpoints"},
]

register_auth_exception_handlers(app)

api_router = APIRouter(prefix='/api')
api_router.include_router(auth_router)
api_router.include_router(admin_router)

db: database.Database = database.get_database()
book_repo = BooksRepository()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[server_settings.site_url if not server_settings.is_debug else 'http://localhost:3000'],
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'OPTIONS', 'PATCH', 'DELETE'], 
    allow_headers=["*"],
)

@app.get("/books/{path:path}")
async def get_book_file(path: str, user=Depends(get_current_user)):
    """Serve book contents"""
    if "book.json" in path and not is_admin(user):
        allowed_books = await db.get_student_books(user)
        if f"books/{path}" not in allowed_books:
            raise HTTPException(status_code=403, detail="You do not have access to this book")
    if "solutions/" in path and not is_admin(user):
        raise HTTPException(status_code=403, detail="You do not have access to solution files as a student")
        
    if server_settings.is_debug:
        full_path = os.path.join("books", path)
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="Book not found")
        return FileResponse(full_path)
    else:
        return Response(
            content="",
            media_type="application/octet-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Redirect": f"/books-internal/{path}"
            }
        )
    
@api_router.get('/results/', tags=["Student endpoints"], summary="Retrieve student progress")
async def get_student_results(book: str, user=Depends(get_current_user)):
    """Retrieve all test passes/fails for the student for a given book"""
    return {
        'res': 'ok',
        'data': await db.get_results_for_user(book=book, user=user)
    }

class StudentResultUpdate(BaseModel):
   book: str
   id: str
   outcome: bool = False
   is_long: bool = False
   code: str = ''
@api_router.post('/results/', tags=["Student endpoints"], summary="Save student progress")
async def post_result(body: StudentResultUpdate, user=Depends(get_current_user)):
    """Save student progress to the database."""
    await db.save_result(
        book=body.book, 
        user=user, 
        challenge_id=body.id, 
        outcome=body.outcome, 
        code=body.code if body.is_long else body.code[:4000]
    )
    return {'res': 'ok'}


@api_router.get('/student-dashboard', tags=["Student endpoints"], summary="Student entrypoint (list books)")
async def get_student_fashboard(user=Depends(get_current_user)):
    """Retrieve the list of books available to the student"""
    books = await db.get_student_books(user)
    book_titles = book_repo.get_local_book_titles(books)
    return {
        'res': 'succ',
        'books': [{
            'path': book,
            'title': book_titles.get(book)
        } for book in books]
    }

class GetAiHintDto(BaseModel):
    bookPath: str
    challengeId: str
    md: str
    consoleText: str
    code: str
@api_router.post('/ai/hints', tags=["Student endpoints"], summary="Get AI hint")
async def get_ai_hint(body: GetAiHintDto, user=Depends(get_current_user), roles: List[str] = Depends(get_current_user_roles)):
    if not 'ai-enabled' in roles:
        raise HTTPException(status_code=403, detail="You do not have access to AI help")
    now = datetime.now(timezone.utc)
    when = await db.upsert_ai_help_use(user)
    if when and now - when < timedelta(seconds=15):
        return {'res': 'ok', 'hint': "I'm on a short break to give you a chance to think. You can ask me again a bit later."}

    if not body.bookPath or not body.challengeId:
        raise HTTPException(status_code=400, detail="You must provide a valid book path and challenge ID")
    
    if not body.code:
        return {'res': 'ok', 'text': text, 'hint': "Please provide your code so I can help you." }

    if not body.md:
        raise HTTPException(status_code=400, detail="You must provide a valid challenge description")
    
    system_prompt = student_helper.get_system_prompt()
    tools = student_helper.get_function_declarations()
    prompt = student_helper.get_prompt(body.md, body.code, body.consoleText)
    text, tool_calls = get_llm_client(LlmPriceTier.LITE).generate_text(
        system_prompt=system_prompt, 
        prompt=prompt, 
        function_declarations=tools,
        force_function_calls=True,
    )
    hint = tool_calls.get('send_hint', {}).get('hint', '') or 'Check your code and the challenge description once more very carefully. Can you spot what went wrong?'
    await db.record_ai_help_with_challenge(user, body.bookPath, body.challengeId)
    return {'res': 'ok', 'text': text, 'hint': hint }

app.include_router(api_router)

customise_open_api(app)  # just for redoc



if __name__ == "__main__":
    if server_settings.is_debug:
        print("Running in development mode")
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=5001, reload=True, reload_excludes=["books-bck/**", "books/**"])
    else:
        print("Running fastapi in prod locally is not allowed")
