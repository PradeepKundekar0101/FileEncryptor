from cryptography.fernet import Fernet
import os
import zipfile
from fastapi import HTTPException
from bson import ObjectId
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from app.config.settings import AZURE_STORAGE_CONNECTION_STRING

blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_name = "test"

def encrypt_files(file_ids, db):
    key = Fernet.generate_key()
    fernet = Fernet(key)
    
    encrypted_file_paths = []
    file_extensions = {}  # Store file extensions

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

def decrypt_files(key: bytes, encrypted_file_paths: list, db):
    fernet = Fernet(key)
    decrypted_file_paths = []

    for encrypted_file_path in encrypted_file_paths:
        file_id = os.path.basename(encrypted_file_path).replace("_encrypted", "")
        file_info = db.files.find_one({"_id": file_id})

        if not file_info:
            raise HTTPException(status_code=404, detail=f"File {file_id} not found")

        original_extension = file_info["original_extension"]
        decrypted_filename = f"{file_id}{original_extension}"
        decrypted_file_path = os.path.join(os.path.dirname(encrypted_file_path), decrypted_filename)
        
        with open(encrypted_file_path, "rb") as encrypted_file:
            encrypted_data = encrypted_file.read()

        decrypted_data = fernet.decrypt(encrypted_data)

        with open(decrypted_file_path, "wb") as decrypted_file:
            decrypted_file.write(decrypted_data)

        decrypted_file_paths.append(decrypted_file_path)

    return decrypted_file_paths
