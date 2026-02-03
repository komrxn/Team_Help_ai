from datetime import datetime, timezone
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatAction
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from bot.common.database.core import async_session_factory
from bot.common.database.models import User, Location
from bot.common.services.rating import get_star_rating
from bot.common.config import settings
from bot.common.data.locations import US_STATES, US_CITIES

from .helpers import (
    IsAdminGroup, 
    get_all_active_users, 
    generate_active_drivers_text
)

router = Router()
router.message.filter(IsAdminGroup())
router.callback_query.filter(F.message.chat.id == settings.ADMIN_GROUP_ID)

# --- /drivers ---
@router.message(Command("drivers"))
async def cmd_drivers(message: Message):
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    users = await get_all_active_users()
    
    if not users:
        await message.answer("⚠️ No active drivers found.")
        return

    text = await generate_active_drivers_text(users)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Refresh List", callback_data="refresh_drivers")]])
    
    try:
        if len(text) > 4000:
            for x in range(0, len(text), 4000):
                await message.answer(text[x:x+4000], parse_mode="HTML")
            # Send button in separate message if split
            await message.answer("🔄", reply_markup=kb)
        else:
             if isinstance(message, Message):
                await message.answer(text, parse_mode="HTML", reply_markup=kb)
             else:
                try: 
                    await message.edit_text(text, parse_mode="HTML", reply_markup=kb)
                except Exception:
                    await message.answer(text, parse_mode="HTML", reply_markup=kb)
                    
    except Exception as e:
        print(f"Error sending drivers list: {e}")

@router.callback_query(F.data == "refresh_drivers")
async def cb_refresh_drivers(callback: CallbackQuery):
    users = await get_all_active_users()
    
    if not users:
        await callback.message.edit_text("⚠️ No active drivers found.")
        return

    text = await generate_active_drivers_text(users)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 Refresh List", callback_data="refresh_drivers")]])
    
    try:
        if callback.message.text != text or callback.message.caption != text:
             await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        else:
             await callback.answer("List is up to date.")
    except Exception:
         await callback.answer("List is up to date.")

# --- /find ---
@router.message(Command("find"))
async def cmd_find(message: Message):
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    args = message.text.split()[1:]
    if args:
        state_query = args[0].upper()
        city_query = " ".join(args[1:]) if len(args) > 1 else ""
        await execute_find(message, state_query, city_query)
        return

    await show_find_states(message)

async def show_find_states(message: Message):
    buttons = []
    row = []
    for code, name in US_STATES.items():
        row.append(InlineKeyboardButton(text=name, callback_data=f"find_state_{code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    if isinstance(message, CallbackQuery):
        await message.message.edit_text("🇺🇸 <b>Select State to Find Drivers:</b>", reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer("🇺🇸 <b>Select State to Find Drivers:</b>", reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("find_state_"))
async def cb_find_state(callback: CallbackQuery):
    state_code = callback.data.split("_")[2]
    # Show Cities
    cities = US_CITIES.get(state_code, [])
    buttons = []
    row = []
    for city in cities:
        cb_data = f"find_city_{city}"[:64]
        row.append(InlineKeyboardButton(text=city, callback_data=cb_data))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="find_back_states")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(f"🏙 <b>Select City in {state_code}:</b>", reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "find_back_states")
async def cb_find_back(callback: CallbackQuery):
    await show_find_states(callback)

@router.callback_query(F.data.startswith("find_city_"))
async def cb_find_city(callback: CallbackQuery):
    city_name = callback.data.replace("find_city_", "")
    await execute_find(callback.message, None, city_name)
    await callback.answer()

async def execute_find(message: Message, state_query, city_query):
    async with async_session_factory() as session:
        q = select(User).join(Location).options(selectinload(User.location)).where(User.status == 'active')
        
        if state_query:
            full_state_name = None
            if len(state_query) == 2:
                full_state_name = US_STATES.get(state_query.upper())
            
            if full_state_name:
                 q = q.where(or_(Location.state.ilike(f"%{state_query}%"), Location.state.ilike(f"%{full_state_name}%")))
            else:
                 q = q.where(Location.state.ilike(f"%{state_query}%"))
            
        if city_query:
            q = q.where(Location.city.ilike(f"%{city_query}%"))
            
        result = await session.execute(q)
        users = result.scalars().all()

    if not users:
        text = f"❌ No active drivers found in {city_query or state_query}."
        if isinstance(message, Message): await message.answer(text)
        else: await message.edit_text(text)
        return

    text = ""
    for u in users:
        stars = get_star_rating(u.rating_score)
        
        now = datetime.now(timezone.utc)
        last_active = u.last_active_at
        if last_active.tzinfo is None: last_active = last_active.replace(tzinfo=timezone.utc)
        
        diff = now - last_active
        if diff.total_seconds() < 3600:
            seen = f"{int(diff.total_seconds()/60)} mins ago"
        else:
            seen = f"{int(diff.total_seconds()/3600)} hours ago"
        
        username_link = f"<a href='tg://user?id={u.user_id}'>{u.full_name or 'Driver'}</a>"
        
        text += (
            f"👤 {username_link}\n"
            f"📍 {u.location.city}, {u.location.state} | 🕒 {seen}\n"
            f"⭐️ {stars} ({u.rating_score:.1f}) | 🆔 <code>{u.user_id}</code>\n"
            f"👉 /rate_{u.user_id}\n\n"
        )
    
    if isinstance(message, Message):
        await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
    else:
        await message.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
