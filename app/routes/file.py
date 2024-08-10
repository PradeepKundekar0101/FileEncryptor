import os
import datetime
import zipfile
from fastapi import APIRouter, File, HTTPException, UploadFile, Depends, Query
from typing import Any
from app.database import db
from app.routes.dependencies import get_db
from bson import ObjectId
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from app.config.settings import AZURE_STORAGE_CONNECTION_STRING
from app.core.security import encrypt_file
from app.services.exe_generator import generate_exe
from cryptography.fernet import Fernet

router = APIRouter()

blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_name = "aarontestblobstorage"

@router.post("/upload_and_encrypt/")
async def upload_and_encrypt_file(
    file: UploadFile = File(...), 
    username: str = Query(...), 
    db: Any = Depends(get_db)
):
    try:
        os.makedirs('temp', exist_ok=True)
        file_id = str(ObjectId())
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_id)
        
        file_contents = await file.read()
        blob_client.upload_blob(file_contents, blob_type="BlockBlob")

        sas_token = generate_blob_sas(
            account_name=blob_service_client.account_name,
            container_name=container_name,
            blob_name=file_id,
            account_key=blob_service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        )

        blob_url_with_sas = f"{blob_client.url}?{sas_token}"

        key = Fernet.generate_key()
        encrypted_data = encrypt_file(file_contents, key)
        
        encrypted_file_path = os.path.join('temp', f"{file_id}_encrypted")
        with open(encrypted_file_path, "wb") as encrypted_file:
            encrypted_file.write(encrypted_data)

        zip_path = os.path.join('temp', f"{file_id}.zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.write(encrypted_file_path, os.path.basename(encrypted_file_path))

        exe_path = generate_exe(key, zip_path, username)

        db.files.insert_one({
            "_id": file_id,
            "filename": file.filename,
            "content_type": file.content_type,
            "blob_url": blob_url_with_sas,
            "encrypted_file_path": encrypted_file_path,
            "zip_path": zip_path,
            "exe_path": exe_path
        })

        db.users.update_one(
            {"username": username},
            {"$push": {"encryptions": {
                "id": file_id,
                "file_ids": [file_id],
                "key": key.decode(),
                "exe_path": exe_path
            }}},
            upsert=True
        )
        
        os.remove(encrypted_file_path)
        os.remove(zip_path)

        return {
            "file_id": file_id, 
            "blob_url": blob_url_with_sas,
            "exe_path": exe_path
        }

    except Exception as e:
        print(f"Error during file upload and encryption: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred during file upload and encryption: {str(e)}")