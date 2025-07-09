import os
import asyncio
from aiogram import types, F, Router, Bot
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from celery.result import AsyncResult
from states.load_states import AuthCompanyStates

from keybords.main_kb import main_menu_kb
from utils.upload_excel import generate_upload_and_get_links, list_admin_weeks, get_yadisk_public_url
from data.database import conn
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
router = Router()

ADMIN_IDS = [5469335222, 5459748606]
 

# @router.message()
# async def get_chat_id(message: types.Message):
#     chat_id = message.chat.id
#     await message.reply(f"ID этого чата: {chat_id}")



@router.message(F.text == '/start')
async def start_handler(message: Message, state: FSMContext):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("👋 Добро пожаловать, администратор!", reply_markup=main_menu_kb())
        return

    await message.answer("Добро пожаловать! Пожалуйста, введите код вашей компании для авторизации:")
    await state.set_state(AuthCompanyStates.waiting_for_code)

@router.message(F.text == "/cancel")
async def cancel(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("❌ Отменено.", reply_markup=main_menu_kb())

@router.message(F.text.startswith('/auth'))
async def auth_via_command(message: Message, state: FSMContext):
    try:
        _, code = message.text.strip().split(maxsplit=1)
    except ValueError:
        await message.answer("❌ Использование команды:\n`/auth <код>`", parse_mode="Markdown")
        return

    cursor = conn.cursor()
    cursor.execute("SELECT id FROM companies WHERE code = ?", (code,))
    row = cursor.fetchone()
    if not row:
        await message.answer("❌ Неверный код компании. Попробуйте снова.")
        return

    company_id = row[0]
    cursor.execute(
        "INSERT OR REPLACE INTO user_company (user_id, company_id) VALUES (?, ?)",
        (message.from_user.id, company_id)
    )
    conn.commit()

    await message.answer("✅ Авторизация прошла успешно!", reply_markup=main_menu_kb())


@router.message(F.text == "ℹ️ Инструкция")
async def instruction_handler(message: Message):
    text = (
        "ℹ️ **Как работает бот:**\n\n"
        "1. Нажмите 📥 Загрузить данные\n"
        "2. Выберите день недели\n"
        "3. Выберите время (день / ночь / запайка)\n"
        "4. Введите количество порций\n\n"
        "Если вы вводите порции повторно за один день — бот их суммирует или заменяет.\n"
        "Вы всегда можете отменить ввод или начать заново.\n\n"
        "❓ Для связи нажмите 💬 Обратная связь"
    )
    await message.answer(text)


#admin
@router.message(F.text.startswith('/create_company'))
async def create_company_handler(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    try:
        _, name, code = message.text.split(maxsplit=2)
    except ValueError:
        await message.answer("❌ Использование команды:\n/create_company <название> <код>")
        return

    cursor = conn.cursor()
    cursor.execute("SELECT id FROM companies WHERE code = ?", (code,))
    if cursor.fetchone():
        await message.answer(f"❌ Компания с кодом '{code}' уже существует.")
        return

    cursor.execute(
        "INSERT INTO companies (name, code) VALUES (?, ?)",
        (name, code)
    )
    conn.commit()
    await message.answer(f"✅ Компания '{name}' с кодом '{code}' успешно создана.")


# 📋 Получить список компаний
@router.message(F.text.startswith("/companies"))
async def list_companies(message: types.Message):
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT name FROM companies ORDER BY name")
    companies = [row[0] for row in cursor.fetchall()]
    
    if not companies:
        await message.answer("❌ Нет зарегистрированных компаний.")
        return

    companies_list = "\n".join(f"• {c}" for c in companies)
    await message.answer(f"📦 Список компаний:\n\n{companies_list}")

# ❌ Удалить компанию
@router.message(F.text.startswith("/delete_company"))
async def delete_company(message: types.Message):
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ Укажите название компании: `/delete_company Название_Компании`", parse_mode="Markdown")
        return

    company_name = parts[1]

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM companies WHERE name = ?", (company_name,))
    count = cursor.fetchone()[0]

    if count == 0:
        await message.answer(f"❌ Компания с названием `{company_name}` не найдена.", parse_mode="Markdown")
        return

    cursor.execute("DELETE FROM companies WHERE name = ?", (company_name,))
    conn.commit()
    await message.answer(f"✅ Компания `{company_name}` и её {count} заявок удалены.", parse_mode="Markdown")



@router.message(F.text == "🔗 Ссылка на Я.Диск")
async def yandex_link_handler(message: Message, state: FSMContext, bot: Bot):
    # Получаем компанию пользователя из базы
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM companies "
                   "JOIN user_company ON companies.id = user_company.company_id "
                   "WHERE user_company.user_id = ?", (message.from_user.id,))
    row = cursor.fetchone()
    if not row:
        await message.answer("❌ Вы не авторизованы. Введите код компании через /auth <код>.")
        return

    company_name = row[0]
    await message.answer("⏳ Генерация файла и загрузка на Яндекс.Диск...")

    task = generate_upload_and_get_links.delay(
        user_id=message.from_user.id,
        company_name=company_name
    )
    asyncio.create_task(check_task_and_send_result(bot, message.from_user.id, task.id))


async def check_admin_excel_result(bot: Bot, chat_id: int, task_id: str):
    for _ in range(20): 
        await asyncio.sleep(1)
        result = AsyncResult(task_id)
        if result.ready():
            if result.successful():
                data = result.get()
                admin_link = data.get("admin_link")
                if admin_link:
                    await bot.send_message(chat_id, f"🛠 Админ-файл готов:\n{admin_link}")
                else:
                    await bot.send_message(chat_id, "Файл администратора не найден.")
            else:
                await bot.send_message(chat_id, "❌ Ошибка при генерации файла.")
            return
    await bot.send_message(chat_id, "⏱ Время ожидания истекло. Попробуйте позже.")



async def check_task_and_send_result(bot, chat_id, task_id):
    for _ in range(20):  
        await asyncio.sleep(1)
        result = AsyncResult(task_id)
        if result.ready():
            if result.successful():
                data = result.get()
                user_link = data.get("user_link")
                if user_link:
                    await bot.send_message(chat_id, f"Ваш файл готов! Вот ссылка:\n{user_link}")
                else:
                    await bot.send_message(chat_id, "Файл с вашими данными не найден.")
            else:
                await bot.send_message(chat_id, "Произошла ошибка при генерации файла.")
            return
    await bot.send_message(chat_id, "Время ожидания истекло. Попробуйте позже.")


@router.message(F.text == "/admin_excel")
async def admin_excel_handler(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет прав для этой команды.")
        return

    try:
        weeks = list_admin_weeks()
        if not weeks:
            await message.answer("Нет доступных отчётов.")
            return

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=week, callback_data=f"admin_excel:{week}")]
                for week in weeks
            ]
        )
        await message.answer("📅 Выберите неделю для отчёта:", reply_markup=kb)

    except Exception as e:
        await message.answer("Ошибка при получении списка отчётов.")
        print(f"[ADMIN EXCEL ERROR] {e}")


# 🔹 Хендлер кнопки (колбэк)
@router.callback_query(F.data.startswith("admin_excel:"))
async def send_admin_excel_link(callback: CallbackQuery):
    week = callback.data.split(":")[1]
    path = f"admin/admin_orders_{week}.xlsx"

    url = get_yadisk_public_url(path)
    if url:
        await callback.message.answer(f"📥 Отчёт за неделю {week}:\n{url}")
    else:
        await callback.message.answer("❌ Не удалось получить ссылку на файл.")