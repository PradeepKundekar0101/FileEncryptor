from fastapi import FastAPI
from app.routes import file, encryption

app = FastAPI()

app.include_router(file.router)
app.include_router(encryption.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)