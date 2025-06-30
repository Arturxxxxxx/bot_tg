from openpyxl import Workbook, load_workbook
from slugify import slugify
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime
from itertools import groupby
import os
from data.database import conn
from collections import defaultdict
import calendar


def generate_user_excel(user_id: int, company_name: str) -> str:
    safe_name = slugify(company_name or str(user_id))
    filename = f"exports/user_{safe_name}.xlsx"

    os.makedirs("exports", exist_ok=True)

    cursor = conn.cursor()
    cursor.execute("""
        SELECT day, time, portion, created_at
        FROM portions
        WHERE user_id = ?
        ORDER BY created_at ASC
    """, (user_id,))
    rows = cursor.fetchall()

    bold_font = Font(bold=True)
    header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin")
    )

    row_start = 4

    if os.path.exists(filename):
        wb = load_workbook(filename)
        ws = wb.active
        # Очистка старых данных
        for row in ws.iter_rows(min_row=5, max_row=ws.max_row):
            for cell in row:
                cell.value = None
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = "Заявки компании"

        ws.merge_cells("A1:D1")
        ws["A1"].value = "Заявки на питание"
        ws["A1"].font = Font(size=14, bold=True)
        ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
        ws["A1"].fill = PatternFill(start_color="BDD7EE", end_color="BDD7EE", fill_type="solid")
        ws["A1"].border = thin_border

        ws.merge_cells("A2:D2")
        ws["A2"].value = f"Компания: {company_name}"
        ws["A2"].font = Font(size=12, bold=True)
        ws["A2"].alignment = Alignment(horizontal="left", vertical="center")
        ws["A2"].border = thin_border

        headers = ["День", "Время", "Порции", "Дата заявки"]
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=row_start, column=col)
            cell.value = header
            cell.font = bold_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.fill = header_fill
            cell.border = thin_border

        col_widths = {1: 15, 2: 15, 3: 15, 4: 20}
        for col, width in col_widths.items():
            ws.column_dimensions[get_column_letter(col)].width = width

    portion_map = {}

    for i, row in enumerate(rows, start=row_start + 1):
        day, time, portion, created_at = row
        key = f"{day}|{time}"

        portion_display = str(portion)
        if key in portion_map:
            prev = portion_map[key]
            diff = portion - prev
            if diff > 0:
                portion_display = f"{portion} (+{diff})"
            elif diff < 0:
                portion_display = f"{portion} ({diff})"

        portion_map[key] = portion

        row_values = [day, time, portion_display, created_at]
        for j, value in enumerate(row_values, start=1):
            cell = ws.cell(row=i, column=j)
            cell.value = value
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border

    wb.save(filename)
    return filename


def generate_admin_excel() -> str:
    os.makedirs("exports", exist_ok=True)

    cursor = conn.cursor()
    cursor.execute("""
        SELECT company_name, day, time, portion, created_at
        FROM portions
        ORDER BY created_at ASC
    """)
    rows = cursor.fetchall()

    # 🔁 Группировка по (год, номер_недели)
    weekly_data = defaultdict(list)
    for company_name, day, time, portion, created_at in rows:
        dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
        year, week_num, _ = dt.isocalendar()
        weekly_data[(year, week_num)].append((company_name, day, time, portion, created_at))

    saved_files = []  # Для возврата списка путей к файлам

    for (year, week_num), week_rows in weekly_data.items():
        filename = f"exports/admin_orders_{year}-W{week_num}.xlsx"

        wb = Workbook()
        ws = wb.active
        ws.title = f"Неделя {week_num}"

        # Заголовок
        ws.merge_cells("A1:F1")
        ws["A1"].value = f"Календарь заявок по питанию — {year}-W{week_num}"
        ws["A1"].font = Font(size=14, bold=True)
        ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
        ws["A1"].fill = PatternFill(start_color="BDD7EE", end_color="BDD7EE", fill_type="solid")

        # Шапка
        headers = ["Компания", "День", "Ночь", "Запайка", "Дата заявки", "Итого порций"]
        ws.append(headers)

        bold_font = Font(bold=True)
        header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
        thin_border = Border(
            left=Side(style="thin"), right=Side(style="thin"),
            top=Side(style="thin"), bottom=Side(style="thin")
        )

        for cell in ws[2]:
            cell.font = bold_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.fill = header_fill
            cell.border = thin_border

        # Суммируем данные по company + date
        grouped = defaultdict(lambda: {"День": 0, "Ночь": 0, "Запайка": 0, "created_at": None})

        for company_name, _, time, portion, created_at in week_rows:
            date_str = created_at[:10]
            key = (company_name, date_str)
            time_key = time.capitalize()
            if time_key in grouped[key]:
                grouped[key][time_key] += portion
            grouped[key]["created_at"] = created_at

        for (company_name, date_str), values in grouped.items():
            day_p = values["День"]
            night_p = values["Ночь"]
            zap_p = values["Запайка"]
            total = day_p + night_p + zap_p
            created_at = values["created_at"]

            row = [company_name, day_p, night_p, zap_p, created_at, total]
            ws.append(row)

        # Автоширина колонок
        for col in ws.columns:
            max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
            ws.column_dimensions[get_column_letter(col[0].column)].width = max_length + 2

        wb.save(filename)
        saved_files.append(filename)

    return saved_files[0] if saved_files else None