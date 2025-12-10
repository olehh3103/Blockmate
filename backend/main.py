from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv

from backend.database import get_database
from backend.services.openai_service import OpenAIValidationService
from backend.models.user import UserModel, GoalModel, ValidationHistory

import uvicorn

load_dotenv()

app = FastAPI(title="BlockMate API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for API
class RegisterUserRequest(BaseModel):
    telegram_id: int
    username: Optional[str] = None


class SetGoalsRequest(BaseModel):
    telegram_id: int
    goals: List[str]
    allowed_usecases: List[str]
    forbidden_usecases: List[str]


class ValidateRequest(BaseModel):
    telegram_id: int
    request_text: str
    duration_minutes: Optional[int] = None


class ValidateResponse(BaseModel):
    decision: str  # "allow" or "deny"
    message: str
    alternative: Optional[str] = None
    reminder_time: Optional[int] = None  # minutes from now


@app.get("/")
async def root():
    return {"message": "BlockMate API", "status": "running"}


@app.post("/register_user")
async def register_user(request: RegisterUserRequest):
    """Реєстрація нового користувача"""
    db = await get_database()
    user_model = UserModel(db)
    
    user = await user_model.get_user(request.telegram_id)
    if user:
        return {"message": "User already exists", "user_id": request.telegram_id}
    
    new_user = {
        "telegram_id": request.telegram_id,
        "username": request.username,
        "goals": [],
        "allowed_usecases": [],
        "forbidden_usecases": [],
        "history": []
    }
    
    result = await user_model.create_user(new_user)
    return {"message": "User registered successfully", "user_id": request.telegram_id}


@app.post("/set_goals")
async def set_goals(request: SetGoalsRequest):
    """Встановлення цілей користувача"""
    db = await get_database()
    user_model = UserModel(db)
    
    user = await user_model.get_user(request.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = {
        "goals": request.goals,
        "allowed_usecases": request.allowed_usecases,
        "forbidden_usecases": request.forbidden_usecases
    }
    
    await user_model.update_user(request.telegram_id, update_data)
    return {"message": "Goals updated successfully"}


@app.post("/validate", response_model=ValidateResponse)
async def validate_request(request: ValidateRequest):
    """Валідація запиту користувача через OpenAI"""
    db = await get_database()
    user_model = UserModel(db)
    
    user = await user_model.get_user(request.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please register first.")
    
    # Отримуємо контекст користувача
    user_context = {
        "goals": user.get("goals", []),
        "allowed_usecases": user.get("allowed_usecases", []),
        "forbidden_usecases": user.get("forbidden_usecases", []),
    }
    
    # Викликаємо OpenAI для валідації
    openai_service = OpenAIValidationService()
    validation_result = await openai_service.validate_request(
        request_text=request.request_text,
        user_context=user_context,
        duration_minutes=request.duration_minutes
    )
    
    # Зберігаємо в історію
    history_item = {
        "timestamp": validation_result.get("timestamp"),
        "request": request.request_text,
        "decision": validation_result["decision"],
        "alternative": validation_result.get("alternative"),
        "duration_minutes": request.duration_minutes
    }
    
    await user_model.add_to_history(request.telegram_id, history_item)
    
    return ValidateResponse(
        decision=validation_result["decision"],
        message=validation_result["message"],
        alternative=validation_result.get("alternative"),
        reminder_time=request.duration_minutes if validation_result["decision"] == "allow" and request.duration_minutes else None
    )


@app.get("/user/{telegram_id}")
async def get_user(telegram_id: int):
    """Отримання інформації про користувача"""
    db = await get_database()
    user_model = UserModel(db)
    
    user = await user_model.get_user(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)


