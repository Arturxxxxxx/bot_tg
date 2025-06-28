from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📥 Загрузить данные")],
            [KeyboardButton(text="ℹ️ Инструкция"), KeyboardButton(text="💬 Обратная связь")],
            [KeyboardButton(text="🔗 Ссылка на Я.Диск")]
        ],
        resize_keyboard=True
    )