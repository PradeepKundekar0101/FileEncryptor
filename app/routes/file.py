import datetime
from fastapi import APIRouter, File, HTTPException, UploadFile, Depends, logger
from app.database import db
from app.routes.dependencies import get_db
from bson import ObjectId
from azure.storage.blob import BlobServiceClient,generate_blob_sas,BlobSasPermissions
from app.config.settings import AZURE_STORAGE_CONNECTION_STRING

router = APIRouter()

blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_name = "aarontestblobstorage"

@router.post("/upload/")
async def upload_file(file: UploadFile = File(...), db = Depends(get_db)):
    try:
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
            expiry=datetime.datetime.now() + datetime.timedelta(hours=1)
        )

        blob_url_with_sas = f"{blob_client.url}?{sas_token}"

        db.files.insert_one({
            "_id": file_id,
            "filename": file.filename,
            "content_type": file.content_type,
            "blob_url": blob_url_with_sas
        })
        
        return {"file_id": file_id, "blob_url": blob_url_with_sas}

    except Exception as e:
        print(f"Error during file upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred during file upload: {str(e)}")
