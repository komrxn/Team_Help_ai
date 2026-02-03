from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from aiogram import Bot
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from bot.common.database.core import async_session_factory
from bot.common.database.models import User

async def check_inactive_drivers(bot: Bot, db_url: str, hours: int = 12):
    """
    Checks for drivers who haven't updated location in 'hours' time.
    Sends them a reminder with a location button.
    Should be scheduled to run every 30 minutes.
    """
    start_time = datetime.now()
    async with async_session_factory() as session:
        # Get all approved users
        stmt = select(User).where(User.status == 'active')
        result = await session.execute(stmt)
        users = result.scalars().all()
        
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📍 Send Location", request_location=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )

        cnt = 0
        for user in users:
            last_active = user.last_active_at
            if last_active.tzinfo is None:
                last_active = last_active.replace(tzinfo=timezone.utc)
            
            # Use UTC for current time comparison to avoid offset issues
            now_utc = datetime.now(timezone.utc)
            diff = (now_utc - last_active).total_seconds()
            
            # If inactivity > hours (12h), send reminder
            # The scheduler runs every ~30m, so this acts as a 30m retry loop
            if diff > hours * 3600:
                try:
                    # Localization fallback (english default for system messages)
                    msg = (
                        f"⏳ <b>Update Required!</b>\n\n"
                        f"It has been over {hours} hours since your last location update.\n"
                        f"Please share your live location now to receive orders."
                    )
                    
                    await bot.send_message(
                        user.user_id, 
                        msg,
                        reply_markup=kb,
                        parse_mode="HTML"
                    )
                    cnt += 1
                except Exception as e:
                    print(f"Failed to send reminder to {user.user_id}: {e}")
        
        if cnt > 0:
            print(f"Sent {cnt} location reminders. Duration: {datetime.now() - start_time}")
