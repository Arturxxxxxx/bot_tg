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


def generate_admin_excel(year: int, week_num: int) -> str:
    """Генерирует Excel‑файл с заявками за ISO‑неделю year‑Wweek_num."""
    monday = datetime.fromisocalendar(year, week_num, 1).date()
    sunday = monday + timedelta(days=6)

    file_name = f"admin_orders_{year}-W{week_num:02d}.xlsx"
    file_path = os.path.join("exports", file_name)
    os.makedirs("exports", exist_ok=True)

    # ---- читаем БД ---------------------------------------------------------
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT company_name, DATE(created_at) as d, time, portion, created_at
        FROM portions
        WHERE DATE(created_at) BETWEEN ? AND ?
        ORDER BY company_name, created_at
        """,
        (monday.isoformat(), sunday.isoformat()),
    )
    rows = cursor.fetchall()

    # company → {(day, time): (portion, created_at)}
    data = defaultdict(dict)
    for comp, d, t, p, created in rows:
        data[comp][(d, t.capitalize())] = (p, created)

    # ---- создаём Excel -----------------------------------------------------
    wb = Workbook()
    ws = wb.active
    ws.title = f"W{week_num:02d}"

    title_fill  = PatternFill("solid", start_color="BDD7EE")
    header_fill = PatternFill("solid", start_color="D9E1F2")
    border = Border(*(Side("thin"),) * 4)
    bold = Font(bold=True)

    ws.merge_cells("A1:G1")
    ws["A1"].value = f"Календарь заявок {year}-W{week_num:02d} ({monday:%d.%m}–{sunday:%d.%m})"
    ws["A1"].font, ws["A1"].alignment, ws["A1"].fill = Font(size=14, bold=True), Alignment(horizontal="center"), title_fill
    ws["A1"].border = border

    headers = ["Компания", "Дата", "День", "Ночь", "Запайка", "Итого"]
    ws.append(headers)
    for c in ws[2]:
        c.font, c.alignment, c.fill, c.border = bold, Alignment(horizontal="center"), header_fill, border

    times = ["День", "Ночь", "Запайка"]
    cur_row = 3

    for company, recs in data.items():
        for i in range(7):
            d = monday + timedelta(days=i)
            d_str = d.isoformat()

            portions = []
            created_at = "—"
            for t in times:
                portion, created = recs.get((d_str, t), (0, "—"))
                portions.append(portion)
                if created_at == "—" and created != "—":
                    created_at = created

            total = sum(portions)
            row = [company, d_str, *portions, total]
            ws.append(row)

            for j, val in enumerate(row, start=1):
                cell = ws.cell(row=cur_row, column=j)
                cell.alignment = Alignment(horizontal="center")
                cell.border = border
            cur_row += 1

        # пустая строка‑разделитель между компаниями
        ws.append([])
        cur_row += 1

    # авто‑ширина
    for col in ws.columns:
        length = max(len(str(c.value)) if c.value else 0 for c in col)
        ws.column_dimensions[get_column_letter(col[0].column)].width = length + 2

    wb.save(file_path)
    return file_path