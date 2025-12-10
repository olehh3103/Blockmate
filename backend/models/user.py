from typing import Dict, List, Any, Optional
from datetime import datetime
from bson import ObjectId


class UserModel:
    def __init__(self, db):
        self.collection = db.users
    
    async def create_user(self, user_data: Dict[str, Any]) -> str:
        """Створення нового користувача"""
        user_data["created_at"] = datetime.utcnow()
        result = await self.collection.insert_one(user_data)
        return str(result.inserted_id)
    
    async def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Отримання користувача за telegram_id"""
        user = await self.collection.find_one({"telegram_id": telegram_id})
        if user and "_id" in user:
            user["_id"] = str(user["_id"])
        return user
    
    async def update_user(self, telegram_id: int, update_data: Dict[str, Any]) -> bool:
        """Оновлення даних користувача"""
        update_data["updated_at"] = datetime.utcnow()
        result = await self.collection.update_one(
            {"telegram_id": telegram_id},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    async def add_to_history(self, telegram_id: int, history_item: Dict[str, Any]) -> bool:
        """Додавання запису в історію"""
        if "timestamp" not in history_item:
            history_item["timestamp"] = datetime.utcnow()
        
        result = await self.collection.update_one(
            {"telegram_id": telegram_id},
            {"$push": {"history": history_item}}
        )
        return result.modified_count > 0


class GoalModel:
    def __init__(self, db):
        self.collection = db.goals
    
    async def create_goal(self, goal_data: Dict[str, Any]) -> str:
        """Створення нової цілі"""
        goal_data["created_at"] = datetime.utcnow()
        result = await self.collection.insert_one(goal_data)
        return str(result.inserted_id)


class ValidationHistory:
    def __init__(self, db):
        self.collection = db.validation_history
    
    async def create_history_entry(self, entry_data: Dict[str, Any]) -> str:
        """Створення запису в історії валідацій"""
        entry_data["created_at"] = datetime.utcnow()
        result = await self.collection.insert_one(entry_data)
        return str(result.inserted_id)


