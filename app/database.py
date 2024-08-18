from pymongo import MongoClient
from app.config.settings import MONGO_URI,MONGO_DB_NAME
import certifi
client = MongoClient(MONGO_URI,tlsCAFile=certifi.where()
)
db = client[MONGO_DB_NAME]