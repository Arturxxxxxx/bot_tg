import os
import asyncio
from aiogram import types, F, Router, Bot
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from celery.result import AsyncResult
from states.load_states import AuthCompanyStates

from keybords.main_kb import main_menu_kb
from utils.upload_excel import generate_upload_and_get_links
from data.database import conn


router = Router()

ADMIN_IDS = [5469335222, 5459748606]
 

@router.message(F.text == '/start')
async def start_handler(message: Message, state: FSMContext):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("👋 Добро пожаловать, администратор!", reply_markup=main_menu_kb())
        return

    await message.answer("Добро пожаловать! Пожалуйста, введите код вашей компании для авторизации:")
    await state.set_state(AuthCompanyStates.waiting_for_code)


@router.message(AuthCompanyStates.waiting_for_code)
async def auth_company(message: Message, state: FSMContext):
    code = message.text.strip()

    cursor = conn.cursor()
    cursor.execute("SELECT id FROM companies WHERE code = ?", (code,))
    row = cursor.fetchone()
    if not row:
        await message.answer("❌ Неверный код компании. Попробуйте ещё раз или введите /start для повторного запроса.")
        return

    company_id = row[0]
    cursor.execute("INSERT OR REPLACE INTO user_company (user_id, company_id) VALUES (?, ?)",
                   (message.from_user.id, company_id))
    conn.commit()

    await message.answer("✅ Авторизация прошла успешно.", reply_markup=main_menu_kb())
    await state.clear()


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


# @router.message(F.text == "/export_excel")
# async def export_excel_handler(message: Message, state: FSMContext, bot: Bot):
#     task = generate_upload_and_get_links.delay(message.from_user.id, message.from_user.username or str(message.from_user.id))
    
#     await message.answer("Генерируем и загружаем файл, это займет несколько секунд...")
#     await state.update_data(task_id=task.id)
    
#     # Запускаем фоновую проверку (без await, чтобы не блокировать)
#     asyncio.create_task(check_task_and_send_result(bot, message.from_user.id, task.id))



# async def check_task_and_send_result(bot, chat_id, task_id):
#     for _ in range(20):  # максимум 20 проверок с паузой 1 секунда (около 20 секунд ожидания)
#         await asyncio.sleep(1)
#         result = AsyncResult(task_id)
#         if result.ready():
#             if result.successful():
#                 data = result.get()
#                 user_link = data.get("user_link")
#                 if user_link:
#                     await bot.send_message(chat_id, f"Ваш файл готов! Вот ссылка:\n{user_link}")
#                 else:
#                     await bot.send_message(chat_id, "Файл с вашими данными не найден.")
#             else:
#                 await bot.send_message(chat_id, "Произошла ошибка при генерации файла.")
#             return
#     await bot.send_message(chat_id, "Время ожидания истекло. Попробуйте позже.")

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


@router.message(F.text == "/admin_excel")
async def admin_excel_handler(message: Message, bot: Bot):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет прав для этой команды.")
        return

    await message.answer("⏳ Генерируем файл администратора...")

    task = generate_upload_and_get_links.delay(user_id=None, username=None)  

    asyncio.create_task(check_admin_excel_result(bot, message.from_user.id, task.id))


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



@router.message(F.text == "🔗 Ссылка на Я.Диск")
async def yandex_link_handler(message: Message, state: FSMContext, bot: Bot):
    await message.answer("⏳ Генерация файла и загрузка на Яндекс.Диск...")

    task = generate_upload_and_get_links.delay(
        message.from_user.id,
        message.from_user.username or str(message.from_user.id)
    )

    asyncio.create_task(check_task_and_send_result(bot, message.from_user.id, task.id))


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







