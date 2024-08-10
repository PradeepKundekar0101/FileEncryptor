from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from app.models.schemas import EncryptionRequest
from app.database import db
from app.routes.dependencies import get_db
from app.core.security import encrypt_files
from app.services.exe_generator import generate_exe
from bson import ObjectId

router = APIRouter()

@router.post("/encrypt/")
async def encrypt_files_endpoint(request: EncryptionRequest, db = Depends(get_db)):
    encrypted_file_paths, key = encrypt_files(request.file_ids, db)
    
    zip_path = f"temp/{str(ObjectId())}.zip"
    exe_path = generate_exe(key, zip_path, request.username)
    
    encryption_id = str(ObjectId())
    db.users.update_one(
        {"username": request.username},
        {"$push": {"encryptions": {
            "id": encryption_id,
            "file_ids": request.file_ids,
            "key": key.decode(),
            "exe_path": exe_path
        }}},
        upsert=True
    )
    
    return FileResponse(exe_path, filename="decryptor.exe")