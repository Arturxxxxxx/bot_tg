from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

def day_select_keyboard(day_options):
    buttons = [
        [KeyboardButton(text=day_name)] for day_name, _ in day_options
    ]
    buttons.append([KeyboardButton(text="🔙 Назад")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)