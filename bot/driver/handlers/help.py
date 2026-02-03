from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ChatAction, ChatType
from bot.common.services.i18n import t

router = Router()

@router.message(Command("help"), F.chat.type == ChatType.PRIVATE)
async def cmd_help(message: Message):
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    await message.answer(t("driver_help_text"), parse_mode="HTML")
