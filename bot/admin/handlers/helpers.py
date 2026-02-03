import math
from datetime import datetime, timezone
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.filters import Filter
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from bot.common.config import settings
from bot.common.database.core import async_session_factory
from bot.common.database.models import User
from bot.common.services.rating import get_star_rating

class IsAdminGroup(Filter):
    async def __call__(self, message: Message) -> bool:
        return message.chat.id == settings.ADMIN_GROUP_ID

class AdminStates(StatesGroup):
    waiting_for_rate_decision = State()
    waiting_for_route = State()
    waiting_for_delete_confirm = State()

async def get_all_active_users():
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).options(selectinload(User.location)).where(User.status == 'active').order_by(User.full_name)
        )
        return result.scalars().all()

def build_pagination_kb(items, page, prefix, columns=1, back_btn=True):
    ITEMS_PER_PAGE = 10
    total_pages = math.ceil(len(items) / ITEMS_PER_PAGE)
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_items = items[start:end]
    
    buttons = []
    row = []
    for item in page_items:
        # Item must be tuple (text, data_suffix)
        row.append(InlineKeyboardButton(text=item[0], callback_data=f"{prefix}_select_{item[1]}"))
        if len(row) == columns:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    # Navigation
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"{prefix}_page_{page-1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"{prefix}_page_{page+1}"))
    if nav_row:
        buttons.append(nav_row)

    if back_btn:
         buttons.append([InlineKeyboardButton(text="🔙 Close", callback_data="admin_close")])
         
    return InlineKeyboardMarkup(inline_keyboard=buttons), total_pages

async def generate_active_drivers_text(users):
    text = "🚙 <b>Active Drivers List</b>\n\n"
    for u in users:
        loc = f"{u.location.city}, {u.location.state}" if u.location else "Unknown"
        last_active = u.last_active_at
        if last_active.tzinfo is None:
             last_active = last_active.replace(tzinfo=timezone.utc)
             
        time_diff = datetime.now(timezone.utc) - last_active
        if time_diff.total_seconds() < 3600:
             last_seen = f"{int(time_diff.total_seconds()/60)}m ago"
        else:
             last_seen = f"{int(time_diff.total_seconds()/3600)}h ago"

        username_link = f"<a href='tg://user?id={u.user_id}'>{u.full_name}</a>"
        
        text += (
            f"👤 {username_link}\n"
            f"📍 {loc} | 🕒 {last_seen}\n"
            f"⭐️ {get_star_rating(u.rating_score)} ({u.rating_score:.1f}) | 🆔 <code>{u.user_id}</code>\n"
            f"-----------------\n"
        )
    return text
