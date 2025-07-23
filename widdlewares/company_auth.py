from aiogram import BaseMiddleware
from aiogram.types import Message
from data.database import conn

ADMIN_IDS = [5469335222, 5459748606]

# class CompanyAuthMiddleware(BaseMiddleware):
#     async def __call__(self, handler, event: Message, data):
#         user_id = event.from_user.id

#         # Разрешаем админам всё
#         if user_id in ADMIN_IDS:
#             return await handler(event, data)

#         # Разрешаем команды, связанные с авторизацией
#         if event.text and (event.text.startswith("/start") or event.text.startswith("/auth")):
#             return await handler(event, data)

#         # Проверяем авторизацию
#         cursor = conn.cursor()
#         cursor.execute("SELECT company_id FROM user_company WHERE user_id = ?", (user_id,))
#         row = cursor.fetchone()

#         if not row:
#             await event.answer("❌ Вы не авторизованы. Введите код компании через /auth <код>.")
#             return

#         return await handler(event, data)
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.context import FSMContext

class CompanyAuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data):
        user_id = event.from_user.id

        # Разрешаем админам всё
        if user_id in ADMIN_IDS:
            return await handler(event, data)

        # Разрешаем команды /start и /auth
        if event.text and (event.text.startswith("/start") or event.text.startswith("/auth")):
            return await handler(event, data)

        # Проверка: если пользователь в FSM состоянии, например ждет код
        state = FSMContext(
            storage = data["dispatcher"].storage,
            key=StorageKey(bot_id=data["bot"].id, chat_id=event.chat.id, user_id=user_id)
        )
        current_state = await state.get_state()
        if current_state is not None:
            return await handler(event, data)

        # Проверка авторизации
        cursor = conn.cursor()
        cursor.execute("SELECT company_id FROM user_company WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if not row:
            await event.answer("❌ Вы не авторизованы. Введите код компании через /auth <код>.")
            return

        return await handler(event, data)
