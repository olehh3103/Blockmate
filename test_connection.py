#!/usr/bin/env python3
"""
Скрипт для тестування підключення до MongoDB та Backend API
"""
import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
import httpx
from dotenv import load_dotenv

load_dotenv()


async def test_mongodb():
    """Тест підключення до MongoDB"""
    print("🔍 Тестування підключення до MongoDB...")
    try:
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        client = AsyncIOMotorClient(mongodb_url)
        # Перевіряємо підключення
        await client.admin.command('ping')
        print("✅ MongoDB: Підключення успішне!")
        client.close()
        return True
    except Exception as e:
        print(f"❌ MongoDB: Помилка підключення - {e}")
        return False


async def test_backend():
    """Тест підключення до Backend API"""
    print("\n🔍 Тестування підключення до Backend API...")
    try:
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{backend_url}/")
            if response.status_code == 200:
                print(f"✅ Backend API: Підключення успішне! {response.json()}")
                return True
            else:
                print(f"❌ Backend API: Неочікуваний статус код - {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Backend API: Помилка підключення - {e}")
        return False


def check_env_vars():
    """Перевірка наявності необхідних змінних оточення"""
    print("\n🔍 Перевірка змінних оточення...")
    required_vars = ["TELEGRAM_BOT_TOKEN", "OPENAI_API_KEY"]
    missing = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
            print(f"⚠️  {var}: не встановлено")
        else:
            # Показуємо тільки перші символи для безпеки
            value = os.getenv(var)
            masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
            print(f"✅ {var}: {masked}")
    
    if missing:
        print(f"\n❌ Відсутні змінні: {', '.join(missing)}")
        print("Переконайтесь, що файл .env містить всі необхідні значення.")
        return False
    
    return True


async def main():
    print("=" * 50)
    print("BlockMate - Тестування підключень")
    print("=" * 50)
    
    # Перевірка змінних оточення
    env_ok = check_env_vars()
    
    if not env_ok:
        print("\n⚠️  Деякі змінні оточення відсутні. Тести підключень можуть не працювати.")
    
    # Тест MongoDB
    mongodb_ok = await test_mongodb()
    
    # Тест Backend
    backend_ok = await test_backend()
    
    # Підсумок
    print("\n" + "=" * 50)
    print("Підсумок:")
    print(f"Змінні оточення: {'✅' if env_ok else '❌'}")
    print(f"MongoDB: {'✅' if mongodb_ok else '❌'}")
    print(f"Backend API: {'✅' if backend_ok else '❌'}")
    print("=" * 50)
    
    if env_ok and mongodb_ok and backend_ok:
        print("\n🎉 Всі тести пройдені успішно!")
        return 0
    else:
        print("\n⚠️  Деякі тести не пройдені. Перевірте налаштування.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))


