from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from bot.common.config import settings

# This currently replaces the 'public_router'
router = Router()

@router.message(Command("id"))
async def cmd_id(message: Message):
    await message.answer(f"Chat ID: `{message.chat.id}`", parse_mode="Markdown")

@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "🛠 <b>Admin Commands</b>\n\n"
        "<b>Drivers:</b>\n"
        "• <code>/drivers</code> - List all active drivers\n"
        "• <code>/find</code> - Find driver (Menu)\n"
        "• <code>/find NY</code> - Find by State shortcut\n"
        "• <code>/rate</code> - Rate driver (Menu)\n"
        "• <code>/delete</code> - Delete driver (Menu)\n"
        "• <code>/approve [ID]</code> - Quick approve\n\n"
        "<b>System:</b>\n"
        "• <code>/export</code> - Download CSV\n"
    )
    await message.answer(text, parse_mode="HTML")
