from pydantic import BaseModel
from typing import List

class EncryptionRequest(BaseModel):
    username: str
    file_ids: List[str]