from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
import logging

from handlers import start, load_data, feedback
from decouple import config
from widdlewares.company_auth import CompanyAuthMiddleware
from handlers.start import set_commands


async def on_startup(bot: Bot):
    await set_commands(bot)

async def main():
    logging.basicConfig(level=logging.INFO)


    bot = Bot(token=config('TOKEN'))
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(CompanyAuthMiddleware())  

    dp.include_router(start.router)
    dp.include_router(load_data.router)
    dp.include_router(feedback.router)

    await on_startup(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())