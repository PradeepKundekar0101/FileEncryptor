from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class FileInfo(BaseModel):
    fileName: str
    fileUrl: str
    fileId: str

class Group(BaseModel):
    name: str
    files: List[FileInfo]
    user: str
    zipURL: str
    pcName: Optional[str] = None
    location: Optional[str] = None
    date: Optional[datetime] = None
    time: Optional[str] = None