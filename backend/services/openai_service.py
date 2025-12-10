import openai
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv
import json

load_dotenv()

logger = logging.getLogger(__name__)


class OpenAIValidationService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        openai.api_key = api_key
        self.client = openai.OpenAI(api_key=api_key)
    
    async def validate_request(
        self,
        request_text: str,
        user_context: Dict[str, Any],
        duration_minutes: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Валідація запиту користувача через OpenAI
        
        Повертає:
        {
            "decision": "allow" | "deny",
            "message": "текст відповіді",
            "alternative": "альтернативна пропозиція (опціонально)",
            "timestamp": datetime
        }
        """
        
        # Формуємо промпт для OpenAI
        goals_text = "\n".join([f"- {goal}" for goal in user_context.get("goals", [])])
        allowed_text = "\n".join([f"- {use}" for use in user_context.get("allowed_usecases", [])])
        forbidden_text = "\n".join([f"- {use}" for use in user_context.get("forbidden_usecases", [])])
        
        duration_info = f" на {duration_minutes} хвилин" if duration_minutes else ""
        
        system_prompt = """Ти допомагаєш користувачам боротись з залежністю від соціальних мереж. 
Твоя задача - проаналізувати запит користувача на використання соцмережі та дати обґрунтовану відповідь.

Відповідай українською мовою, бути дружнім та підтримуючим.
Якщо запит узгоджений з цілями користувача - дозволи його.
Якщо це виглядає як відволікання - запропонуй альтернативу.

Формат відповіді (JSON):
{
    "decision": "allow" або "deny",
    "message": "персональне повідомлення користувачу",
    "alternative": "альтернативна пропозиція (тільки якщо decision=deny)"
}"""

        user_prompt = f"""Користувач хоче: {request_text}{duration_info}

Цілі користувача:
{goals_text if goals_text else "Не вказано"}

Дозволені сценарії використання:
{allowed_text if allowed_text else "Не вказано"}

Заборонені сценарії використання:
{forbidden_text if forbidden_text else "Не вказано"}

Проаналізуй запит та дай відповідь у форматі JSON."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Додаємо timestamp
            result["timestamp"] = datetime.utcnow().isoformat()
            
            # Перевірка формату
            if result["decision"] not in ["allow", "deny"]:
                result["decision"] = "deny"
            
            return result
            
        except Exception as e:
            # У випадку помилки повертаємо консервативну відповідь
            logger.error(f"Error validating request with OpenAI: {e}", exc_info=True)
            return {
                "decision": "deny",
                "message": "Вибач, зараз не можу обробити запит. Спробуй пізніше.",
                "alternative": "Зроби коротку паузу без телефону.",
                "timestamp": datetime.utcnow().isoformat()
            }

