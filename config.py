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

# Базовая директория с расписаниями
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ID группы для уведомлений (можно тоже хранить в .env)
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

# ===== Функции работы с базой данных =====
async def create_tables():
    """Создает таблицы в базе данных если они не существуют"""
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
        print("✅ Таблицы в базе данных созданы/проверены")
    except Exception as e:
        print(f"❌ Ошибка создания таблиц: {e}")
    finally:
        await conn.close()

async def update_user_data(user_id, user_info):
    """Обновляет или создает данные пользователя"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute('''
            INSERT INTO users (user_id, faculty, course, group_name, username, full_name)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (user_id) 
            DO UPDATE SET 
                faculty = $2,
                course = $3,
                group_name = $4,
                username = $5,
                full_name = $6,
                registered_at = CURRENT_TIMESTAMP
        ''', user_id, user_info['faculty'], user_info['course'], 
            user_info['group'], user_info['username'], user_info['full_name'])
    except Exception as e:
        print(f"❌ Ошибка обновления данных пользователя: {e}")
    finally:
        await conn.close()

async def remove_user_data(user_id):
    """Удаляет данные пользователя"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        result = await conn.execute('DELETE FROM users WHERE user_id = $1', user_id)
        return "DELETE 1" in result
    except Exception as e:
        print(f"❌ Ошибка удаления пользователя: {e}")
        return False
    finally:
        await conn.close()

async def get_user_data(user_id):
    """Получает данные пользователя"""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow(
            'SELECT faculty, course, group_name, username, full_name FROM users WHERE user_id = $1', 
            user_id
        )
        if row:
            return {
                'faculty': row['faculty'],
                'course': row['course'],
                'group': row['group_name'],
                'username': row['username'],
                'full_name': row['full_name']
            }
        return None
    except Exception as e:
        print(f"❌ Ошибка получения данных пользователя: {e}")
        return None
    finally:
        await conn.close()
