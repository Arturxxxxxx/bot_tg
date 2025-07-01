from celery_app import celery
from utils.export_excel import generate_user_excel, generate_admin_excel
import requests
from slugify import slugify
import os
from dotenv import load_dotenv
from datetime import date

load_dotenv()

TOKEN = os.getenv("YANDEX_TOKEN")
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


@celery.task
def generate_upload_and_get_links(user_id: int = None, company_name: str = None):
    print(f"[CELERY] Генерация Excel для {company_name} (user_id={user_id}) началась")

    user_link = None
    admin_link = None

    create_folder_if_not_exists("users")
    create_folder_if_not_exists("admin")

    try:
        # --- Генерация Excel-файла пользователя ---
        if user_id and company_name:
            print(f"[CELERY] Генерация user Excel...")
            user_file = generate_user_excel(user_id=user_id, company_name=company_name)
            safe_name = slugify(company_name or str(user_id))
            user_remote_path = f"/users/{safe_name}.xlsx"
            upload_file(user_file, user_remote_path)
            user_link = publish_file(user_remote_path)
            print(f"[CELERY] User файл загружен и опубликован")

        # --- Генерация Excel-файла для недели ---
        print(f"[CELERY] Генерация admin Excel по неделе...")
        today = date.today()
        year, week, _ = today.isocalendar()
        admin_file = generate_admin_excel(year, week)
        admin_filename = os.path.basename(admin_file)
        admin_remote_path = f"/admin/{admin_filename}"
        upload_file(admin_file, admin_remote_path)
        admin_link = publish_file(admin_remote_path)
        print(f"[CELERY] Admin файл '{admin_filename}' загружен и опубликован")

    except Exception as e:
        print(f"[CELERY ERROR] {e}")
        raise e

    finally:
        if 'user_file' in locals() and user_file and os.path.exists(user_file):
            os.remove(user_file)
        if 'admin_file' in locals() and admin_file and os.path.exists(admin_file):
            os.remove(admin_file)

    return {
        "user_link": user_link,
        "admin_link": admin_link
    }