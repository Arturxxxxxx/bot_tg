from openpyxl import Workbook, load_workbook
from slugify import slugify
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime, timedelta, date
from itertools import groupby
import os
from data.database import conn
from collections import defaultdict
import calendar


def generate_user_excel(user_id: int, company_name: str) -> str:
    safe_name = slugify(company_name or str(user_id))

    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())  # Понедельник
    end_of_week = start_of_week + timedelta(days=6)          # Воскресенье

    # Название файла с указанием недельного диапазона
    filename = f"exports/user_{safe_name}_{start_of_week.strftime('%d-%m')}_{end_of_week.strftime('%d-%m')}.xlsx"
    os.makedirs("exports", exist_ok=True)

    cursor = conn.cursor()
    cursor.execute("""
        SELECT day, time, portion, created_at
        FROM portions
        WHERE user_id = ?
        AND DATE(created_at) BETWEEN ? AND ?
        ORDER BY created_at ASC
    """, (
        user_id,
        start_of_week.strftime("%Y-%m-%d"),
        end_of_week.strftime("%Y-%m-%d")
    ))
    rows = cursor.fetchall()

    # Мапа: (day, time) -> (portion, created_at)
    portion_map = {
        (row[0], row[1]): (row[2], row[3])
        for row in rows
    }

    wb = Workbook()
    ws = wb.active
    ws.title = "Заявки компании"

    # Стили
    bold_font = Font(bold=True)
    header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    title_fill = PatternFill(start_color="BDD7EE", end_color="BDD7EE", fill_type="solid")
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin")
    )

    # Заголовки
    ws.merge_cells("A1:D1")
    ws["A1"].value = "Заявки на питание"
    ws["A1"].font = Font(size=14, bold=True)
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws["A1"].fill = title_fill
    ws["A1"].border = thin_border

    ws.merge_cells("A2:D2")
    ws["A2"].value = f"Компания: {company_name}"
    ws["A2"].font = Font(size=12, bold=True)
    ws["A2"].alignment = Alignment(horizontal="left", vertical="center")
    ws["A2"].border = thin_border

    headers = ["День", "Время", "Порции", "Дата заявки"]
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=4, column=col)
        cell.value = header
        cell.font = bold_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.fill = header_fill
        cell.border = thin_border

    col_widths = {1: 15, 2: 15, 3: 15, 4: 20}
    for col, width in col_widths.items():
        ws.column_dimensions[get_column_letter(col)].width = width

    # Времена
    times = ["День", "Ночь", "Запайка"]
    row_index = 5

    for i in range(7):
        current_day = start_of_week + timedelta(days=i)
        day_str = current_day.strftime("%Y-%m-%d")

        for time in times:
            portion, created_at = portion_map.get((day_str, time), (0, "—"))

            row_values = [day_str, time, portion, created_at]
            for j, value in enumerate(row_values, start=1):
                cell = ws.cell(row=row_index, column=j)
                cell.value = value
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = thin_border
            row_index += 1

    wb.save(filename)
    return filename

def _week_range(any_date: date) -> tuple[date, date]:
    """Возвращает (понедельник, воскресенье) для ISO‑недели даты any_date."""
    start = any_date - timedelta(days=any_date.weekday())
    return start, start + timedelta(days=6)


def generate_admin_excel(year: int, week: int) -> str:
    # 🗂 Создание имени файла
    filename = f"exports/admin_orders_{year}-W{week}.xlsx"
    os.makedirs("exports", exist_ok=True)

    # 🎯 Вычисляем даты начала и конца недели
    monday = datetime.strptime(f'{year}-W{week}-1', "%Y-W%W-%w").date()
    week_dates = [(monday + timedelta(days=i)) for i in range(7)]

    # 📥 Получение данных из базы
    cursor = conn.cursor()
    cursor.execute("""
        SELECT company_name, day, time, portion, created_at
        FROM portions
        ORDER BY created_at ASC
    """)
    rows = cursor.fetchall()

    # 📊 Группируем по дате и компании
    grouped = defaultdict(lambda: defaultdict(lambda: {"День": 0, "Ночь": 0, "Запайка": 0}))

    for company_name, _, time, portion, created_at in rows:
        created_date = created_at[:10]
        created_dt = datetime.strptime(created_date, "%Y-%m-%d").date()
        if created_dt in week_dates:
            time_key = time.capitalize()
            if time_key in grouped[created_dt][company_name]:
                grouped[created_dt][company_name][time_key] += portion

    # ✍️ Начинаем писать Excel
    wb = Workbook()
    ws = wb.active
    ws.title = f"Неделя {week}"

    current_row = 1
    bold_font = Font(bold=True)
    header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin")
    )

    for day_date in week_dates:
        companies = grouped.get(day_date, {})
        if not companies:
            # Если данных нет, всё равно создаём пустую таблицу
            companies = {}

        # 🟦 Заголовок дня
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=6)
        cell = ws.cell(row=current_row, column=1)
        cell.value = f"Дата: {day_date.strftime('%d.%m.%Y')} ({day_date.strftime('%A')})"
        cell.font = Font(size=12, bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
        cell.border = thin_border
        current_row += 1

        # 🏷 Шапка
        headers = ["Компания", "День", "Ночь", "Запайка", "Итого порций"]
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=current_row, column=col)
            cell.value = header
            cell.font = bold_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.fill = header_fill
            cell.border = thin_border
        current_row += 1

        # 📄 Заполнение компаний
        if companies:
            for company, values in companies.items():
                day_p = values["День"]
                night_p = values["Ночь"]
                zap_p = values["Запайка"]
                total = day_p + night_p + zap_p
                row = [company, day_p, night_p, zap_p, total]
                for col, val in enumerate(row, start=1):
                    cell = ws.cell(row=current_row, column=col)
                    cell.value = val
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    cell.border = thin_border
                current_row += 1
        else:
            # 🟨 Пустая строка если данных нет
            cell = ws.cell(row=current_row, column=1)
            cell.value = "Нет заявок"
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border
            current_row += 1

        current_row += 1  # пустая строка между днями

    # 📏 Автоширина
    for col in ws.columns:
        max_len = max(len(str(cell.value)) if cell.value else 0 for cell in col)
        ws.column_dimensions[get_column_letter(col[0].column)].width = max_len + 2

    wb.save(filename)
    return filename