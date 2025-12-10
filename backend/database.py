from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

_client: Optional[AsyncIOMotorClient] = None
_db = None


async def get_database():
    """Отримання підключення до бази даних"""
    global _db
    if _db is None:
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        db_name = os.getenv("MONGODB_DB_NAME", "blockmate")
        
        client = AsyncIOMotorClient(mongodb_url)
        _db = client[db_name]
    
    return _db


async def close_database():
    """Закриття підключення до бази даних"""
    global _client
    if _client:
        _client.close()


