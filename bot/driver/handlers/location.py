from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ChatAction, ChatType
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func
import math

from bot.common.services.geocoding import get_location_by_query, get_location_by_coords
from bot.common.services.i18n import t
from bot.common.database.core import async_session_factory
from bot.common.database.models import User as DBUser, Location as DBLocation
from bot.common.data.locations import US_STATES, US_CITIES

router = Router()

class LocationStates(StatesGroup):
    waiting_for_manual_city = State() 
    browsing_states = State()
    browsing_cities = State()

@router.message(F.text.in_([
    "📍 Update Location", "📍 Обновить локацию", "📍 Joylashuvni yangilash", "🔄 Update Location"
]))
async def cmd_update_menu(message: Message, state: FSMContext):
    if message.chat.type != ChatType.PRIVATE: return
    await state.clear()
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("location_btn"), request_location=True)], # "📍 Update Location"
            [KeyboardButton(text=t("manual_location_btn"))] # "🗺 Select Manually"
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(t("location_prompt"), reply_markup=kb, parse_mode="HTML")

@router.message(F.text == "🗺 Qo'lda tanlash", F.chat.type == ChatType.PRIVATE)
@router.message(F.text == "🗺 Select Manually", F.chat.type == ChatType.PRIVATE)
@router.message(F.text == "🗺 Выбрать вручную", F.chat.type == ChatType.PRIVATE)
async def cmd_manual_selection(message: Message, state: FSMContext):
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    await show_states_menu(message, page=0)

async def show_states_menu(message: Message | CallbackQuery, page=0):
    # Pagination for States
    items = list(US_STATES.items()) # [(code, name), ...]
    ITEMS_PER_PAGE = 10
    total_pages = math.ceil(len(items) / ITEMS_PER_PAGE)
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_items = items[start:end]
    
    buttons = []
    row = []
    for code, name in page_items:
        row.append(InlineKeyboardButton(text=name, callback_data=f"set_state_{code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    # Navigation
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"state_page_{page-1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"state_page_{page+1}"))
    if nav_row:
        buttons.append(nav_row)
        
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    text = t("choose_state")
    if isinstance(message, CallbackQuery):
        await message.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("state_page_"))
async def cb_state_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    await show_states_menu(callback, page)
    await callback.answer()

@router.callback_query(F.data.startswith("set_state_"))
async def cb_state_selected(callback: CallbackQuery, state: FSMContext):
    state_code = callback.data.split("_")[2]
    state_name = US_STATES.get(state_code, state_code)
    
    await state.update_data(selected_state=state_name, selected_state_code=state_code)
    await show_cities_menu(callback, state_code, page=0) # Pass state_code explicitly or via retrieval

async def show_cities_menu(callback: CallbackQuery, state_code: str, page=0):
    cities = US_CITIES.get(state_code, []) # List of strings
    
    ITEMS_PER_PAGE = 10
    total_pages = math.ceil(len(cities) / ITEMS_PER_PAGE)
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_items = cities[start:end]
    
    buttons = []
    row = []
    for city in page_items:
        cb_data = f"set_city_{city}"[:64]
        row.append(InlineKeyboardButton(text=city, callback_data=cb_data))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    # Navigation for Cities
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"city_page_{state_code}_{page-1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"city_page_{state_code}_{page+1}"))
    if nav_row:
        buttons.append(nav_row)

    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="back_to_states")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(t("enter_city"), reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("city_page_"))
async def cb_city_page(callback: CallbackQuery):
    parts = callback.data.split("_")
    # Format: city_page_STATECODE_PAGE
    state_code = parts[2]
    page = int(parts[3])
    await show_cities_menu(callback, state_code, page)

@router.callback_query(F.data == "back_to_states")
async def cb_back_states(callback: CallbackQuery):
    await show_states_menu(callback, page=0)
    await callback.answer()

@router.callback_query(F.data.startswith("set_city_"))
async def cb_city_selected(callback: CallbackQuery, state: FSMContext):
    city_name = callback.data.replace("set_city_", "")
    data = await state.get_data()
    state_name = data.get("selected_state", "Unknown")
    
    await save_location(callback.from_user.id, state_name, city_name, 0.0, 0.0)
    
    await callback.message.delete()
    await callback.message.answer(t("location_saved", state=state_name, city=city_name), parse_mode="HTML")
    await callback.answer()

@router.message(F.location, F.chat.type == ChatType.PRIVATE)
async def handle_location(message: Message, state: FSMContext):
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    lat = message.location.latitude
    lon = message.location.longitude
    
    # Use existing reverse geocoding service
    res_state, res_city, _, _ = get_location_by_coords(lat, lon)
    
    await save_location(message.from_user.id, res_city, res_state, lat, lon)
    
    await state.clear()
    await message.answer(t("location_saved", state=res_state, city=res_city), parse_mode="HTML")
    
    # Restore Main Menu
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("location_btn"), request_location=True)],
            [KeyboardButton(text=t("manual_location_btn"))],
            [KeyboardButton(text="/help")]
        ],
        resize_keyboard=True
    )
    # The user wanted something like "Thank you" instead of "Menu"
    await message.answer(t("menu_text_thank_you"), reply_markup=kb, parse_mode="HTML")

async def save_location(user_id, city, state, lat, lon):
    async with async_session_factory() as session:
        stmt = insert(DBLocation).values(
            user_id=user_id,
            city=city,
            state=state,
            latitude=lat,
            longitude=lon
        ).on_conflict_do_update(
            index_elements=['user_id'],
            set_=dict(
                city=city,
                state=state,
                latitude=lat,
                longitude=lon,
                updated_at=func.now()
            )
        )
        await session.execute(stmt)
        
        # Update User last_active_at
        from sqlalchemy import update
        await session.execute(
            update(DBUser).where(DBUser.user_id == user_id).values(last_active_at=func.now())
        )
        
        await session.commit()
