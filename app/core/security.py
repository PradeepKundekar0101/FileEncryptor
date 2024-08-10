from cryptography.fernet import Fernet
import os
import zipfile
from fastapi import HTTPException
from bson import ObjectId
def encrypt_files(file_ids, db):
    key = Fernet.generate_key()
    fernet = Fernet(key)
    
    encrypted_file_paths = []
    for file_id in file_ids:
        file_info = db.files.find_one({"_id": file_id})
        if not file_info:
            raise HTTPException(status_code=404, detail=f"File {file_id} not found")
        
        with open(f"temp/{file_id}", "rb") as file:
            original_data = file.read()
        
        encrypted_data = fernet.encrypt(original_data)
        encrypted_file_path = f"temp/{file_id}_encrypted"
        with open(encrypted_file_path, "wb") as encrypted_file:
            encrypted_file.write(encrypted_data)
        
        encrypted_file_paths.append(encrypted_file_path)
    
    zip_path = f"temp/{str(ObjectId())}.zip"
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file_path in encrypted_file_paths:
            zipf.write(file_path, os.path.basename(file_path))
    
    for file_path in encrypted_file_paths:
        os.remove(file_path)
    
    return encrypted_file_paths, key