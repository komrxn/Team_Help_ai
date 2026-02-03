import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from redis.asyncio import Redis

from bot.common.config import settings
from bot.common.database.core import init_db
from bot.common.services.listener import DBListener
from bot.common.services.scheduler import check_inactive_drivers
from bot.driver.handlers import registration, location, help
from bot.middlewares.i18n import I18nMiddleware

from apscheduler.schedulers.asyncio import AsyncIOScheduler

async def notify_user_callback(channel, payload, bot: Bot):
    if channel == "user_approved":
        try:
            user_id = int(payload)
            # Create location request keyboard
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="📍 Send Location", request_location=True)],
                    [KeyboardButton(text="🔄 Update Location")] # Manual trigger
                ],
                resize_keyboard=True,
                is_persistent=True
            )
            
            await bot.send_message(
                user_id, 
                "✅ <b>Profile Approved!</b>\n\n"
                "Please share your current location so we can send you orders.\n"
                "<i>Click the button below:</i>",
                reply_markup=kb,
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Failed to notify user {payload}: {e}")

async def main():
    logging.basicConfig(level=logging.INFO)
    
    redis = Redis(host='redis')
    storage = RedisStorage(redis=redis)
    
    bot = Bot(token=settings.DRIVER_BOT_TOKEN.get_secret_value())
    dp = Dispatcher(storage=storage)

    # Middlewares
    dp.update.middleware(I18nMiddleware())

    # Routers
    dp.include_router(registration.router)
    dp.include_router(location.router)
    dp.include_router(help.router)

    await init_db()
    
    # Start DB Listener
    # Removed 'user_approved' listener as it is now handled directly in registration handler
    listener = DBListener(
        settings.database_url, 
        [], 
        lambda c, p: None
    )
    asyncio.create_task(listener.start())
    
    # Start Scheduler
    scheduler = AsyncIOScheduler()
    # Check every 30 mins for drivers inactive > 12h
    scheduler.add_job(check_inactive_drivers, 'interval', minutes=30, args=[bot, settings.database_url, 12]) 
    scheduler.start()

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
