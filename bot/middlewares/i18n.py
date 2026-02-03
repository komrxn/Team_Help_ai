from typing import Any, Dict, Callable, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from sqlalchemy.future import select
from bot.common.services.i18n import t, set_lang
from bot.common.database.core import async_session_factory
from bot.common.database.models import User as DBUser

class I18nMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user: User = data.get("event_from_user")
        
        if not user:
            return await handler(event, data)

        async with async_session_factory() as session:
            result = await session.execute(select(DBUser).where(DBUser.user_id == user.id))
            db_user = result.scalar_one_or_none()
            
            if db_user:
                set_lang(db_user.language)
                data["user_lang"] = db_user.language
                data["db_user"] = db_user
            else:
                # Try to get lang from FSM if not in DB
                state = data.get("state")
                fsm_lang = "en"
                if state:
                    fsm_data = await state.get_data()
                    fsm_lang = fsm_data.get("language", "en")
                
                set_lang(fsm_lang)
                data["user_lang"] = fsm_lang
                data["db_user"] = None
        
        return await handler(event, data)
