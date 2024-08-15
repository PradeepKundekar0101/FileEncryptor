import os
from dotenv import load_dotenv
load_dotenv()
MONGO_URI = os.environ["MONGO_URI"]
AZURE_STORAGE_CONNECTION_STRING = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
MONGO_DB_NAME = os.environ["MONGO_NAME"]
EMAIL_HOST_USER = os.environ["EMAIL_HOST_USER"]
EMAIL_HOST_PASSWORD = os.environ["EMAIL_HOST_PASSWORD"]