from pydantic import BaseModel

class LocationData(BaseModel):
    group_name: str
    pc_name: str
    location: str
    ip: str
    date: str
    time: str