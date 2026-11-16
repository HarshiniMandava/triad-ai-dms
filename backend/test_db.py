import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(
    Path(__file__).resolve().parent.parent / ".env"
)

mongo_uri = os.getenv("MONGO_URI")

if not mongo_uri:
    raise ValueError("MONGO_URI is missing in .env file")

try:
    client = MongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=10000
    )

    client.admin.command("ping")

    db = client[os.getenv("DB_NAME", "triad_ai_dms")]

    print("MongoDB connected successfully!")
    print("Database:", db.name)

except Exception as e:
    print("MongoDB connection failed!")
    print("Error:", e)
