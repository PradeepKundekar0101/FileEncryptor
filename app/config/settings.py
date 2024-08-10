import os
from dotenv import load_dotenv
load_dotenv()

MONGO_URI = os.environ["MONGO_URI"]
AZURE_STORAGE_CONNECTION_STRING = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
MONGO_DB_NAME = os.environ["MONGO_NAME"]