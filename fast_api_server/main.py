from shared.server_settings import server_settings

from fastapi import FastAPI, Depends

from fast_api_server.auth import get_current_user, register_auth_exception_handlers, auth_router
from fast_api_server.admin import admin_router
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    root_path="/api",
)

register_auth_exception_handlers(app)
app.include_router(auth_router)
app.include_router(admin_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[server_settings.site_url if not server_settings.is_debug else 'http://localhost:3000'],
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'OPTIONS', 'PATCH', 'DELETE'], 
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/protected")
def protected(user=Depends(get_current_user)):
    return {"hello": user}
    


if __name__ == "__main__":
    if server_settings.is_debug:
        print("Running in development mode")
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=5001)
    else:
        print("Running fastapi in prod locally is not allowed")
