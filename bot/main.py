import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

import httpx

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Змінні оточення
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

# Глобальний scheduler для нагадувань
scheduler = AsyncIOScheduler()
scheduler.start()


class BlockMateBot:
    def __init__(self):
        self.backend_url = BACKEND_URL
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def register_user(self, telegram_id: int, username: str = None) -> bool:
        """Реєстрація користувача в системі"""
        try:
            response = await self.client.post(
                f"{self.backend_url}/register_user",
                json={
                    "telegram_id": telegram_id,
                    "username": username
                }
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return False
    
    async def set_goals(
        self,
        telegram_id: int,
        goals: list,
        allowed_usecases: list,
        forbidden_usecases: list
    ) -> bool:
        """Встановлення цілей користувача"""
        try:
            response = await self.client.post(
                f"{self.backend_url}/set_goals",
                json={
                    "telegram_id": telegram_id,
                    "goals": goals,
                    "allowed_usecases": allowed_usecases,
                    "forbidden_usecases": forbidden_usecases
                }
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error setting goals: {e}")
            return False
    
    async def validate_request(
        self,
        telegram_id: int,
        request_text: str,
        duration_minutes: int = None
    ) -> Dict:
        """Валідація запиту користувача"""
        try:
            response = await self.client.post(
                f"{self.backend_url}/validate",
                json={
                    "telegram_id": telegram_id,
                    "request_text": request_text,
                    "duration_minutes": duration_minutes
                }
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": response.text}
        except Exception as e:
            logger.error(f"Error validating request: {e}")
            return {"error": str(e)}


bot_instance = BlockMateBot()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /start"""
    user = update.effective_user
    telegram_id = user.id
    username = user.username
    
    # Реєструємо користувача
    await bot_instance.register_user(telegram_id, username)
    
    welcome_message = f"""
Привіт, {user.first_name}! 👋

Я BlockMate - твій помічник у боротьбі з залежністю від соціальних мереж.

📋 Спочатку потрібно налаштувати профіль:
1. Вкажи свої цілі (/goals)
2. Опиши дозволені та заборонені сценарії використання

Після цього ти зможеш використовувати Shortcut на iPhone для валідації кожного відкриття соцмереж.

Команди:
/goals - налаштувати цілі
/validate - перевірити запит
/help - допомога
"""
    
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /help"""
    help_text = """
📚 Довідка BlockMate:

/goals - Налаштувати цілі та правила
/validate - Перевірити запит на використання соцмережі

💡 Як працює валідація:
1. Створи Shortcut на iPhone, який відкриває цього бота
2. Коли хочеш відкрити соцмережу, напиши боту
3. AI проаналізує твій запит та дасть рекомендацію

Приклад запиту:
"Хочу відкрити YouTube на 20 хв, щоб подивитися щось поки їм"
"""
    await update.message.reply_text(help_text)


async def set_goals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /goals - налаштування цілей"""
    user_id = update.effective_user.id
    
    message_text = """
🎯 Налаштування цілей

Будь ласка, відповідай на питання. Відправ мені повідомлення у такому форматі:

**Цілі:** вивчити Python, розвивати блог, не зливати час після 22:00
**Дозволені:** навчання, робота, фітнес, інспірація
**Заборонені:** скрол, перегляд чужих новин, бездумні відео

Або відправляй по одному пункту, і я збережу їх.
"""
    
    await update.message.reply_text(message_text, parse_mode='Markdown')
    
    # Зберігаємо стан для парсингу відповіді
    context.user_data['setting_goals'] = True


async def validate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /validate"""
    message = """
✅ Валідація запиту

Опиши, що ти хочеш зробити з соцмережею.

Приклад:
"Хочу відкрити Instagram на 10 хвилин, щоб перевірити повідомлення"
"Хочу подивитися YouTube під час обіду"

Я проаналізую твій запит та дам рекомендацію!
"""
    await update.message.reply_text(message)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник звичайних повідомлень"""
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Перевіряємо, чи користувач налаштовує цілі
    if context.user_data.get('setting_goals'):
        await process_goals_setup(update, context, message_text)
        return
    
    # Інакше - це запит на валідацію
    await process_validation_request(update, context, message_text)


async def process_goals_setup(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Обробка налаштування цілей"""
    user_id = update.effective_user.id
    
    # Простий парсинг формату
    goals = []
    allowed = []
    forbidden = []
    
    lines = text.split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if 'цілі' in line.lower() or 'goals' in line.lower():
            current_section = 'goals'
            # Витягуємо список після ":"
            if ':' in line:
                items = line.split(':', 1)[1].strip()
                goals.extend([g.strip() for g in items.split(',')])
        elif 'дозволені' in line.lower() or 'allowed' in line.lower():
            current_section = 'allowed'
            if ':' in line:
                items = line.split(':', 1)[1].strip()
                allowed.extend([a.strip() for a in items.split(',')])
        elif 'заборонені' in line.lower() or 'forbidden' in line.lower():
            current_section = 'forbidden'
            if ':' in line:
                items = line.split(':', 1)[1].strip()
                forbidden.extend([f.strip() for f in items.split(',')])
        else:
            if current_section == 'goals':
                goals.append(line)
            elif current_section == 'allowed':
                allowed.append(line)
            elif current_section == 'forbidden':
                forbidden.append(line)
    
    # Якщо не знайдено структурований формат, намагаємося витягти списки
    if not goals and not allowed and not forbidden:
        # Спрощений парсинг - шукаємо ключові слова
        if any(word in text.lower() for word in ['цілі', 'goals', 'хочу']):
            goals = [text]
        else:
            # Припускаємо, що це список цілей через кому
            items = [item.strip() for item in text.split(',')]
            if len(items) > 1:
                goals = items
            else:
                goals = [text]
    
    # Зберігаємо цілі
    success = await bot_instance.set_goals(user_id, goals, allowed, forbidden)
    
    if success:
        await update.message.reply_text(
            f"✅ Цілі збережено!\n\n"
            f"🎯 Цілі: {', '.join(goals) if goals else 'Не вказано'}\n"
            f"✅ Дозволені: {', '.join(allowed) if allowed else 'Не вказано'}\n"
            f"❌ Заборонені: {', '.join(forbidden) if forbidden else 'Не вказано'}\n\n"
            f"Тепер ти можеш використовувати /validate для перевірки запитів."
        )
        context.user_data['setting_goals'] = False
    else:
        await update.message.reply_text(
            "❌ Помилка при збереженні цілей. Спробуй ще раз або звернись до адміністратора."
        )


async def process_validation_request(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Обробка запиту на валідацію"""
    user_id = update.effective_user.id
    
    # Показуємо індикатор набору тексту
    await update.message.reply_chat_action("typing")
    
    # Витягуємо тривалість (якщо вказана)
    duration_minutes = None
    import re
    duration_match = re.search(r'(\d+)\s*(хв|мин|min|m|хвилин|минут)', text, re.IGNORECASE)
    if duration_match:
        duration_minutes = int(duration_match.group(1))
    
    # Викликаємо API для валідації
    result = await bot_instance.validate_request(user_id, text, duration_minutes)
    
    if "error" in result:
        await update.message.reply_text(
            f"❌ Помилка: {result['error']}\n\n"
            "Переконайся, що ти зареєстрований (/start) та налаштував цілі (/goals)."
        )
        return
    
    decision = result.get("decision", "deny")
    message = result.get("message", "")
    alternative = result.get("alternative")
    reminder_time = result.get("reminder_time")
    
    # Формуємо відповідь
    response_text = message
    
    if alternative:
        response_text += f"\n\n💡 Альтернатива: {alternative}"
    
    # Якщо дозволено та вказана тривалість - налаштовуємо нагадування
    if decision == "allow" and reminder_time:
        await schedule_reminder(user_id, reminder_time, update.effective_chat.id)
        response_text += f"\n\n⏰ Нагадування встановлено на {reminder_time} хвилин."
    
    await update.message.reply_text(response_text)


async def send_reminder(chat_id: int, user_id: int):
    """Надсилання нагадування користувачу"""
    try:
        from telegram import Bot
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        bot = Bot(token=bot_token)
        
        await bot.send_message(
            chat_id=chat_id,
            text="⏰ Час вийшов! Запланований час використання соцмережі минув.\n\n"
                 "Рекомендую закрити додаток та повернутись до своїх цілей. 💪"
        )
    except Exception as e:
        logger.error(f"Error sending reminder: {e}")


async def schedule_reminder(user_id: int, minutes: int, chat_id: int):
    """Планування нагадування"""
    reminder_time = datetime.utcnow() + timedelta(minutes=minutes)
    
    scheduler.add_job(
        send_reminder,
        trigger=DateTrigger(run_date=reminder_time),
        args=[chat_id, user_id],
        id=f"reminder_{user_id}_{datetime.utcnow().timestamp()}"
    )


def main():
    """Запуск бота"""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Реєстрація обробників
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("goals", set_goals_command))
    application.add_handler(CommandHandler("validate", validate_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()


