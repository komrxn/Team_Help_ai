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
    # 1. Resolve Target Location (Lat/Lon)
    target_lat, target_lon = None, None
    search_term = ""
    
    if city_query and state_query:
        search_term = f"{city_query}, {state_query}"
    elif state_query:
        search_term = state_query
    elif city_query:
        search_term = city_query
        
    if search_term:
        from bot.common.services.geocoding import get_location_by_query, calculate_distance
        loc_res = get_location_by_query(search_term)
        if loc_res:
             _, _, target_lat, target_lon = loc_res
    
    # 2. Fetch Users
    users = await get_all_active_users()
    
    if not users:
        await message.answer("⚠️ No active drivers found in database.")
        return

    # 3. Filter/Sort Logic
    results = [] # List of tuples (User, Distance)
    
    if target_lat is not None and target_lon is not None:
        # Distance-based sort
        for u in users:
            if u.location and u.location.latitude and u.location.longitude:
                dist = calculate_distance(target_lat, target_lon, u.location.latitude, u.location.longitude)
                results.append((u, dist))
            else:
                # Users without location go to bottom if we are sorting by distance
                results.append((u, float('inf')))
        
        # Sort by distance (asc)
        results.sort(key=lambda x: x[1])
        
        # Take Top 10
        results = results[:10]
        match_type = f"📍 <b>Nearest to {search_term}:</b>"
        
    else:
        # Fallback to Text Match (Old Logic) if Geocoding Fails
        # Or if we just want to match text strictly.
        # But user requested "proximity", so if geocoding fails, we might just warn.
        # Let's keep a basic text filter as backup.
        match_type = f"🔍 <b>Text Matches for '{search_term}':</b>"
        for u in users:
            u_loc_str = f"{u.location.city} {u.location.state}" if u.location else ""
            if city_query and city_query.lower() in u_loc_str.lower():
                results.append((u, -1))
            elif state_query and state_query.lower() in u_loc_str.lower():
                results.append((u, -1))
        
        if not results and search_term:
             await message.answer(f"❌ Location '{search_term}' not found and no text matches.")
             return
             
    # 4. Generate Output
    text = f"{match_type}\n\n"
    
    for u, dist in results:
        stars = get_star_rating(u.rating_score)
        
        now = datetime.now(timezone.utc)
        last_active = u.last_active_at
        if last_active.tzinfo is None: last_active = last_active.replace(tzinfo=timezone.utc)
        
        diff = now - last_active
        if diff.total_seconds() < 3600:
            seen = f"{int(diff.total_seconds()/60)}m ago"
        else:
            seen = f"{int(diff.total_seconds()/3600)}h ago"
        
        username_link = f"<a href='tg://user?id={u.user_id}'>{u.full_name or 'Driver'}</a>"
        
        loc_str = f"{u.location.city}, {u.location.state}" if u.location else "Unknown"
        
        dist_str = ""
        if dist != float('inf') and dist != -1:
            dist_str = f"\n📏 <b>{dist:.1f} miles away</b>"
        
        text += (
            f"👤 {username_link}\n"
            f"📍 {loc_str} | 🕒 {seen}"
            f"{dist_str}\n"
            f"⭐️ {stars} ({u.rating_score:.1f}) | 🆔 <code>{u.user_id}</code>\n"
            f"👉 /rate_{u.user_id}\n\n"
        )
    
    if isinstance(message, Message):
        await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
    else:
        await message.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
