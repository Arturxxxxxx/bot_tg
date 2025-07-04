# handlers/feedback.py
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

from data.database import conn
from keybords.main_kb import main_menu_kb

# ─────────── ID чатов (замени на реальные) ────────────
FEEDBACK_CHAT_ID = -4860703178   # группа «Обратная связь»

router = Router()

class FeedbackState(StatesGroup):
    writing = State()

# ─────────── старт ввода ────────────
@router.message(F.text == "💬 Обратная связь")
async def feedback_start(msg: Message, state: FSMContext):
    await state.set_state(FeedbackState.writing)
    await msg.answer("✍️ Напишите ваше сообщение\n(/cancel — отмена)")

# ─────────── приём текста ────────────
@router.message(FeedbackState.writing, ~F.text.startswith("/"))
async def feedback_save(msg: Message, state: FSMContext, bot: Bot):
    # 1. сохраняем в БД
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO feedback (user_id, username, message, created_at) "
        "VALUES (?,?,?,?)",
        (
            msg.from_user.id,
            msg.from_user.username,
            msg.text,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()

    # 2. публикуем в группу
    text = (
        "📝 <b>Обратная связь</b>\n"
        f"👤 <a href='tg://user?id={msg.from_user.id}'>{msg.from_user.full_name}</a>\n\n"
        f"{msg.text}"
    )
    await bot.send_message(FEEDBACK_CHAT_ID, text, parse_mode="HTML")

    # 3. отвечаем пользователю
    await msg.answer("✅ Спасибо! Ваше сообщение передано.", reply_markup=main_menu_kb())
    await state.clear()

# ─────────── отмена ────────────
@router.message(FeedbackState.writing, F.text == "/cancel")
async def cancel_feedback(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("❌ Отменено.", reply_markup=main_menu_kb())
