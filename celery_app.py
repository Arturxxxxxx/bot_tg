from celery import Celery

celery = Celery(
    "tg_bot",
    broker="redis://localhost:6379/0",  # или свой
    backend="redis://localhost:6379/0"  # если нужен результат
)

# ❗ Добавь этот импорт явно
from utils import upload_excel
