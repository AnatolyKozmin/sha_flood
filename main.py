import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from handlers import chat_init, orgkom_handlers, user_handlers
from database.engine import AsyncSessionLocal
from database.models import Wakeup
from sqlalchemy import select
from datetime import datetime
import asyncio

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция для запуска бота"""
    # Инициализация бота и диспетчера
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Подключаем роутеры
    dp.include_router(chat_init.router)
    dp.include_router(orgkom_handlers.router)
    dp.include_router(user_handlers.router)
    
    logger.info("🚀 Бот запускается...")

    async def wakeup_scheduler():
        """Периодически проверяет запланированные побудки и отправляет уведомления."""
        while True:
            try:
                now = datetime.utcnow()
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(Wakeup).where(Wakeup.done == False, Wakeup.wake_at <= now)
                    )
                    due = result.scalars().all()
                    for w in due:
                        try:
                            await bot.send_message(
                                w.chat_id,
                                f"⏰ Пора вставать! <a href=\"tg://user?id={w.user_id}\">тебя</a>",
                                parse_mode="HTML"
                            )
                        finally:
                            w.done = True
                    if due:
                        await session.commit()
            except Exception as e:
                logger.exception("Wakeup scheduler error: %s", e)
            await asyncio.sleep(30)
    
    try:
        # Удаляем старые апдейты и запускаем polling
        asyncio.create_task(wakeup_scheduler())
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⛔️ Бот остановлен")
