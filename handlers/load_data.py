from keybords.day_select import day_select_keyboard
from keybords.time_select import time_select_keyboard
from keybords.main_kb import main_menu_kb
from aiogram import Router, F, Bot
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from datetime import datetime
from celery.result import AsyncResult
from states.load_states import LoadDataStates
from utils.upload_excel import generate_upload_and_get_links
from data.database import conn
from datetime import datetime, time, timedelta, date
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



def get_available_day_options(week: str) -> list[tuple[str, str]]:
    """
    Возвращает список доступных дней в виде кортежей:
    (название дня недели, ISO-дата этого дня)
    """
    today = datetime.now()
    weekday_index = today.weekday()  # 0 = Monday
    noon = time(12, 0)

    # Понедельник выбранной недели
    if week == "next":
        monday = today.date() + timedelta(days=7 - weekday_index)
    else:
        monday = today.date() - timedelta(days=weekday_index)

    days = []
    for i in range(7):
        current_day = monday + timedelta(days=i)
        is_today = current_day == today.date()

        if week == "current":
            if current_day <= today.date():
                continue  # Пропускаем сегодня и все предыдущие
            if today.time() >= noon and current_day == today.date() + timedelta(days=1):
                continue  # После 12:00 — пропускаем и завтра

        day_name = DAYS_FULL[i]
        iso_date = current_day.isoformat()
        days.append((day_name, iso_date))

    return days


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

    day_options = get_available_day_options(week_key)
    keyboard = day_select_keyboard(day_options)

    # Сохраняем список допустимых дней в FSMContext
    await state.update_data(day_options=day_options)

    await message.answer("Выберите день недели:", reply_markup=keyboard)
    await state.set_state(LoadDataStates.choosing_day)




@router.message(LoadDataStates.choosing_day)
async def choose_day(message: Message, state: FSMContext):
    data = await state.get_data()
    week = data.get("week", "current")
    day_options = data.get("day_options", [])
    valid_day_names = [d[0] for d in day_options] + [BACK_BUTTON]

    if message.text not in valid_day_names:
        await message.answer("Пожалуйста, выберите день недели, используя кнопки.")
        return

    if message.text == BACK_BUTTON:
        await message.answer("Выберите неделю:", reply_markup=week_select_keyboard())
        await state.set_state(LoadDataStates.choosing_week)
        return

    # Получаем iso-дату по названию дня
    day_name = message.text
    day_date = next((date for name, date in day_options if name == day_name), None)

    if not day_date:
        await message.answer("Ошибка: не удалось определить дату выбранного дня.")
        return

    await state.update_data(day=day_name, day_date=day_date)

    await message.answer(
        "Введите количество порций (только число):",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(LoadDataStates.entering_portion)




@router.message(LoadDataStates.entering_portion)
async def enter_portion(message: Message, state: FSMContext, bot: Bot):
    # ----- отмена --------------------------------------------------------
    if message.text == BACK_BUTTON:
        d = await state.get_data()
        week_key = d.get("week", "current")
        days_kb = day_select_keyboard(
            [name for name, _ in get_available_day_options(week_key)]
        )
        await message.answer("Выберите день недели:", reply_markup=days_kb)
        await state.set_state(LoadDataStates.choosing_day)
        return

    # ----- валидация числа ----------------------------------------------
    if not message.text.isdigit():
        await message.answer("Введите только число или нажмите 🔙 Назад.")
        return
    portion = int(message.text)

    # ----- данные из FSM --------------------------------------------------
    data = await state.get_data()
    day_iso   = data["day_date"]      # '2025‑07‑09'
    time_slot = data["time"]          # День | Ночь | Запайка
    week_key  = data.get("week", "current")
    user_id   = message.from_user.id

    # понедельник «целевой» недели
    sel_dt          = datetime.fromisoformat(day_iso).date()
    monday_of_week  = sel_dt - timedelta(days=sel_dt.weekday())

    # ----- компания пользователя -----------------------------------------
    cur = conn.cursor()
    cur.execute("""
        SELECT c.name
        FROM   companies c
        JOIN   user_company uc ON uc.company_id = c.id
        WHERE  uc.user_id = ?
    """, (user_id,))
    row = cur.fetchone()
    if not row:
        await message.answer("❌ Не удалось определить вашу компанию.", reply_markup=main_menu_kb())
        return
    company_name = row[0]

    # ----- запись / обновление -------------------------------------------
    try:
        cur.execute("""
            SELECT id, portion
            FROM   portions
            WHERE  user_id=? AND day=? AND time=?
        """, (user_id, day_iso, time_slot))
        existing = cur.fetchone()

        diff_note = ""
        now_str   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        NOTIFY_CHAT_ID = -4978614010  # ← сюда вставь ID группы/чата для уведомлений

        if existing:
            pid, prev = existing
            diff = portion - prev
            diff_note = f" (⏫ +{diff})" if diff > 0 else f" (⏬ {diff})" if diff < 0 else ""

            cur.execute(
                "UPDATE portions SET portion=?, created_at=? WHERE id=?",
                (portion, now_str, pid)
            )

            if diff != 0:
                # Формируем уведомление об изменении
                msg = (
                    f"🔄 Изменение порций\n"
                    f"👤 Пользователь: {message.from_user.full_name} (@{message.from_user.username})\n"
                    f"🏢 Компания: {company_name}\n"
                    f"📅 {day_iso} | 🕒 {time_slot}\n"
                    f"🍽 Было: {prev} → Стало: {portion}"
                )
                try:
                    await bot.send_message(NOTIFY_CHAT_ID, msg)
                except Exception:
                    logging.exception("Не удалось отправить уведомление об изменении порций")

        else:
            cur.execute("""
                INSERT INTO portions
                (user_id, company_name, day, time, portion,
                 created_at, week_monday, week_key)
                VALUES (?,?,?,?,?,?,?,?)
            """, (user_id, company_name, day_iso, time_slot,
                  portion, now_str, monday_of_week.isoformat(), week_key))
        conn.commit()
    except Exception:
        logging.exception("Ошибка при работе с БД")
        await message.answer("Произошла ошибка при сохранении данных.")
        return

    # ----- создаём отчёты -------------------------------------------------
    # вычисляем ISO‑год и номер недели выбранной даты
    year, week_num, _ = sel_dt.isocalendar()

    task = generate_upload_and_get_links.delay(
        user_id=user_id,
        company_name=company_name,
        year=year,
        week_num=week_num          # ← передаём!
    )
    asyncio.create_task(check_task_and_send_result(bot, user_id, task.id))

    # ----- ответ пользователю --------------------------------------------
    week_label = "эта" if week_key == "current" else "следующая"
    await message.answer(
        f"✅ Данные обновлены:\n"
        f"📅 {day_iso} | 🕒 {time_slot} | 🗓 Неделя: {week_label}\n"
        f"🍽 {portion} порций{diff_note}",
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
