from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

def get_lang_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="English 🇺🇸", callback_data="lang_en"))
    builder.add(InlineKeyboardButton(text="Русский 🇷🇺", callback_data="lang_ru"))
    builder.add(InlineKeyboardButton(text="O'zbek 🇺🇿", callback_data="lang_uz"))
    builder.adjust(1)
    return builder.as_markup()
