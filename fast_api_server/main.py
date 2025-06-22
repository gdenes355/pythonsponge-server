from fastapi import FastAPI
from shared.server_settings import server_settings

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}


if __name__ == "__main__":
    if server_settings.is_debug:
        print("Running in development mode")
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        print("Running fastapi in prod locally is not allowed")
