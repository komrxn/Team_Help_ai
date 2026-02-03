from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.enums import ChatType
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from bot.fsm.registration import RegistrationStates
from bot.keyboards.common import get_lang_keyboard
from bot.common.services.i18n import t, set_lang
from bot.common.database.core import async_session_factory
from bot.common.database.models import User as DBUser
from bot.common.config import settings
# Removed circular import of notify_user_callback

router = Router()

@router.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
async def cmd_start(message: Message, state: FSMContext, user_lang: str = "en", db_user: DBUser = None):
    if db_user and db_user.status == "active":
        await message.answer(t("welcome_back") or "Welcome back!") # TODO: Add menu
        return

    await state.set_state(RegistrationStates.waiting_for_lang)
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    await message.answer(t("welcome"), reply_markup=get_lang_keyboard(), parse_mode="HTML")

@router.callback_query(RegistrationStates.waiting_for_lang, F.data.startswith("lang_"))
async def process_lang_selection(callback: CallbackQuery, state: FSMContext):
    lang_code = callback.data.split("_")[1]
    set_lang(lang_code)
    
    await state.update_data(language=lang_code)
    await state.set_state(RegistrationStates.waiting_for_name)
    await callback.bot.send_chat_action(chat_id=callback.message.chat.id, action=ChatAction.TYPING)
    await callback.message.answer(t("ask_name"), parse_mode="HTML")
    await callback.answer()

@router.message(RegistrationStates.waiting_for_name, F.chat.type == ChatType.PRIVATE)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await state.set_state(RegistrationStates.waiting_for_phone)
    
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t("share_phone"), request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    await message.answer(t("ask_phone"), reply_markup=kb, parse_mode="HTML")

@router.message(RegistrationStates.waiting_for_phone, F.contact, F.chat.type == ChatType.PRIVATE)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await state.set_state(RegistrationStates.waiting_for_zelle)
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    await message.answer(t("ask_zelle"), reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")

@router.message(RegistrationStates.waiting_for_zelle, F.chat.type == ChatType.PRIVATE)
async def process_zelle(message: Message, state: FSMContext):
    await state.update_data(zelle=message.text)
    await state.set_state(RegistrationStates.waiting_for_photo)
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    await message.answer(t("ask_photo"), parse_mode="HTML")

@router.message(RegistrationStates.waiting_for_photo, F.photo, F.chat.type == ChatType.PRIVATE)
async def process_photo(message: Message, state: FSMContext, bot: Bot):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    data['dl_photo_id'] = photo_id # Store photo_id in data for later use
    
    # Create User in DB
    async with async_session_factory() as session:
        # Check if exists
        result = await session.execute(select(DBUser).where(DBUser.user_id == message.from_user.id))
        user = result.scalar_one_or_none()
        
        if user:
            # Update
            user.full_name = data['full_name']
            user.phone = data['phone']
            user.zelle = data['zelle']
            user.dl_photo_id = data['dl_photo_id']
            # Re-set to pending if they are updating? Or keep status?
            # If rejected/pending, set to pending. If active, keep active?
            # Usually re-registration implies pending.
            if user.status != 'active':
                user.status = 'pending'
            user.language = data['language']
        else:
            # Create
            user = DBUser(
                user_id=message.from_user.id,
                full_name=data['full_name'],
                phone=data['phone'],
                zelle=data['zelle'],
                dl_photo_id=data['dl_photo_id'],
                status='pending',
                language=data['language']
            )
            session.add(user)
        
        await session.commit()

    await state.clear()
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    await message.answer(t("registration_complete"), reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    
    # Notify Admin Group (Driver Bot must be in the group!)
    try:
        msg = (
            f"🔔 <b>New Driver Request!</b>\n\n"
            f"👤 <b>Name:</b> {data['full_name']}\n"
            f"📱 <b>Phone:</b> <code>{data['phone']}</code>\n"
            f"💳 <b>Zelle:</b> <code>{data['zelle']}</code>\n"
            f"🗣 <b>Lang:</b> {data['language']}\n"
            f"🆔 <b>ID:</b> <code>{message.from_user.id}</code> | <a href='tg://user?id={message.from_user.id}'>Profile</a>\n\n"
            f"<i>Please verify the DL photo below.</i>"
        )
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Approve Driver", callback_data=f"approve_{message.from_user.id}")]
        ])
        
        if data['dl_photo_id']:
             await message.bot.send_photo(
                 settings.ADMIN_GROUP_ID, 
                 data['dl_photo_id'], 
                 caption=msg, 
                 parse_mode="HTML", 
                 reply_markup=kb
             )
        else:
             await message.bot.send_message(
                 settings.ADMIN_GROUP_ID, 
                 msg + "\n\n⚠️ <b>No DL Photo provided!</b>", 
                 parse_mode="HTML", 
                 reply_markup=kb
             )
    except Exception as e:
        # Failure to notify group shouldn't crash the user flow, but we should log it
        # Likely cause: Bot not in group or ID wrong.
        print(f"Failed to notify Admin Group: {e}")
        await message.answer("⚠️ System Warning: Could not notify dispatchers. Please contact admin manually.")

@router.callback_query(F.data.startswith("approve_"))
async def cb_approve(callback: CallbackQuery):
    # Driver Bot handles approval because it sent the message to the group
    try:
        target_id = int(callback.data.split("_")[1])
        
        # Update DB
        async with async_session_factory() as session:
            stmt = update(DBUser).where(DBUser.user_id == target_id).values(status='active')
            await session.execute(stmt)
            await session.commit()
        
        # Edit Admin Group Message
        new_text = "\n\n✅ APPROVED (by " + callback.from_user.full_name + ")"
        if callback.message.caption:
            await callback.message.edit_caption(caption=callback.message.caption + new_text, parse_mode="HTML")
        elif callback.message.text:
            await callback.message.edit_text(text=callback.message.text + new_text, parse_mode="HTML")
            
        await callback.answer("Driver Approved!")
        
        # Notify User (We are the driver bot, so we can msg them directly!)
        # Direct notification is more reliable than DB triggers + Listeners
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📍 Send Location", request_location=True)],
                [KeyboardButton(text="🔄 Update Location")]
            ],
            resize_keyboard=True,
            is_persistent=True
        )
        
        await callback.bot.send_message(
            target_id, 
            t("profile_approved"),
            reply_markup=kb,
            parse_mode="HTML"
        )
        
    except Exception as e:
        print(f"Approval error: {e}")
        await callback.answer("Error approving user.")
