from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def time_select_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=" День"), KeyboardButton(text="Ночь")],
            [KeyboardButton(text="Выпечка")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )
