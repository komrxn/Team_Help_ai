import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from bot.common.config import settings
from bot.common.services.listener import DBListener

# Routers
from bot.admin.handlers import system, drivers, management, export

async def main():
    logging.basicConfig(level=logging.INFO)
    
    redis = Redis(host='redis')
    storage = RedisStorage(redis=redis)
    
    bot = Bot(token=settings.ADMIN_BOT_TOKEN.get_secret_value())
    dp = Dispatcher(storage=storage)

    # Routers
    dp.include_router(system.router)
    dp.include_router(drivers.router)
    dp.include_router(management.router)
    dp.include_router(export.router)

    # Start DB Listener
    # Removed 'new_driver' as Driver Bot handles notifications now.
    # Passing no-op for now since we don't handle any notifications here
    listener = DBListener(
        settings.database_url, 
        [], # No channels for now
        lambda c, p: logging.info(f"Received DB Event: {c} {p}")
    )
    asyncio.create_task(listener.start())

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
