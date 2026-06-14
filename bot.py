"""
Главный файл бота SizeRandomBot
"""
import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import BOT_TOKEN
from database import Database
from utils import finish_giveaway

# Импорт обработчиков
from handlers import common, create_giveaway, manage_giveaways, admin
from handlers.participate import router as participate_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализация базы данных
db = Database()

# Инициализация планировщика задач
scheduler = AsyncIOScheduler()


async def check_giveaways():
    """
    Проверка и завершение розыгрышей по расписанию
    """
    try:
        # Получаем все активные розыгрыши с автоматическим завершением
        giveaways = await db.get_active_giveaways()
        
        current_time = datetime.now()
        
        for giveaway in giveaways:
            # Проверяем, пришло ли время завершения
            if giveaway['end_time']:
                end_time = datetime.fromisoformat(giveaway['end_time'])
                
                if current_time >= end_time:
                    logger.info(f"Завершаем розыгрыш {giveaway['id']}")
                    success = await finish_giveaway(bot, giveaway['id'])
                    
                    if success:
                        logger.info(f"Розыгрыш {giveaway['id']} успешно завершен")
                    else:
                        logger.warning(f"Не удалось завершить розыгрыш {giveaway['id']}")
    
    except Exception as e:
        logger.error(f"Ошибка при проверке розыгрышей: {e}")


async def on_startup():
    """
    Действия при запуске бота
    """
    logger.info("Инициализация базы данных...")
    await db.init_db()
    
    logger.info("Запуск планировщика задач...")
    # Проверяем розыгрыши каждую минуту
    scheduler.add_job(
        check_giveaways,
        trigger=IntervalTrigger(minutes=1),
        id='check_giveaways',
        replace_existing=True
    )
    scheduler.start()
    
    logger.info("Бот запущен и готов к работе!")


async def on_shutdown():
    """
    Действия при остановке бота
    """
    logger.info("Остановка планировщика задач...")
    scheduler.shutdown()
    
    logger.info("Закрытие соединения с ботом...")
    await bot.session.close()
    
    logger.info("Бот остановлен.")


async def main():
    """
    Главная функция запуска бота
    """
    # Регистрация роутеров
    dp.include_router(common.router)
    dp.include_router(create_giveaway.router)
    dp.include_router(participate_router)
    dp.include_router(manage_giveaways.router)
    dp.include_router(admin.router)
    
    # Запуск бота
    try:
        await on_startup()
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await on_shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
