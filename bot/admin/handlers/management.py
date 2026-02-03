from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from sqlalchemy import delete

from bot.common.database.core import async_session_factory
from bot.common.database.models import User, Location, Order
from bot.common.services.rating import recalculate_rating
from bot.common.config import settings

from .helpers import (
    IsAdminGroup, AdminStates, 
    get_all_active_users, build_pagination_kb
)

router = Router()
router.message.filter(IsAdminGroup())
router.callback_query.filter(F.message.chat.id == settings.ADMIN_GROUP_ID)

@router.callback_query(F.data == "admin_close")
async def cb_close(callback: CallbackQuery):
    await callback.message.delete()

# --- /delete ---
@router.message(Command("delete"))
async def cmd_delete(message: Message, state: FSMContext):
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    args = message.text.split()
    if len(args) > 1:
        # /delete 123
        await confirm_delete(message, state, args[1])
        return

    # User list to delete
    await show_delete_list(message, page=0)

async def show_delete_list(message: Message, page=0):
    users = await get_all_active_users()
    if not users:
        await message.answer("No drivers to delete.")
        return

    items = [(u.full_name, u.user_id) for u in users]
    kb, total = build_pagination_kb(items, page, "del", columns=2)
    
    text = f"🗑 <b>Select Driver to REMOVE</b> (Page {page+1}/{total})"
    if isinstance(message, CallbackQuery):
        await message.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("del_page_"))
async def cb_del_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    await show_delete_list(callback, page)
    await callback.answer()

@router.callback_query(F.data.startswith("del_select_"))
async def cb_del_select(callback: CallbackQuery, state: FSMContext):
    user_id = callback.data.split("_")[2]
    await confirm_delete(callback.message, state, user_id)
    await callback.answer()

async def confirm_delete(message: Message, state: FSMContext, user_id: str):
    await state.update_data(target_id=int(user_id))
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ CANCEL", callback_data="del_cancel")],
        [InlineKeyboardButton(text="⚠️ YES, DELETE", callback_data="del_confirm")]
    ])
    
    warning = (
        f"⚠️ <b>WARNING: DELETING USER {user_id}</b>\n\n"
        "Are you sure? This cannot be undone."
    )
    if isinstance(message, Message):
        await message.answer(warning, reply_markup=kb, parse_mode="HTML")
    else: # Edited message (from callback)
        await message.edit_text(warning, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "del_cancel")
async def cb_del_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("✅ Deletion Cancelled.")

@router.callback_query(F.data == "del_confirm")
async def cb_del_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    target_id = data.get("target_id")
    
    async with async_session_factory() as session:
         # Manually cascade delete related records to avoid IntegrityError
         await session.execute(delete(Location).where(Location.user_id == target_id))
         await session.execute(delete(Order).where(Order.driver_id == target_id))
         
         stmt = delete(User).where(User.user_id == target_id)
         await session.execute(stmt)
         await session.commit()
    
    await callback.message.edit_text(f"🗑 User {target_id} has been deleted.")
    await state.clear()


# --- /rate ---
@router.message(Command("rate"))
async def cmd_rate(message: Message):
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    args = message.text.split()
    if len(args) > 1:
        await start_rating_flow_by_id(message, None, args[1])
        return
    await show_rate_list(message, page=0)

async def show_rate_list(message: Message, page=0):
    users = await get_all_active_users()
    if not users:
        await message.answer("No active drivers to rate.")
        return

    items = [(u.full_name, u.user_id) for u in users]
    kb, total = build_pagination_kb(items, page, "rate", columns=2)
    
    text = f"⭐️ <b>Select Driver to Rate</b> (Page {page+1}/{total})"
    if isinstance(message, CallbackQuery):
        await message.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("rate_page_"))
async def cb_rate_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    await show_rate_list(callback, page=page)
    await callback.answer()

@router.callback_query(F.data.startswith("rate_select_"))
async def cb_rate_select(callback: CallbackQuery, state: FSMContext):
    user_id = callback.data.split("_")[2]
    await start_rating_flow_by_id(callback.message, state, user_id)
    await callback.answer()

@router.message(F.text.regexp(r"^/rate_(\d+)$"))
async def cmd_rate_click(message: Message, state: FSMContext):
    user_id = message.text.split("_")[1]
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    await start_rating_flow_by_id(message, state, user_id)

async def start_rating_flow_by_id(message: Message, state: FSMContext, user_id: str):
    await state.update_data(target_id=int(user_id))
    await state.set_state(AdminStates.waiting_for_rate_decision)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👍 Good", callback_data="rate_good")],
        [InlineKeyboardButton(text="👎 Bad", callback_data="rate_bad")]
    ])
    
    text = f"📝 <b>Rating Driver</b> <code>{user_id}</code>\n\nHow was the completion?"
    if isinstance(message, Message):
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(AdminStates.waiting_for_rate_decision, F.data.in_(["rate_good", "rate_bad"]))
async def process_rate_decision(callback: CallbackQuery, state: FSMContext):
    is_good = callback.data == "rate_good"
    data = await state.get_data()
    
    # Simplified flow: No route tracking for now, just +/- rating
    await save_rating(callback.from_user.id, data['target_id'], is_good, "N/A", "N/A")
    
    verdict = "✅ GOOD" if is_good else "👎 BAD"
    await callback.message.edit_text(
        f"Rating Saved: <b>{verdict}</b>",
        parse_mode="HTML"
    )
    await state.clear()

async def save_rating(admin_id, driver_id, is_good, route_from, route_to):
    async with async_session_factory() as session:
        session.add(Order(
            driver_id=driver_id,
            admin_id=admin_id,
            route_from=route_from,
            route_to=route_to,
            is_good=is_good
        ))
        await session.commit()
    await recalculate_rating(driver_id)
