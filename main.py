import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN, create_tables
from handlers import router
from aiohttp import web

async def handle(request):
    return web.Response(text="✅ Bot is alive!", content_type="text/plain")

async def main():
    # Создаем таблицы в базе данных
    await create_tables()
    
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)

    # aiohttp сервер
    app = web.Application()
    app.router.add_get("/", handle)

    # Запуск Telegram бота и веб-сервера параллельно
    async def run_bot():
        await dp.start_polling(bot)

    async def run_web():
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 10000)
        await site.start()
        print("🌐 Web server запущен на порту 10000")

    await asyncio.gather(run_bot(), run_web())

if __name__ == "__main__":
    asyncio.run(main())
