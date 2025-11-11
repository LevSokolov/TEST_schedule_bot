import io
import re
from datetime import datetime, timedelta

import aiohttp
import openpyxl
import pandas as pd
import xlrd
from aiogram.client.session import aiohttp

from config import SCHEDULE_URLS, TZ

DAY_MAP = {
    "понедельник": 0, "вторник": 1, "среда": 2, "четверг": 3, 
    "пятница": 4, "суббота": 5, "воскресенье": 6
}

RUS_DAYS_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
RUS_MONTHS = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}
RUS_MONTHS_REVERSE = {v: k for k, v in RUS_MONTHS.items()}


def escape_markdown(text: str) -> str:
    """Экранирование специальных символов для MarkdownV2"""
    if not text:
        return ""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))


def parse_russian_date(date_str: str):
    """Парсит русскую дату из строки"""
    if not date_str:
        return None
    
    date_str = str(date_str).lower().strip()
    
    patterns = [
        r'(\d{1,2})\s+(\w+)\s+(\w+)',
        r'(\d{1,2})\s+(\w+)',
        r'"(\d{1,2})\s+(\w+)\s+(\w+)"',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, date_str)
        if match:
            groups = match.groups()
            if len(groups) >= 2:
                try:
                    day = int(groups[0])
                    month_str = groups[1].strip()
                    
                    month = None
                    for rus_month, num in RUS_MONTHS_REVERSE.items():
                        if rus_month in month_str:
                            month = num
                            break
                    
                    if month:
                        now = datetime.now(TZ)
                        year = now.year
                        if month < now.month or (month == now.month and day < now.day):
                            year = now.year + 1
                        
                        return datetime(year, month, day)
                except (ValueError, IndexError):
                    continue
    return None


async def get_schedule_urls(faculty: str, course: int, is_even: bool) -> list:
    """Получает список URL-адресов для расписания"""
    week_folder = "Четная неделя" if is_even else "Нечетная неделя"
    try:
        urls = SCHEDULE_URLS[week_folder][faculty][course]
        if isinstance(urls, str):
            return [urls]
        return urls  # Если это уже список
    except KeyError:
        return []


async def load_schedule_from_url(url: str):
    """Асинхронно загружает и читает XLS файл по URL"""
    if not url or not url.startswith("http"):
        print(f"❌ Неверный URL: {url}")
        return None

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    print(f"❌ Ошибка загрузки {url}: статус {response.status}")
                    return None
                
                content = await response.read()
                file_ext = ".xlsx" if "xlsx" in url else ".xls"
                
                # Используем io.BytesIO для чтения файла из памяти
                file_in_memory = io.BytesIO(content)
                
                data = []
                if file_ext == ".xlsx":
                    wb = openpyxl.load_workbook(file_in_memory)
                    sheet = wb.active
                    for row in sheet.iter_rows(values_only=True):
                        data.append([cell if cell is not None else "" for cell in row])
                elif file_ext == ".xls":
                    wb = xlrd.open_workbook(file_contents=content)
                    sheet = wb.sheet_by_index(0)
                    for r in range(sheet.nrows):
                        data.append([sheet.cell_value(r, c) if sheet.cell_value(r, c) else "" for c in range(sheet.ncols)])
                
                return data

    except Exception as e:
        print(f"❌ Исключение при загрузке {url}: {e}")
        return None


async def get_available_groups(faculty: str, course: int) -> list:
    """Получает список доступных групп, загружая файлы по URL"""
    for is_even in [False, True]:
        urls = await get_schedule_urls(faculty, course, is_even)
        for url in urls:
            schedule_data = await load_schedule_from_url(url)
            if not schedule_data:
                continue

            for row in schedule_data:
                if len(row) > 2:
                    first_cell = str(row[0]).lower() if row[0] else ""
                    second_cell = str(row[1]).lower() if row[1] else ""
                    
                    if "день" in first_cell and "часы" in second_cell:
                        groups = []
                        for cell in row[2:]:
                            cell_str = str(cell).strip()
                            if cell_str and cell_str not in ["День", "Часы"] and not cell_str.isspace():
                                groups.append(cell_str)
                        if groups:
                            return groups
    return []


def find_group_column(schedule_data: list, group_name: str) -> int:
    """Находит номер столбца для указанной группы"""
    if not schedule_data:
        return -1
        
    for row in schedule_data:
        if len(row) > 2:
            first_cell = str(row[0]).lower() if row[0] else ""
            second_cell = str(row[1]).lower() if row[1] else ""
            
            if "день" in first_cell and "часы" in second_cell:
                for col_idx, cell in enumerate(row[2:], start=2):
                    if str(cell).strip() == group_name:
                        return col_idx
                break
    return -1


def find_schedule_for_date(schedule_data: list, group_column: int, target_date: datetime):
    """Находит расписание для группы на указанную дату"""
    if not schedule_data or group_column < 0:
        return []

    search_date = target_date.replace(tzinfo=None)
    
    lessons = []
    current_time = None
    
    i = 0
    while i < len(schedule_data):
        row = schedule_data[i]
        
        if not row or not row[0]:
            i += 1
            continue
            
        date_cell = str(row[0])
        parsed_date = parse_russian_date(date_cell)
        
        if parsed_date and parsed_date.date() == search_date.date():
            j = i
            while j < len(schedule_data):
                current_row = schedule_data[j]
                
                time = current_row[1] if len(current_row) > 1 else ""
                subject_cell = current_row[group_column] if len(current_row) > group_column else ""
                
                if time and str(time).strip():
                    current_time = str(time).strip()
                
                if current_time and subject_cell and str(subject_cell).strip():
                    subject_text = str(subject_cell)
                    subject_lines = [
                        line.strip().lstrip('-').strip()
                        for line in subject_text.split('\n') if line.strip()
                    ]
                    
                    if subject_lines:
                        time_exists = False
                        for idx, (existing_time, existing_lines) in enumerate(lessons):
                            if existing_time == current_time:
                                lessons[idx] = (current_time, existing_lines + subject_lines)
                                time_exists = True
                                break
                        
                        if not time_exists:
                            lessons.append((current_time, subject_lines))
                
                j += 1
                
                if j < len(schedule_data) and schedule_data[j] and schedule_data[j][0]:
                    next_date_cell = str(schedule_data[j][0])
                    next_parsed_date = parse_russian_date(next_date_cell)
                    if next_parsed_date and next_parsed_date != parsed_date:
                        break
            
            return lessons
        
        i += 1
    
    return None


async def get_day_schedule(faculty: str, course: int, group: str, command: str):
    """Основная функция для получения расписания"""
    now = datetime.now(TZ)
    target_date = now

    if command == "сегодня":
        target_date = now
    elif command == "завтра":
        target_date = now + timedelta(days=1)
    else:
        days_map = {"пн": 0, "вт": 1, "ср": 2, "чт": 3, "пт": 4, "сб": 5}
        today_weekday = now.weekday()
        target_weekday = days_map.get(command)

        if target_weekday is not None:
            shift = target_weekday - today_weekday
            if shift < 0:
                shift += 7
            target_date = now + timedelta(days=shift)
    
    for is_even in [False, True]:
        urls = await get_schedule_urls(faculty, course, is_even)
        for url in urls:
            schedule_data = await load_schedule_from_url(url)
            if not schedule_data:
                continue
            
            group_column = find_group_column(schedule_data, group)
            if group_column == -1:
                continue
            
            lessons = find_schedule_for_date(schedule_data, group_column, target_date)
            
            if lessons is not None:
                return format_schedule(lessons, is_even, target_date, group)

    return "❌ Расписание на выбранную дату не найдено"


def format_schedule(lessons, is_even, date, group):
    """Форматирует расписание в красивый текст"""
    format_date = date.replace(tzinfo=None)
        
    week_str = "Четная" if is_even else "Нечетная"
    day_short = RUS_DAYS_SHORT[format_date.weekday()]
    month_rus = RUS_MONTHS[format_date.month].capitalize()
    date_str = f"{day_short} {format_date.day} {month_rus}"
    
    escaped_week = escape_markdown(week_str)
    escaped_group = escape_markdown(group)
    escaped_date = escape_markdown(date_str)
    
    result = [
        f"*📅 {escaped_week} неделя*",
        f"*👥 {escaped_group}*",
        "",
        f"🟢__*{escaped_date}*__",
        "",
    ]
    
    if not lessons:
        result.append("❌ *Пар нет*")
    else:
        def time_key(lesson):
            try:
                start_time = lesson[0].split('-')[0].strip()
                hours, minutes = map(int, start_time.split(':'))
                return hours * 60 + minutes
            except:
                return 0
        
        sorted_lessons = sorted(lessons, key=time_key)
        
        for time, subject_lines in sorted_lessons:
            escaped_time = escape_markdown(time)
            result.append(f"*⏰ {escaped_time}*")
            
            for line in subject_lines:
                escaped_line = escape_markdown(line)
                result.append(f"\\- {escaped_line}")
            result.append("")

    return "\n".join(result)
