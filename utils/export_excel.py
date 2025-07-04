# from openpyxl import Workbook, load_workbook
# from slugify import slugify
# from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
# from openpyxl.utils import get_column_letter
# from datetime import datetime, timedelta, date
# from itertools import groupby
# import os
# from data.database import conn
# from collections import defaultdict
# import calendar


# def generate_user_excel(user_id: int, company_name: str, monday: date) -> str:
#     safe_name = slugify(company_name or str(user_id))

#     start_of_week = monday
#     end_of_week = monday + timedelta(days=6)        # Воскресенье

#     # Название файла с указанием недельного диапазона
#     filename = f"exports/user_{safe_name}_{start_of_week.strftime('%d-%m')}_{end_of_week.strftime('%d-%m')}.xlsx"
#     os.makedirs("exports", exist_ok=True)

#     cursor = conn.cursor()
#     cursor.execute("""
#         SELECT day, time, portion, created_at
#         FROM portions
#         WHERE user_id = ?
#         AND DATE(created_at) BETWEEN ? AND ?
#         ORDER BY created_at ASC
#     """, (
#         user_id,
#         start_of_week.strftime("%Y-%m-%d"),
#         end_of_week.strftime("%Y-%m-%d")
#     ))
#     rows = cursor.fetchall()

#     # Мапа: (day, time) -> (portion, created_at)
#     portion_map = {
#         (row[0], row[1]): (row[2], row[3])
#         for row in rows
#     }

#     wb = Workbook()
#     ws = wb.active
#     ws.title = "Заявки компании"

#     # Стили
#     bold_font = Font(bold=True)
#     header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
#     title_fill = PatternFill(start_color="BDD7EE", end_color="BDD7EE", fill_type="solid")
#     thin_border = Border(
#         left=Side(style="thin"), right=Side(style="thin"),
#         top=Side(style="thin"), bottom=Side(style="thin")
#     )

#     # Заголовки
#     ws.merge_cells("A1:D1")
#     ws["A1"].value = "Заявки на питание"
#     ws["A1"].font = Font(size=14, bold=True)
#     ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
#     ws["A1"].fill = title_fill
#     ws["A1"].border = thin_border

#     ws.merge_cells("A2:D2")
#     ws["A2"].value = f"Компания: {company_name}"
#     ws["A2"].font = Font(size=12, bold=True)
#     ws["A2"].alignment = Alignment(horizontal="left", vertical="center")
#     ws["A2"].border = thin_border

#     headers = ["День", "Время", "Порции", "Дата заявки"]
#     for col, header in enumerate(headers, start=1):
#         cell = ws.cell(row=4, column=col)
#         cell.value = header
#         cell.font = bold_font
#         cell.alignment = Alignment(horizontal="center", vertical="center")
#         cell.fill = header_fill
#         cell.border = thin_border

#     col_widths = {1: 15, 2: 15, 3: 15, 4: 20}
#     for col, width in col_widths.items():
#         ws.column_dimensions[get_column_letter(col)].width = width

#     # Времена
#     times = ["День", "Ночь", "Запайка"]
#     row_index = 5

#     for i in range(7):
#         current_day = start_of_week + timedelta(days=i)
#         day_str = current_day.strftime("%Y-%m-%d")

#         for time in times:
#             portion, created_at = portion_map.get((day_str, time), (0, "—"))

#             row_values = [day_str, time, portion, created_at]
#             for j, value in enumerate(row_values, start=1):
#                 cell = ws.cell(row=row_index, column=j)
#                 cell.value = value
#                 cell.alignment = Alignment(horizontal="center", vertical="center")
#                 cell.border = thin_border
#             row_index += 1

#     wb.save(filename)
#     return filename

# def _week_range(any_date: date) -> tuple[date, date]:
#     """Возвращает (понедельник, воскресенье) для ISO‑недели даты any_date."""
#     start = any_date - timedelta(days=any_date.weekday())
#     return start, start + timedelta(days=6)


# def generate_admin_excel(year: int, week: int) -> str:
#     # 🗂 Создание имени файла
#     filename = f"exports/admin_orders_{year}-W{week}.xlsx"
#     os.makedirs("exports", exist_ok=True)

#     # 🎯 Вычисляем даты начала и конца недели
#     monday = datetime.strptime(f'{year}-W{week}-1', "%Y-W%W-%w").date()
#     week_dates = [(monday + timedelta(days=i)) for i in range(7)]

#     # 📥 Получение данных из базы
#     cursor = conn.cursor()
#     cursor.execute("""
#         SELECT company_name, day, time, portion, created_at
#         FROM portions
#         ORDER BY created_at ASC
#     """)
#     rows = cursor.fetchall()

#     # 📊 Группируем по дате и компании
#     grouped = defaultdict(lambda: defaultdict(lambda: {"День": 0, "Ночь": 0, "Запайка": 0}))

#     for company_name, _, time, portion, created_at in rows:
#         created_date = created_at[:10]
#         created_dt = datetime.strptime(created_date, "%Y-%m-%d").date()
#         if created_dt in week_dates:
#             time_key = time.capitalize()
#             if time_key in grouped[created_dt][company_name]:
#                 grouped[created_dt][company_name][time_key] += portion

#     # ✍️ Начинаем писать Excel
#     wb = Workbook()
#     ws = wb.active
#     ws.title = f"Неделя {week}"

#     current_row = 1
#     bold_font = Font(bold=True)
#     header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
#     thin_border = Border(
#         left=Side(style="thin"), right=Side(style="thin"),
#         top=Side(style="thin"), bottom=Side(style="thin")
#     )

#     for day_date in week_dates:
#         companies = grouped.get(day_date, {})
#         if not companies:
#             # Если данных нет, всё равно создаём пустую таблицу
#             companies = {}

#         # 🟦 Заголовок дня
#         ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=6)
#         cell = ws.cell(row=current_row, column=1)
#         cell.value = f"Дата: {day_date.strftime('%d.%m.%Y')} ({day_date.strftime('%A')})"
#         cell.font = Font(size=12, bold=True, color="FFFFFF")
#         cell.alignment = Alignment(horizontal="center", vertical="center")
#         cell.fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
#         cell.border = thin_border
#         current_row += 1

#         # 🏷 Шапка
#         headers = ["Компания", "День", "Ночь", "Запайка", "Итого порций"]
#         for col, header in enumerate(headers, start=1):
#             cell = ws.cell(row=current_row, column=col)
#             cell.value = header
#             cell.font = bold_font
#             cell.alignment = Alignment(horizontal="center", vertical="center")
#             cell.fill = header_fill
#             cell.border = thin_border
#         current_row += 1

#         # 📄 Заполнение компаний
#         if companies:
#             for company, values in companies.items():
#                 day_p = values["День"]
#                 night_p = values["Ночь"]
#                 zap_p = values["Запайка"]
#                 total = day_p + night_p + zap_p
#                 row = [company, day_p, night_p, zap_p, total]
#                 for col, val in enumerate(row, start=1):
#                     cell = ws.cell(row=current_row, column=col)
#                     cell.value = val
#                     cell.alignment = Alignment(horizontal="center", vertical="center")
#                     cell.border = thin_border
#                 current_row += 1
#         else:
#             # 🟨 Пустая строка если данных нет
#             cell = ws.cell(row=current_row, column=1)
#             cell.value = "Нет заявок"
#             cell.alignment = Alignment(horizontal="center", vertical="center")
#             cell.border = thin_border
#             current_row += 1

#         current_row += 1  # пустая строка между днями

#     # 📏 Автоширина
#     for col in ws.columns:
#         max_len = max(len(str(cell.value)) if cell.value else 0 for cell in col)
#         ws.column_dimensions[get_column_letter(col[0].column)].width = max_len + 2

#     wb.save(filename)
#     return filename

# utils/export_excel.py
from collections import defaultdict
from datetime import date, datetime, timedelta
import os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from slugify import slugify

from data.database import conn

DAYS_RU = ["Понедельник", "Вторник", "Среда",
           "Четверг", "Пятница", "Суббота", "Воскресенье"]


# ---------- USER REPORT --------------------------------------------------
def generate_user_excel(user_id: int, company_name: str, monday: date) -> str:
    """
    Формирует Excel‑отчёт компании за неделю, начинающуюся с monday (ISO‑дата понедельника).
    Возвращает локальный путь к файлу.
    """
    safe = slugify(company_name or user_id)
    sunday = monday + timedelta(days=6)
    fname  = f"exports/user_{safe}_{monday:%d-%m}_{sunday:%d-%m}.xlsx"
    os.makedirs("exports", exist_ok=True)

    cur = conn.cursor()
    cur.execute(
        """
        SELECT day, time, portion, created_at
        FROM   portions
        WHERE  user_id=? AND day BETWEEN ? AND ?
        ORDER  BY day, time
        """,
        (user_id, monday.isoformat(), sunday.isoformat()),
    )
    rows = cur.fetchall()                                    # (iso_day, time, portion, created)

    # (day,time) -> (portion, created_at)
    m = {(d, t): (p, c) for d, t, p, c in rows}

    # wb, ws = Workbook(), Workbook().active
    wb = Workbook()
    ws = wb.active 
    ws.title = "Заявки компании"

    # ---- стили -----------------------------------------------------------
    bold  = Font(bold=True)
    hfill = PatternFill("solid", start_color="D9E1F2")
    tfill = PatternFill("solid", start_color="BDD7EE")
    border = Border(*(Side("thin"),)*4)

    # ---- шапка -----------------------------------------------------------
    ws.merge_cells("A1:D1")
    ws["A1"].value, ws["A1"].font, ws["A1"].alignment, ws["A1"].fill = (
        "Заявки на питание", Font(size=14, bold=True), Alignment("center"), tfill
    )
    ws["A1"].border = border

    ws.merge_cells("A2:D2")
    ws["A2"].value, ws["A2"].font = f"Компания: {company_name}", Font(size=12, bold=True)
    ws["A2"].border = border

    headers = ["День", "Время", "Порции", "Дата заявки"]
    ws.append(headers)
    for c in ws[3]:
        c.font, c.alignment, c.fill, c.border = bold, Alignment("center"), hfill, border

    # ---- данные ----------------------------------------------------------
    times = ["День", "Ночь", "Запайка"]
    for i in range(7):
        d = monday + timedelta(days=i)
        iso = d.isoformat()
        for t in times:
            portion, created = m.get((iso, t), (0, "—"))
            ws.append([iso, t, portion, created])
            for cell in ws[ws.max_row]:
                cell.alignment, cell.border = Alignment("center"), border

    # ---- автоширина ------------------------------------------------------
    for col in ws.columns:
        ws.column_dimensions[get_column_letter(col[0].column)].width = max(
            len(str(c.value)) if c.value else 0 for c in col
        ) + 2

    wb.save(fname)
    return fname


# ---------- ADMIN REPORT -------------------------------------------------
def generate_admin_excel(year: int, week_num: int) -> str:
    """
    Формирует общий отчёт за ISO‑неделю year‑Wweek_num (понедельник‑воскресенье)
    по всем компаниям. Файл сохраняется в ./exports и возвращается его путь.
    """
    monday  = datetime.fromisocalendar(year, week_num, 1).date()
    sunday  = monday + timedelta(days=6)
    fname   = f"exports/admin_orders_{year}-W{week_num:02d}.xlsx"
    os.makedirs("exports", exist_ok=True)

    # ---- Читаем БД -------------------------------------------------------
    cur = conn.cursor()
    cur.execute(
        """
        SELECT company_name,
               day,                -- ISO‑дата (TEXT)
               time,               -- 'День' | 'Ночь' | 'Запайка'
               SUM(portion)        -- суммуем сразу
        FROM   portions
        WHERE  day BETWEEN ? AND ?
        GROUP  BY company_name, day, time
        """,
        (monday.isoformat(), sunday.isoformat()),
    )
    rows = cur.fetchall()            # (comp, iso_day, time, sum_portion)

    # company → {(iso_day, time) → portion}
    data: dict[str, dict[tuple[str, str], int]] = defaultdict(dict)
    for comp, iso_d, t, total in rows:
        data[comp][(iso_d, t.capitalize())] = total

    # ---- Создаём Excel ---------------------------------------------------
    wb  = Workbook()
    ws  = wb.active
    ws.title = f"W{week_num:02d}"

    # Стили
    bold   = Font(bold=True)
    tfill  = PatternFill("solid", start_color="BDD7EE")
    hfill  = PatternFill("solid", start_color="D9E1F2")
    border = Border(*(Side("thin"),)*4)

    # Заголовок файла
    ws.merge_cells("A1:F1")
    top = ws["A1"]
    top.value = f"Календарь заявок {year}-W{week_num:02d} " \
                f"({monday:%d.%m}–{sunday:%d.%m})"
    top.font, top.alignment, top.fill = Font(size=14, bold=True), Alignment("center"), tfill
    top.border = border

    # Шапка таблицы
    ws.append(["Компания", "Дата", "День", "Ночь", "Запайка", "Итого"])
    for c in ws[2]:
        c.font, c.alignment, c.fill, c.border = bold, Alignment("center"), hfill, border

    times = ["День", "Ночь", "Запайка"]
    row_i = 3

    for comp, recs in data.items():
        for i in range(7):
            d        = monday + timedelta(days=i)
            iso_d    = d.isoformat()
            portions = [recs.get((iso_d, t), 0) for t in times]
            total    = sum(portions)

            ws.append([comp, iso_d, *portions, total])
            for c in ws[row_i]:
                c.alignment, c.border = Alignment("center"), border
            row_i += 1

        # пустая разделительная строка
        ws.append([])
        row_i += 1

    # Авто‑ширина
    for col in ws.columns:
        ws.column_dimensions[get_column_letter(col[0].column)].width = (
            max(len(str(c.value)) if c.value else 0 for c in col) + 2
        )

    wb.save(fname)
    return fname