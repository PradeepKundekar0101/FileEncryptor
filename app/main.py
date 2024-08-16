from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import auth, file,notification

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

app.include_router(file.router)
app.include_router(auth.router)
app.include_router(notification.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
