import csv
import io
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile
from aiogram.enums import ChatAction

from bot.common.config import settings
from bot.admin.handlers.helpers import IsAdminGroup, get_all_active_users

router = Router()
router.message.filter(IsAdminGroup())

@router.message(Command("export"))
async def cmd_export(message: Message):
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_DOCUMENT)
    
    users = await get_all_active_users()
    if not users:
        await message.answer("⚠️ No active drivers to export.")
        return

    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    # Header
    writer.writerow(["User ID", "Name", "Phone", "Zelle", "Status", "City", "State", "Rating", "Joined At"])
    
    for u in users:
        city = u.location.city if u.location else "N/A"
        state = u.location.state if u.location else "N/A"
        writer.writerow([
            u.user_id,
            u.full_name,
            u.phone,
            u.zelle,
            u.status,
            city,
            state,
            u.rating_score,
            u.created_at.strftime("%Y-%m-%d %H:%M:%S")
        ])
    
    output.seek(0)
    document = BufferedInputFile(output.getvalue().encode(), filename=f"drivers_export_{datetime.now().strftime('%Y%m%d')}.csv")
    
    await message.answer_document(document, caption="📊 <b>Drivers Export</b>", parse_mode="HTML")
