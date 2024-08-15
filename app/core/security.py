from cryptography.fernet import Fernet
import os
from fastapi import HTTPException
from azure.storage.blob import BlobServiceClient
from app.config.settings import AZURE_STORAGE_CONNECTION_STRING

blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_name = "test"
def encrypt_files(file_ids, db):
    key = Fernet.generate_key()
    fernet = Fernet(key)
    
    encrypted_file_paths = []
    file_extensions = {}  
    print("IDS")
    print(file_ids)
    for file_id in file_ids:
        file_info = db.files.find_one({"_id": file_id})
        if not file_info:
            raise HTTPException(status_code=404, detail=f"File {file_id} not found")
        
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_id)
        original_data = blob_client.download_blob().readall()
        
        encrypted_data = fernet.encrypt(original_data)
        encrypted_file_path = f"temp/{file_id}_encrypted"
        
        # Save the original file extension
        file_extensions[file_id] = os.path.splitext(file_info["filename"])[1]

        with open(encrypted_file_path, "wb") as encrypted_file:
            encrypted_file.write(encrypted_data)
        
        encrypted_file_paths.append(encrypted_file_path)
    
    return encrypted_file_paths, key, file_extensions

