from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from data.database import conn
from datetime import datetime
from keybords.main_kb import main_menu_kb

router = Router()

class FeedbackState(StatesGroup):
    writing = State()

@router.message(F.text == "💬 Обратная связь")
async def feedback_start(message: Message, state: FSMContext):
    await message.answer("✍️ Напишите ваше сообщение (или /cancel для отмены):")
    await state.set_state(FeedbackState.writing)

@router.message(FeedbackState.writing)
async def feedback_save(message: Message, state: FSMContext):
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO feedback (user_id, username, message, created_at)
        VALUES (?, ?, ?, ?)
    ''', (
        message.from_user.id,
        message.from_user.username,
        message.text,
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ))
    conn.commit()

    await message.answer("✅ Спасибо! Ваше сообщение отправлено.")
    await state.clear()

@router.message(F.text == "/cancel")
async def cancel_feedback(message: Message, state: FSMContext):
    await message.answer("❌ Отменено.", reply_markup=main_menu_kb())
    await state.clear()
