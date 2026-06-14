"""
Конфигурация бота SizeRandomBot
"""
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ID администратора
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# Настройки базы данных
USE_SQLITE = os.getenv("USE_SQLITE", "True").lower() == "true"

if USE_SQLITE:
    DATABASE_URL = "sqlite+aiosqlite:///sizerandom.db"
else:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "sizerandom_bot")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Константы бота
MAX_WINNERS = 100
MAX_CHANNELS = 5
BOT_NAME = "SizeRandomBot"
WELCOME_MESSAGE = (
    "Привет! Я SizeRandomBot — твой надежный помощник для проведения "
    "честных розыгрышей в Telegram. Нажми кнопку ниже, чтобы создать "
    "свой первый конкурс!"
)
