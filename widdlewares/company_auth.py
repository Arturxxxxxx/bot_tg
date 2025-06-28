from aiogram import BaseMiddleware
from aiogram.types import Message
from data.database import conn

ADMIN_IDS = [5469335222, 5459748606]  # Список ID админов

class CompanyAuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data):
        user_id = event.from_user.id
        
        # Если админ — пропускаем проверку
        if user_id in ADMIN_IDS:
            return await handler(event, data)
        
        # Разрешаем команды /start и /auth без проверки
        if event.text and (event.text.startswith("/start") or event.text.startswith("/auth")):
            return await handler(event, data)

        cursor = conn.cursor()
        cursor.execute("SELECT company_id FROM user_company WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if not row:
            await event.answer("❌ Вы не авторизованы. Введите код компании через /auth <код>.")
            return

        return await handler(event, data)
