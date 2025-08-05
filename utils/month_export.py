# utils/monthly_report.py

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from datetime import datetime
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
import os

def create_monthly_summary_sheet(workbook, month_name, day_night_total, sealing_total):
    sheet = workbook.create_sheet(title=f"Итоги {month_name}")
    sheet["A1"] = f"Ежемесячный табель: {month_name}"
    sheet["A1"].font = Font(size=14, bold=True)
    sheet.merge_cells("A1:C1")
    sheet["A1"].alignment = Alignment(horizontal="center")
    sheet["A3"] = "Итого: День + Ночь"
    sheet["B3"] = day_night_total
    sheet["A4"] = "Итого: Запайка"
    sheet["B4"] = sealing_total
    sheet.column_dimensions["A"].width = 25
    sheet.column_dimensions["B"].width = 15

def generate_monthly_report() -> str:
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    current_month = datetime.now().strftime("%Y-%m")
    
    cursor.execute("""
        SELECT company_name, time, portion
        FROM portions
        WHERE strftime('%Y-%m', day) = ?
    """, (current_month,))

    rows = cursor.fetchall()

    data = {}

    for company, time_of_day, portion in rows:
        if company not in data:
            data[company] = {"День": 0, "Ночь": 0, "Выпечка": 0}

        if time_of_day == "День":
            data[company]["День"] += portion
        elif time_of_day == "Ночь":
            data[company]["Ночь"] += portion
        elif time_of_day == "Выпечка":
            data[company]["Выпечка"] += portion

    # Подготовим список для DataFrame
    table = []
    for company, values in data.items():
        day = values["День"]
        night = values["Ночь"]
        bake = values["Выпечка"]
        total = day + night
        table.append([company, day, night, bake, total])

    df = pd.DataFrame(table, columns=["Компания", "День", "Ночь", "Выпечка", "Итого день + ночь"])

    file_name = f"monthly_report_{current_month}.xlsx"
    export_path = Path("exports") / file_name
    export_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_excel(export_path, index=False)
    conn.close()
    return str(export_path)
