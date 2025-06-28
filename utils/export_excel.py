from openpyxl import Workbook
from slugify import slugify
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime
from itertools import groupby
import os
from data.database import conn

from openpyxl import Workbook, load_workbook
from slugify import slugify
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime
import os
from data.database import conn



def generate_user_excel(user_id: int, username: str) -> str:
    safe_name = slugify(username or str(user_id))
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

    # Настройки Excel
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

        # Очистим старые данные
        for row in ws.iter_rows(min_row=5, max_row=ws.max_row):
            for cell in row:
                cell.value = None
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = "Заявки пользователя"

        # Заголовок
        ws.merge_cells("A1:D1")
        ws["A1"].value = "Заявки на питание"
        ws["A1"].font = Font(size=14, bold=True)
        ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
        ws["A1"].fill = PatternFill(start_color="BDD7EE", end_color="BDD7EE", fill_type="solid")
        ws["A1"].border = thin_border

        # Пользователь
        display_name = username or f"ID {user_id}"
        ws.merge_cells("A2:D2")
        ws["A2"].value = f"Пользователь: {display_name}"
        ws["A2"].font = Font(size=12, bold=True)
        ws["A2"].alignment = Alignment(horizontal="left", vertical="center")
        ws["A2"].border = thin_border

        # Шапка
        headers = ["День", "Время", "Порции", "Дата заявки"]
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=row_start, column=col)
            cell.value = header
            cell.font = bold_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.fill = header_fill
            cell.border = thin_border

        # Ширина колонок
        col_widths = {1: 15, 2: 15, 3: 15, 4: 20}
        for col, width in col_widths.items():
            ws.column_dimensions[get_column_letter(col)].width = width

    # --- Заполнение данных с вычислением (+N / -N) ---
    portion_map = {}  # для day|time

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
    filename = "exports/admin_orders.xlsx"
    os.makedirs("exports", exist_ok=True)

    cursor = conn.cursor()
    cursor.execute("""
        SELECT username, day, time, portion, created_at
        FROM portions
        ORDER BY created_at ASC
    """)
    rows = cursor.fetchall()

    def get_date(row):
        return row[4][:10]  # created_at[:10]

    rows = sorted(rows, key=get_date)

    wb = Workbook()
    ws = wb.active
    ws.title = "Календарь заявок по питанию"

    # Заголовок всей таблицы
    ws.merge_cells("A1:D1")
    title_cell = ws["A1"]
    title_cell.value = "Календарь заявок по питанию"
    title_cell.font = Font(bold=True, size=16)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    title_cell.fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")

    current_row = 3
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin")
    )

    # 💡 Храним последние порции по ключу user|day|time
    portion_map = {}

    for date_key, group in groupby(rows, key=get_date):
        # 📅 Дата
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=4)
        date_cell = ws.cell(row=current_row, column=1)
        try:
            dt = datetime.strptime(date_key, "%Y-%m-%d")
            formatted_date = dt.strftime("%d.%m.%Y")
        except Exception:
            formatted_date = date_key
        date_cell.value = f"Дата: {formatted_date}"
        date_cell.font = Font(bold=True, size=12, color="FFFFFF")
        date_cell.alignment = Alignment(horizontal="center", vertical="center")
        date_cell.fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
        date_cell.border = thin_border
        current_row += 1

        # Заголовки столбцов
        headers = ["Пользователь", "Время", "Порции", "Время заявки"]
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=current_row, column=col)
            cell.value = header
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.fill = PatternFill(start_color="BDD7EE", end_color="BDD7EE", fill_type="solid")
            cell.border = thin_border
        current_row += 1

        for record in group:
            username_val, day, time_val, portion, created_at = record
            key = f"{username_val}|{day}|{time_val}"

            # Вычисление разницы
            portion_display = str(portion)
            if key in portion_map:
                prev = portion_map[key]
                diff = portion - prev
                if diff > 0:
                    portion_display = f"{portion} (+{diff})"
                elif diff < 0:
                    portion_display = f"{portion} ({diff})"
            portion_map[key] = portion

            time_request = created_at[11:] if len(created_at) >= 11 else created_at
            row_values = [username_val, time_val, portion_display, time_request]

            for col, val in enumerate(row_values, start=1):
                cell = ws.cell(row=current_row, column=col)
                cell.value = val
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = thin_border
            current_row += 1

        current_row += 1  # Пустая строка между группами

    # Ширина колонок
    col_widths = {1: 20, 2: 15, 3: 15, 4: 18}
    for col, width in col_widths.items():
        ws.column_dimensions[get_column_letter(col)].width = width

    wb.save(filename)
    return filename