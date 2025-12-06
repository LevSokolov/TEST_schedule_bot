import io
import re
import time
from datetime import datetime, timedelta

import aiohttp
import openpyxl
import xlrd

from config import SCHEDULE_URLS, TZ

# ===== НОВЫЕ ПЕРЕМЕННЫЕ ДЛЯ КЭШИРОВАНИЯ =====
# Словарь для хранения загруженных данных: { 'url': (время_загрузки, данные) }
SCHEDULE_CACHE = {} 
# Время жизни кэша в секундах (3600 секунд = 1 час)
CACHE_DURATION_SECONDS = 3600

# --- Остальные константы без изменений ---
RUS_DAYS_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
RUS_MONTHS = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня", 
    7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}
RUS_MONTHS_REVERSE = {v: k for k, v in RUS_MONTHS.items()}


def escape_markdown(text: str) -> str:
    if not text:
        return ""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))


def parse_russian_date(date_str: str):
    if not date_str:
        return None
    date_str = str(date_str).lower().strip()
    patterns = [
        r'(\d{1,2})\s+(\w+)\s+(\w+)', r'(\d{1,2})\s+(\w+)', r'"(\d{1,2})\s+(\w+)\s+(\w+)"'
    ]
    for pattern in patterns:
        match = re.search(pattern, date_str)
        if match:
            groups = match.groups()
            if len(groups) >= 2:
                try:
                    day = int(groups[0])
                    month_str = groups[1].strip()
                    month = next((num for rus_month, num in RUS_MONTHS_REVERSE.items() if rus_month in month_str), None)
                    if month:
                        now = datetime.now(TZ)
                        year = now.year
                        if month < now.month or (month == now.month and day < now.day):
                            year += 1
                        return datetime(year, month, day)
                except (ValueError, IndexError):
                    continue
    return None


async def _load_and_parse_xls(url: str):
    """Внутренняя функция: только скачивает и парсит файл."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    print(f"❌ Ошибка загрузки {url}: статус {response.status}")
                    return None
                
                content = await response.read()
                data = []
                
                if ".xlsx" in url:
                    wb = openpyxl.load_workbook(io.BytesIO(content))
                    sheet = wb.active
                    for row in sheet.iter_rows(values_only=True):
                        data.append([cell if cell is not None else "" for cell in row])
                else: # .xls
                    wb = xlrd.open_workbook(file_contents=content)
                    sheet = wb.sheet_by_index(0)
                    for r in range(sheet.nrows):
                        data.append([sheet.cell_value(r, c) or "" for c in range(sheet.ncols)])
                
                return data
    except Exception as e:
        print(f"❌ Исключение при загрузке и парсинге {url}: {e}")
        return None


async def get_schedule_data_from_url(url: str):
    """
    Основная функция для получения данных расписания.
    Использует кэш для предотвращения повторных загрузок.
    """
    current_time = time.time()
    
    # 1. Проверяем, есть ли URL в кэше и не устарели ли данные
    if url in SCHEDULE_CACHE:
        cached_time, cached_data = SCHEDULE_CACHE[url]
        if current_time - cached_time < CACHE_DURATION_SECONDS:
            print(f"✅ [Cache] Используем данные для {url}")
            return cached_data
        else:
            print(f"🔄 [Cache] Данные для {url} устарели.")
    
    # 2. Если в кэше нет или данные устарели - загружаем
    print(f"📥 [Download] Загружаем свежие данные для {url}")
    new_data = await _load_and_parse_xls(url)
    
    # 3. Если загрузка успешна, обновляем кэш
    if new_data:
        SCHEDULE_CACHE[url] = (current_time, new_data)
        print(f"💾 [Cache] Сохранили свежие данные для {url}")
    
    return new_data


def get_schedule_urls(faculty: str, course: int, is_even: bool) -> list:
    """Получает список URL-адресов для расписания из config.py"""
    week_folder = "Четная неделя" if is_even else "Нечетная неделя"
    try:
        urls = SCHEDULE_URLS[week_folder][faculty][course]
        return [urls] if isinstance(urls, str) else urls
    except KeyError:
        return []


async def get_available_groups(faculty: str, course: int) -> list:
    """Получает список доступных групп, используя кэшированные данные."""
    for is_even in [False, True]:
        urls = get_schedule_urls(faculty, course, is_even)
        for url in urls:
            schedule_data = await get_schedule_data_from_url(url)
            if not schedule_data:
                continue
            
            for row in schedule_data:
                if len(row) > 2 and "день" in str(row[0]).lower() and "часы" in str(row[1]).lower():
                    groups = [str(cell).strip() for cell in row[2:] if str(cell).strip() and "день" not in str(cell).lower() and "часы" not in str(cell).lower()]
                    if groups:
                        return groups
    return []


def find_group_column(schedule_data: list, group_name: str) -> int:
    if not schedule_data:
        return -1
    for row in schedule_data:
        if len(row) > 2 and "день" in str(row[0]).lower() and "часы" in str(row[1]).lower():
            for col_idx, cell in enumerate(row):
                if str(cell).strip() == group_name:
                    return col_idx
            break
    return -1


def find_schedule_for_date(schedule_data: list, group_column: int, target_date: datetime):
    if not schedule_data or group_column < 0:
        return None
    
    search_date = target_date.replace(tzinfo=None)
    lessons = []
    
    i = 0
    while i < len(schedule_data):
        row = schedule_data[i]
        if not row or not row[0]:
            i += 1
            continue
        
        parsed_date = parse_russian_date(str(row[0]))
        if parsed_date and parsed_date.date() == search_date.date():
            current_time = None
            j = i
            while j < len(schedule_data):
                current_row = schedule_data[j]
                
                # Проверяем, не наступила ли уже следующая дата
                if j > i and current_row and current_row[0]:
                   next_parsed_date = parse_russian_date(str(current_row[0]))
                   if next_parsed_date and next_parsed_date.date() != search_date.date():
                       break # Выходим, если нашли следующую дату
                
                time_cell = current_row[1] if len(current_row) > 1 else ""
                if time_cell and str(time_cell).strip():
                    current_time = str(time_cell).strip()
                
                subject_cell = current_row[group_column] if len(current_row) > group_column else ""
                if current_time and subject_cell and str(subject_cell).strip():
                    subject_lines = [line.strip().lstrip('-').strip() for line in str(subject_cell).split('\n') if line.strip()]
                    if subject_lines:
                        lessons.append((current_time, subject_lines))
                
                j += 1
            return lessons
        i += 1
        
    return None # Явно возвращаем None, если дата не найдена в файле


async def get_day_schedule(faculty: str, course: int, group: str, command: str):
    now = datetime.now(TZ)
    target_date = now

    if command == "завтра":
        target_date = now + timedelta(days=1)
    elif command != "сегодня":
        days_map = {"пн": 0, "вт": 1, "ср": 2, "чт": 3, "пт": 4, "сб": 5}
        shift = days_map.get(command, now.weekday()) - now.weekday()
        if shift < 0:
            shift += 7
        target_date = now + timedelta(days=shift)
    
    for is_even in [False, True]:
        urls = get_schedule_urls(faculty, course, is_even)
        for url in urls:
            schedule_data = await get_schedule_data_from_url(url)
            if not schedule_data:
                continue
            
            group_column = find_group_column(schedule_data, group)
            if group_column == -1:
                continue
            
            lessons = find_schedule_for_date(schedule_data, group_column, target_date)
            if lessons is not None:
                return format_schedule(lessons, is_even, target_date, group)

    return f"❌ Расписание на `{escape_markdown(target_date.strftime('%d.%m.%Y'))}` не найдено"


def format_schedule(lessons, is_even, date, group):
    date_str = f"{RUS_DAYS_SHORT[date.weekday()]} {date.day} {RUS_MONTHS[date.month]}"
    result = [
        f"*📅 {('Четная' if is_even else 'Нечетная')} неделя*",
        f"*👥 {escape_markdown(group)}*",
        f"\n🟢__*{escape_markdown(date_str)}*__\n"
    ]
    
    if not lessons:
        result.append("🎉 *Пар нет, можно отдыхать!*")
    else:
        # Убираем дубликаты пар, которые могли появиться из-за объединения ячеек
        unique_lessons = []
        [unique_lessons.append(x) for x in lessons if x not in unique_lessons]
        
        # Сортировка по времени
        def time_key(lesson):
            try:
                h, m = map(int, lesson[0].split('-')[0].strip().split(':'))
                return h * 60 + m
            except:
                return 0
        
        for time, subject_lines in sorted(unique_lessons, key=time_key):
            result.append(f"*⏰ {escape_markdown(time)}*")
            for line in subject_lines:
                result.append(f"• _{escape_markdown(line)}_")
            result.append("")

    return "\n".join(result)
