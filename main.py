import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from sqlalchemy import select, func
from config import TOKEN
from database.models import async_main, async_session
import os
from datetime import datetime
from aiogram.types import FSInputFile
from handlers import (
    start,
)
import time


async def main():
    
    # Создание БД
    await async_main()

    # Инициализация бота
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
    dp = Dispatcher()
    
    # Инициализация всех обработчиков
    dp.include_routers(
        start.router,
    )

    task_polling = dp.start_polling(bot)

    await asyncio.gather(task_polling)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен вручную")