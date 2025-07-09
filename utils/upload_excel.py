from celery_app import celery
from utils.export_excel import generate_user_excel, generate_admin_excel
import requests
from slugify import slugify
import os
from dotenv import load_dotenv
from datetime import date, timedelta, datetime

load_dotenv()

TOKEN = os.getenv("YANDEX_TOK")
print(TOKEN)
HEADERS = {"Authorization": f"OAuth {TOKEN}"}

def create_folder_if_not_exists(folder_path: str):
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    params = {"path": folder_path}
    response = requests.put(url, headers=HEADERS, params=params)
    if response.status_code not in (201, 409):
        response.raise_for_status()

def upload_file(local_path: str, remote_path: str):
    url = "https://cloud-api.yandex.net/v1/disk/resources/upload"
    params = {"path": remote_path, "overwrite": "true"}

    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    upload_url = response.json()["href"]

    with open(local_path, "rb") as f:
        upload_response = requests.put(upload_url, files={"file": f})
        upload_response.raise_for_status()

def publish_file(remote_path: str) -> str:
    url = "https://cloud-api.yandex.net/v1/disk/resources/publish"
    params = {"path": remote_path}

    response = requests.put(url, headers=HEADERS, params=params)
    if response.status_code not in (200, 201, 409):
        response.raise_for_status()

    info_url = "https://cloud-api.yandex.net/v1/disk/resources"
    info_response = requests.get(info_url, headers=HEADERS, params=params)
    info_response.raise_for_status()
    data = info_response.json()

    public_url = data.get("public_url")
    if not public_url:
        raise ValueError(f"публичная ссылка не найдена в ответе: {data}")
    return public_url


def _week_bounds(year: int, week: int) -> tuple[date, date]:
    monday = datetime.fromisocalendar(year, week, 1).date()
    return monday, monday + timedelta(days=6)

@celery.task
def generate_upload_and_get_links(
        *,
        user_id: int | None = None,
        company_name: str | None = None,
        year: int | None = None,
        week_num: int | None = None,
):
    """Генерирует и выгружает отчёты.  
       Если year/week_num не переданы → используется текущая неделя."""
    if year is None or week_num is None:
        today = date.today()
        year, week_num, _ = today.isocalendar()

    monday, sunday = _week_bounds(year, week_num)
    print(f"[CELERY] building reports for {year}-W{week_num:02d} ({monday}…{sunday})")

    user_link  = None
    admin_link = None

    create_folder_if_not_exists("users")
    create_folder_if_not_exists("admin")

    try:
        # ─────────────────────  USER  ─────────────────────
        if user_id and company_name:
            user_file = generate_user_excel(user_id, company_name, monday)
            safe = slugify(company_name or str(user_id))
            user_remote = f"users/{safe}_{year}-W{week_num:02d}.xlsx"
            upload_file(user_file, user_remote)
            user_link = publish_file(user_remote)
            os.remove(user_file)

        # ───────────────────── ADMIN ─────────────────────
        admin_file   = generate_admin_excel(year, week_num)
        admin_remote = f"admin/admin_orders_{year}-W{week_num:02d}.xlsx"
        upload_file(admin_file, admin_remote)
        admin_link = publish_file(admin_remote)
        os.remove(admin_file)

    except Exception as e:
        print(f"[CELERY ERROR] {e}")
        raise

    return {"user_link": user_link, "admin_link": admin_link}


# 🔹 Получение списка недель из папки admin/
def list_admin_weeks() -> list[str]:
    headers = {"Authorization": f"OAuth {TOKEN}"}
    response = requests.get(
        "https://cloud-api.yandex.net/v1/disk/resources",
        headers=headers,
        params={"path": "admin", "limit": 100}
    )
    response.raise_for_status()
    items = response.json()["_embedded"]["items"]

    weeks = []
    for item in items:
        name = item["name"]  # example: admin_orders_2025-W28.xlsx
        if name.startswith("admin_orders_") and name.endswith(".xlsx"):
            week = name.removeprefix("admin_orders_").removesuffix(".xlsx")
            weeks.append(week)

    return sorted(weeks, reverse=True)  # последние — сверху


# 🔹 Получение публичной ссылки на файл
def get_yadisk_public_url(path: str) -> str | None:
    headers = {"Authorization": f"OAuth {TOKEN}"}

    # Публикуем файл
    requests.put(
        "https://cloud-api.yandex.net/v1/disk/resources/publish",
        params={"path": path},
        headers=headers,
    )

    # Получаем ссылку
    response = requests.get(
        "https://cloud-api.yandex.net/v1/disk/resources",
        params={"path": path},
        headers=headers,
    )

    if response.status_code == 200:
        return response.json().get("public_url")
    return None