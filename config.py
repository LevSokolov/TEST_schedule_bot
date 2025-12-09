import os
import asyncpg
from datetime import timezone, timedelta
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Безопасно берём токен из окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Укажи его в .env")

# URL базы данных
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL не найден! Укажи его в .env")

# Временная зона
TZ = timezone(timedelta(hours=5))  # Екатеринбург UTC+5

# ID группы для уведомлений
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID", "-4940561857"))

# Структура факультетов
FACULTIES = {
    "Механический факультет": "МФ",
    "Строительный факультет": "СФ",
    "Факультет управления процессами перевозок": "ФУПП",
    "Факультет экономики и управления": "ФЭУ",
    "Электромеханический факультет": "ЭМФ",
    "Электротехнический факультет": "ЭТФ",
    "ДиА": "ДиА"
}

# Ссылки на расписания
SCHEDULE_URLS = {
    "Нечетная неделя": {
        "ДиА": { 1: "https://bb.usurt.ru/bbcswebdav/xid-21084187_1" },
        "Механический факультет": {
            1: "https://bb.usurt.ru/bbcswebdav/xid-20933625_1", 2: "https://bb.usurt.ru/bbcswebdav/xid-23861424_1",
            3: "https://bb.usurt.ru/bbcswebdav/xid-23862319_1", 4: "https://bb.usurt.ru/bbcswebdav/xid-23863115_1",
            5: "https://bb.usurt.ru/bbcswebdav/xid-23863375_1",
        },
        "Строительный факультет": {
            1: "https://bb.usurt.ru/bbcswebdav/xid-20933630_1", 2: "https://bb.usurt.ru/bbcswebdav/xid-23861425_1",
            3: "https://bb.usurt.ru/bbcswebdav/xid-23862320_1", 4: "https://bb.usurt.ru/bbcswebdav/xid-23863116_1",
            5: "https://bb.usurt.ru/bbcswebdav/xid-23863376_1",
        },
        "Факультет управления процессами перевозок": {
            1: "https://bb.usurt.ru/bbcswebdav/xid-20933635_1", 2: "https://bb.usurt.ru/bbcswebdav/xid-23861426_1",
            3: "https://bb.usurt.ru/bbcswebdav/xid-23862321_1", 4: "https://bb.usurt.ru/bbcswebdav/xid-23863377_1",
            5: "https://bb.usurt.ru/bbcswebdav/xid-23864226_1",
        },
        "Факультет экономики и управления": {
            1: "https://bb.usurt.ru/bbcswebdav/xid-20933640_1", 2: "https://bb.usurt.ru/bbcswebdav/xid-23861427_1",
            3: "https://bb.usurt.ru/bbcswebdav/xid-23862322_1", 4: "https://bb.usurt.ru/bbcswebdav/xid-23863121_1",
        },
        "Электромеханический факультет": {
            1: "https://bb.usurt.ru/bbcswebdav/xid-20933644_1", 2: "https://bb.usurt.ru/bbcswebdav/xid-23861428_1",
            3: "https://bb.usurt.ru/bbcswebdav/xid-23862323_1", 4: "https://bb.usurt.ru/bbcswebdav/xid-23863126_1",
            5: "https://bb.usurt.ru/bbcswebdav/xid-23863378_1",
        },
        "Электротехнический факультет": {
            1: "https://bb.usurt.ru/bbcswebdav/xid-20933649_1", 2: "https://bb.usurt.ru/bbcswebdav/xid-23861429_1",
            3: "https://bb.usurt.ru/bbcswebdav/xid-23862324_1", 4: "https://bb.usurt.ru/bbcswebdav/xid-23863127_1",
            5: "https://bb.usurt.ru/bbcswebdav/xid-23863379_1",
        }
    },
    "Четная неделя": {
        "ДиА": { 1: "https://bb.usurt.ru/bbcswebdav/xid-23870736_1" },
        "Механический факультет": {
            1: "https://bb.usurt.ru/bbcswebdav/xid-23870737_1", 2: "https://bb.usurt.ru/bbcswebdav/xid-23870789_1",
            3: "https://bb.usurt.ru/bbcswebdav/xid-23872118_1", 4: "https://bb.usurt.ru/bbcswebdav/xid-23879494_1",
            5: "https://bb.usurt.ru/bbcswebdav/xid-23882477_1",
        },
        "Строительный факультет": {
            1: "https://bb.usurt.ru/bbcswebdav/xid-23872117_1", 2: "https://bb.usurt.ru/bbcswebdav/xid-23870790_1",
            3: "https://bb.usurt.ru/bbcswebdav/xid-23872119_1", 4: "https://bb.usurt.ru/bbcswebdav/xid-23879495_1",
            5: "https://bb.usurt.ru/bbcswebdav/xid-23883756_1",
        },
        "Факультет управления процессами перевозок": {
            1: "https://bb.usurt.ru/bbcswebdav/xid-23870739_1", 2: "https://bb.usurt.ru/bbcswebdav/xid-23870791_1",
            3: "https://bb.usurt.ru/bbcswebdav/xid-23872120_1", 4: "https://bb.usurt.ru/bbcswebdav/xid-23879496_1",
            5: "https://bb.usurt.ru/bbcswebdav/xid-23886773_1",
        },
        "Факультет экономики и управления": {
            1: "https://bb.usurt.ru/bbcswebdav/xid-23873014_1", 2: "https://bb.usurt.ru/bbcswebdav/xid-23870793_1",
            3: "https://bb.usurt.ru/bbcswebdav/xid-23872121_1", 4: "https://bb.usurt.ru/bbcswebdav/xid-23879497_1",
        },
        "Электромеханический факультет": {
            1: "https://bb.usurt.ru/bbcswebdav/xid-23870741_1", 2: "https://bb.usurt.ru/bbcswebdav/xid-23870794_1",
            3: "https://bb.usurt.ru/bbcswebdav/xid-23872122_1", 4: "https://bb.usurt.ru/bbcswebdav/xid-23879498_1",
            5: "https://bb.usurt.ru/bbcswebdav/xid-23882478_1",
        },
        "Электротехнический факультет": {
            1: "https://bb.usurt.ru/bbcswebdav/xid-23870742_1", 2: "https://bb.usurt.ru/bbcswebdav/xid-23870795_1",
            3: "https://bb.usurt.ru/bbcswebdav/xid-23872123_1", 4: "https://bb.usurt.ru/bbcswebdav/xid-23879499_1",
            5: "https://bb.usurt.ru/bbcswebdav/xid-23883107_1",
        }
    }
}


async def create_tables():
    """Создает таблицы users и notes в базе данных, если они не существуют."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                faculty TEXT NOT NULL,
                course TEXT NOT NULL,
                group_name TEXT NOT NULL,
                username TEXT,
                full_name TEXT NOT NULL,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                note_date DATE NOT NULL,
                note_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (user_id, note_date)
            )
        ''')
        print("✅ Таблицы users и notes созданы/проверены")
    except Exception as e:
        print(f"❌ Ошибка создания таблиц: {e}")
    finally:
        await conn.close()


async def update_user_data(user_id, user_info):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute('''
            INSERT INTO users (user_id, faculty, course, group_name, username, full_name)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (user_id) DO UPDATE SET 
                faculty = $2, course = $3, group_name = $4, username = $5, full_name = $6,
                registered_at = CURRENT_TIMESTAMP
        ''', user_id, user_info['faculty'], user_info['course'], 
            user_info['group'], user_info['username'], user_info['full_name'])
    finally:
        await conn.close()


async def remove_user_data(user_id):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute('DELETE FROM users WHERE user_id = $1', user_id)
        return True
    except:
        return False
    finally:
        await conn.close()


async def get_user_data(user_id):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow('SELECT * FROM users WHERE user_id = $1', user_id)
        return dict(row) if row else None
    finally:
        await conn.close()


async def add_or_update_note(user_id: int, note_date, note_text: str):
    """Добавляет или обновляет личную заметку пользователя."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute('''
            INSERT INTO notes (user_id, note_date, note_text)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, note_date) 
            DO UPDATE SET note_text = $3, created_at = CURRENT_TIMESTAMP
        ''', user_id, note_date, note_text)
    finally:
        await conn.close()


async def get_note(user_id: int, note_date):
    """Получает личную заметку пользователя."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow(
            'SELECT note_text FROM notes WHERE user_id = $1 AND note_date = $2',
            user_id, note_date
        )
        return row['note_text'] if row else None
    finally:
        await conn.close()


async def delete_note(user_id: int, note_date):
    """Удаляет личную заметку пользователя."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute('DELETE FROM notes WHERE user_id = $1 AND note_date = $2', user_id, note_date)
        return True
    finally:
        await conn.close()
