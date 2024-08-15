import os
import datetime
import zipfile
from fastapi import APIRouter, File, HTTPException, UploadFile, Depends, Query
from typing import Any, List
from pydantic import BaseModel
from app.models.location import LocationData
from app.models.notification import Notification
from app.routes.dependencies import get_db
from bson import ObjectId
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from azure.core.exceptions import ResourceNotFoundError
from app.config.settings import AZURE_STORAGE_CONNECTION_STRING
from app.core.security import encrypt_files
from app.services.auth import get_current_user
from app.services.email import send_email
from app.services.exe_generator import generate_exe
from app.models.group import Group, FileInfo

router = APIRouter()

blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_name = "test"

try:
    container_client = blob_service_client.get_container_client(container_name)
    container_client.get_container_properties()
except ResourceNotFoundError:
    container_client = blob_service_client.create_container(container_name)


@router.post("/upload_and_encrypt/")
async def upload_and_encrypt_files(
    files: List[UploadFile] = File(...),
    group_name: str = Query(...),
    current_user: dict = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    try:
        os.makedirs('temp', exist_ok=True)
        file_infos = []
        
        # Upload files to Azure Blob Storage
        for file in files:
            try:
                file_id = str(ObjectId())
                blob_client = container_client.get_blob_client(blob=file_id)
                
                file_contents = await file.read()
                if not file_contents:
                    raise ValueError(f"File {file.filename} is empty")
                
                blob_client.upload_blob(file_contents, blob_type="BlockBlob")
                
                # Generate SAS token for the file
                file_sas_token = generate_blob_sas(
                    account_name=blob_service_client.account_name,
                    container_name=container_name,
                    blob_name=file_id,
                    account_key=blob_service_client.credential.account_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=datetime.datetime.utcnow() + datetime.timedelta(hours=1)
                )
                file_url_with_sas = f"{blob_client.url}?{file_sas_token}"
                file_infos.append(FileInfo(fileName=file.filename, fileUrl=file_url_with_sas,fileId=file_id))
                
                # Save file info to database, including the original file extension
                file_extension = os.path.splitext(file.filename)[1]
                db.files.insert_one({
                    "_id": file_id,
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "username": current_user['email'],
                    "original_extension": file_extension
                })
            except Exception as e:
                print(f"Error processing file {file.filename}: {str(e)}")
                raise HTTPException(status_code=400, detail=f"Error processing file {file.filename}: {str(e)}")

        # Encrypt files
        try:
            print("file_infos")
            print(file_infos)
            encrypted_file_paths, key, file_extensions = encrypt_files([f.fileId for f in file_infos], db)
        except Exception as e:
            print(f"Error during file encryption: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error during file encryption: {str(e)}")

       # Generate executables
        try:
            exe_paths = generate_exe(key, encrypted_file_paths, file_extensions, current_user['email'], group_name)
        except Exception as e:
            print(f"Error generating executables: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error generating executables: {str(e)}")

        # Create and upload ZIP file
        try:
            zip_id = str(ObjectId())
            zip_path = f"temp/{zip_id}.zip"
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for file_path in encrypted_file_paths:
                    zipf.write(file_path, os.path.basename(file_path))
                for exe_path in exe_paths:
                    zipf.write(exe_path, os.path.basename(exe_path))


            zip_blob_client = container_client.get_blob_client(blob=zip_id)
            with open(zip_path, "rb") as zip_file:
                zip_blob_client.upload_blob(zip_file.read(), blob_type="BlockBlob")

            zip_sas_token = generate_blob_sas(
                account_name=blob_service_client.account_name,
                container_name=container_name,
                blob_name=zip_id,
                account_key=blob_service_client.credential.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            )

            zip_url_with_sas = f"{zip_blob_client.url}?{zip_sas_token}"
        except Exception as e:
            print(f"Error creating or uploading ZIP file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error creating or uploading ZIP file: {str(e)}")

        try:
            new_group = Group(
                name=group_name,
                files=file_infos,
                user=current_user['email'],
                zipURL=zip_url_with_sas
            )
            
            inserted_id = db.groups.insert_one(new_group.dict()).inserted_id
        except Exception as e:
            print(f"Error creating group in database: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error creating group in database: {str(e)}")

        # Clean up temporary files
        for file_path in encrypted_file_paths:
            if os.path.exists(file_path):
                os.remove(file_path)
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(exe_path):
            os.remove(exe_path)

        return {
            "message": "Files uploaded and encrypted successfully",
            "group_id": str(inserted_id),
            "zip_url": zip_url_with_sas
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Unexpected error during file upload and encryption: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during file upload and encryption: {str(e)}")

@router.get("/get_download_url/{group_id}")
async def get_download_url(group_id: str, current_user: dict = Depends(get_current_user), db: Any = Depends(get_db)):
    group = db.groups.find_one({"_id": ObjectId(group_id), "user": current_user['email']})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    return {"download_url": group["zipURL"]}

@router.get("/user_groups")
async def get_user_groups(current_user: dict = Depends(get_current_user), db: Any = Depends(get_db)):
    try:
        groups = list(db.groups.find({"user": current_user['email']}))
        return {"groups": [Group(**group).dict() for group in groups]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sendLocation")
async def send_location(data: LocationData, db: Any = Depends(get_db)):
    try:
        now = datetime.datetime.now()
        print(data)
        
        # Update the group information
        group = db.groups.find_one_and_update(
            {"name": data.group_name},
            {"$set": {
                "pcName": data.pc_name,
                "location": data.location,
                "date": data.date,
                "time": data.time
            }},
            return_document=True
        )
        
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Create a notification
        notification = Notification(
            title=f"New location data for group {data.group_name}",
            isRead=False,
            files=group['files'],
            user=group['user'],
            zipURL=group['zipURL'],
            pcName=data.pc_name,
            location=data.location,
            date=data.date,
            time=data.time
        )
        
        # Insert the notification into the database
        db.notifications.insert_one(notification.dict())
        
        # Send an email to the user
        email_content = f"""
        New location data received for group {data.group_name}:
        PC Name: {data.pc_name}
        Location: {data.location}
        Date: {data.date}
        Time: {data.time}
        """
        send_email(to_email=group['user'], subject="New Location Data", content=email_content)
        
        print(f"Received location data: {data.json()}")
        return {"message": "Location data received, group updated, and notification sent successfully"}
    except Exception as e:
        print(f"Error processing location data: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while processing location data")

@router.get("/user_groups/")
async def get_user_groups(current_user: dict = Depends(get_current_user), db: Any = Depends(get_db)):
    """
    Returns a list of groups associated with the current user's email.
    """
    try:
        # Find all groups associated with the user's email
        groups = list(db.groups.find({"user": current_user['email']}))
        
        # Convert each group document into a dictionary using the Group model and return the list of groups
        return {"groups": [Group(**group).dict() for group in groups]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
