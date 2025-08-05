from celery import Celery
from celery.schedules import crontab



celery = Celery(
    "tg_bot",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

# Включаем автопоиск задач в папке utils
# celery.autodiscover_tasks(["utils"])

# Устанавливаем расписание задач
celery.conf.beat_schedule = {
    "check-and-export-last-day-of-month": {
        "task": "utils.upload_excel.export_monthly_admin_excel_task",  # ← Укажи реальный путь!
        "schedule": crontab(hour=23, minute=59),  # каждый день в 23:59
    },
}
from utils import upload_excel