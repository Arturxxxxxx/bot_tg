from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def day_select_keyboard(days: list):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=day)] for day in days] + [[KeyboardButton(text="🔙 Назад")]],
        resize_keyboard=True
    )