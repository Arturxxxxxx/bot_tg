# from keybords.day_select import day_select_keyboard
# from keybords.time_select import time_select_keyboard
# from keybords.main_kb import main_menu_kb
# from aiogram import Router, F, Bot
# from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
# from aiogram.fsm.context import FSMContext
# from datetime import datetime
# from celery.result import AsyncResult
# from states.load_states import LoadDataStates
# from utils.upload_excel import generate_upload_and_get_links
# from data.database import conn
# import asyncio

# router = Router()

# DAYS_FULL = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

# def get_available_days(week: str) -> list:
#     today = datetime.today()
#     weekday_index = today.weekday()  # 0 = Monday, 6 = Sunday

#     if week == "current":
#         return DAYS_FULL[weekday_index:]  # Возвращаем только оставшиеся дни
#     else:
#         return DAYS_FULL  # Вся неделя

# @router.message(F.text == "📥 Загрузить данные")
# async def start_load_data(message: Message, state: FSMContext):
#     await message.answer(
#         "Выберите время суток:",
#         reply_markup=time_select_keyboard()
#     )
#     await state.set_state(LoadDataStates.choosing_time)


# @router.message(LoadDataStates.choosing_time)
# async def choose_time(message: Message, state: FSMContext):
#     if message.text == "🔙 Назад":
#         await message.answer("Операция отменена.", reply_markup=main_menu_kb())
#         await state.clear()
#         return

#     await state.update_data(time=message.text)

#     await message.answer(
#         "Выберите неделю:",
#         reply_markup=ReplyKeyboardMarkup(keyboard=[
#             [KeyboardButton(text="📅 Текущая неделя")],
#             [KeyboardButton(text="🗓 Следующая неделя")],
#             [KeyboardButton(text="🔙 Назад")],
#         ], resize_keyboard=True)
#     )
#     await state.set_state(LoadDataStates.choosing_week)


# @router.message(LoadDataStates.choosing_week)
# async def choose_week(message: Message, state: FSMContext):
#     if message.text == "🔙 Назад":
#         await message.answer("Выберите время суток:", reply_markup=time_select_keyboard())
#         await state.set_state(LoadDataStates.choosing_time)
#         return

#     week = message.text.strip()
#     if week not in ["📅 Текущая неделя", "🗓 Следующая неделя"]:
#         await message.answer("Выберите корректную неделю.")
#         return

#     week_key = "current" if week == "📅 Текущая неделя" else "next"
#     await state.update_data(week=week_key)

#     available_days = get_available_days(week_key)
#     if not available_days:
#         await message.answer("На эту неделю нет доступных дней.")
#         return

#     keyboard = day_select_keyboard(available_days)
#     await message.answer("Выберите день недели:", reply_markup=keyboard)
#     await state.set_state(LoadDataStates.choosing_day)


# @router.message(LoadDataStates.choosing_day)
# async def choose_day(message: Message, state: FSMContext):
#     if message.text == "🔙 Назад":
#         week = (await state.get_data()).get("week", "current")
#         keyboard = ReplyKeyboardMarkup(keyboard=[
#             [KeyboardButton(text="📅 Текущая неделя")],
#             [KeyboardButton(text="🗓 Следующая неделя")],
#             [KeyboardButton(text="🔙 Назад")],
#         ], resize_keyboard=True)
#         await message.answer("Выберите неделю:", reply_markup=keyboard)
#         await state.set_state(LoadDataStates.choosing_week)
#         return

#     await state.update_data(day=message.text)
#     await message.answer("Введите количество порций (только число):")
#     await state.set_state(LoadDataStates.entering_portion)

# @router.message(LoadDataStates.entering_portion)
# async def enter_portion(message: Message, state: FSMContext, bot: Bot):
#     if not message.text.isdigit():
#         await message.answer("Введите только число или нажмите 🔙 для отмены.")
#         return

#     portion = int(message.text)
#     data = await state.get_data()

#     day = data['day']
#     time = data['time']
#     week = data.get('week', 'current')
#     user_id = message.from_user.id
#     username = message.from_user.username or f"id_{user_id}"

#     cursor = conn.cursor()

#     # Проверка: была ли уже заявка
#     cursor.execute("""
#         SELECT id, portion FROM portions
#         WHERE user_id = ? AND week = ? AND day = ? AND time = ?
#     """, (user_id, week, day, time))
#     existing = cursor.fetchone()

#     portion_diff_str = ""
#     if existing:
#         portion_id, old_portion = existing
#         diff = portion - old_portion
#         if diff > 0:
#             portion_diff_str = f" (⏫ +{diff})"
#         elif diff < 0:
#             portion_diff_str = f" (⏬ {diff})"

#         cursor.execute("""
#             UPDATE portions SET portion = ?, created_at = ?
#             WHERE id = ?
#         """, (portion, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), portion_id))
#     else:
#         cursor.execute("""
#             INSERT INTO portions (user_id, username, day, time, portion, created_at, week)
#             VALUES (?, ?, ?, ?, ?, ?, ?)
#         """, (
#             user_id,
#             username,
#             day,
#             time,
#             portion,
#             datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
#             week
#         ))

#     conn.commit()

#     # Задача отправки в Яндекс.Диск
#     task = generate_upload_and_get_links.delay(user_id, username)
#     asyncio.create_task(check_task_and_send_result(bot, user_id, task.id))

#     await message.answer(
#         f"✅ Данные обновлены:\n"
#         f"📅 {day} | 🕒 {time} | 🗓 Неделя: {'эта' if week == 'current' else 'следующая'}\n"
#         f"🍽️ {portion} порций{portion_diff_str}",
#         reply_markup=main_menu_kb()
#     )
#     await state.clear()


# async def check_task_and_send_result(bot, chat_id, task_id):
#     for _ in range(20):
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


from keybords.day_select import day_select_keyboard
from keybords.time_select import time_select_keyboard
from keybords.main_kb import main_menu_kb
from aiogram import Router, F, Bot
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
from aiogram.fsm.context import FSMContext
from datetime import datetime
from celery.result import AsyncResult
from states.load_states import LoadDataStates
from utils.upload_excel import generate_upload_and_get_links
from data.database import conn
import asyncio
import logging

router = Router()

DAYS_FULL = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

CURRENT_WEEK = "📅 Текущая неделя"
NEXT_WEEK = "🗓 Следующая неделя"
BACK_BUTTON = "🔙 Назад"

MAX_CELERY_WAIT_SECONDS = 20


def week_select_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=CURRENT_WEEK)],
        [KeyboardButton(text=NEXT_WEEK)],
        [KeyboardButton(text=BACK_BUTTON)],
    ], resize_keyboard=True)


def get_available_days(week: str) -> list:
    today = datetime.today()
    weekday_index = today.weekday()  # 0 = Monday, 6 = Sunday
    return DAYS_FULL[weekday_index:] if week == "current" else DAYS_FULL


@router.message(F.text == "📥 Загрузить данные")
async def start_load_data(message: Message, state: FSMContext):
    await message.answer("Выберите время суток:", reply_markup=time_select_keyboard())
    await state.set_state(LoadDataStates.choosing_time)


@router.message(LoadDataStates.choosing_time)
async def choose_time(message: Message, state: FSMContext):
    if message.text not in ["Запайка", "День", "Ночь", BACK_BUTTON]:  # замените на ваши кнопки
        await message.answer("Пожалуйста, выберите время суток, используя кнопки ниже.")
        return

    if message.text == BACK_BUTTON:
        await message.answer("Операция отменена.", reply_markup=main_menu_kb())
        await state.clear()
        return

    await state.update_data(time=message.text)
    await message.answer("Выберите неделю:", reply_markup=week_select_keyboard())
    await state.set_state(LoadDataStates.choosing_week)



@router.message(LoadDataStates.choosing_week)
async def choose_week(message: Message, state: FSMContext):
    if message.text not in [CURRENT_WEEK, NEXT_WEEK, BACK_BUTTON]:
        await message.answer("Пожалуйста, выберите неделю, используя кнопки.")
        return

    if message.text == BACK_BUTTON:
        await message.answer("Выберите время суток:", reply_markup=time_select_keyboard())
        await state.set_state(LoadDataStates.choosing_time)
        return

    week_key = "current" if message.text == CURRENT_WEEK else "next"
    await state.update_data(week=week_key)

    available_days = get_available_days(week_key)
    keyboard = day_select_keyboard(available_days)
    await message.answer("Выберите день недели:", reply_markup=keyboard)
    await state.set_state(LoadDataStates.choosing_day)



@router.message(LoadDataStates.choosing_day)
async def choose_day(message: Message, state: FSMContext):
    data = await state.get_data()
    week = data.get("week", "current")
    valid_days = get_available_days(week) + [BACK_BUTTON]

    if message.text not in valid_days:
        await message.answer("Пожалуйста, выберите день недели, используя кнопки.")
        return

    if message.text == BACK_BUTTON:
        await message.answer("Выберите неделю:", reply_markup=week_select_keyboard())
        await state.set_state(LoadDataStates.choosing_week)
        return

    await state.update_data(day=message.text)
    await message.answer("Введите количество порций (только число):")
    await state.set_state(LoadDataStates.entering_portion)


@router.message(LoadDataStates.entering_portion)
async def enter_portion(message: Message, state: FSMContext, bot: Bot):
    if message.text == BACK_BUTTON:
        await message.answer("Выберите день недели снова:")
        data = await state.get_data()
        week = data.get("week", "current")
        keyboard = day_select_keyboard(get_available_days(week))
        await message.answer("Выберите день недели:", reply_markup=keyboard)
        await state.set_state(LoadDataStates.choosing_day)
        return
    
    if not message.text.isdigit():
        await message.answer("Введите только число или нажмите 🔙 для отмены.")
        return

    portion = int(message.text)
    data = await state.get_data()
    day, time, week = data['day'], data['time'], data.get('week', 'current')
    user_id, username = message.from_user.id, message.from_user.username or f"id_{message.from_user.id}"

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, portion FROM portions
            WHERE user_id = ? AND week = ? AND day = ? AND time = ?
        """, (user_id, week, day, time))
        existing = cursor.fetchone()

        portion_diff_str = ""
        if existing:
            portion_id, old_portion = existing
            diff = portion - old_portion
            portion_diff_str = f" (⏫ +{diff})" if diff > 0 else f" (⏬ {diff})" if diff < 0 else ""
            cursor.execute("""
                UPDATE portions SET portion = ?, created_at = ?
                WHERE id = ?
            """, (portion, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), portion_id))
        else:
            cursor.execute("""
                INSERT INTO portions (user_id, username, day, time, portion, created_at, week)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                username,
                day,
                time,
                portion,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                week
            ))
        conn.commit()
    except Exception as e:
        logging.exception("Ошибка при работе с БД")
        await message.answer("Произошла ошибка при сохранении данных.")
        return

    task = generate_upload_and_get_links.delay(user_id, username)
    asyncio.create_task(check_task_and_send_result(bot, user_id, task.id))

    await message.answer(
        f"✅ Данные обновлены:\n"
        f"📅 {day} | 🕒 {time} | 🗓 Неделя: {'эта' if week == 'current' else 'следующая'}\n"
        f"🍽️ {portion} порций{portion_diff_str}",
        reply_markup=main_menu_kb()
    )
    await state.clear()


async def check_task_and_send_result(bot: Bot, chat_id: int, task_id: str):
    for _ in range(MAX_CELERY_WAIT_SECONDS):
        await asyncio.sleep(1)
        result = AsyncResult(task_id)
        if result.ready():
            if result.successful():
                try:
                    data = result.get(timeout=2)
                    user_link = data.get("user_link")
                    if user_link:
                        await bot.send_message(chat_id, f"Ваш файл готов! Вот ссылка:\n{user_link}")
                    else:
                        await bot.send_message(chat_id, "Файл с вашими данными не найден.")
                except Exception as e:
                    logging.exception("Ошибка при получении данных из задачи")
                    await bot.send_message(chat_id, "Произошла ошибка при обработке результата.")
            else:
                logging.error(f"Celery task failed: {result.result}")
                await bot.send_message(chat_id, "Произошла ошибка при генерации файла.")
            return
    await bot.send_message(chat_id, "Время ожидания истекло. Попробуйте позже.")
