import os
from datetime import datetime, timedelta
from config import FACULTIES, TZ, BASE_DIR
import openpyxl
import xlrd
import re

BASE_DIR = os.path.join(os.path.dirname(__file__), "sheets")

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
    
    # Паттерны для поиска даты
    patterns = [
        r'(\d{1,2})\s+(\w+)\s+(\w+)',  # "20 октября понедельник"
        r'(\d{1,2})\s+(\w+)',           # "20 октября"
        r'"(\d{1,2})\s+(\w+)\s+(\w+)"', # в кавычках
    ]
    
    for pattern in patterns:
        match = re.search(pattern, date_str)
        if match:
            groups = match.groups()
            if len(groups) >= 2:
                try:
                    day = int(groups[0])
                    month_str = groups[1].strip()
                    
                    # Определяем месяц
                    month = None
                    for rus_month, num in RUS_MONTHS_REVERSE.items():
                        if rus_month in month_str:
                            month = num
                            break
                    
                    if month:
                        # Берем текущий год или следующий, если месяц уже прошел
                        now = datetime.now(TZ)
                        year = now.year
                        if month < now.month or (month == now.month and day < now.day):
                            year = now.year + 1
                        
                        return datetime(year, month, day)
                except (ValueError, IndexError):
                    continue
    return None

def get_schedule_file_path(faculty: str, course: int, is_even: bool) -> str:
    """Получает путь к файлу расписания"""
    week_folder = "Четная неделя" if is_even else "Нечетная неделя"
    base_path = os.path.join(BASE_DIR, week_folder, faculty)
    
    if not os.path.exists(base_path):
        return None
    
    for file in os.listdir(base_path):
        if file.endswith(('.xls', '.xlsx')):
            if f"{course} курс" in file:
                return os.path.join(base_path, file)
    
    return None

def load_schedule(file_path: str):
    """Загружает данные из файла расписания"""
    if not file_path or not os.path.exists(file_path):
        return None
        
    ext = os.path.splitext(file_path)[1].lower()
    data = []

    try:
        if ext == ".xlsx":
            wb = openpyxl.load_workbook(file_path)
            sheet = wb.active
            for row in sheet.iter_rows(values_only=True):
                data.append([cell if cell is not None else "" for cell in row])
        elif ext == ".xls":
            wb = xlrd.open_workbook(file_path)
            sheet = wb.sheet_by_index(0)
            for r in range(sheet.nrows):
                data.append([sheet.cell_value(r, c) if sheet.cell_value(r, c) else "" for c in range(sheet.ncols)])
    except Exception as e:
        print(f"Ошибка загрузки файла {file_path}: {e}")
        return None
        
    return data

def get_available_groups(faculty: str, course: int) -> list:
    """Получает список доступных групп для факультета и курса"""
    for is_even in [False, True]:
        file_path = get_schedule_file_path(faculty, course, is_even)
        if not file_path:
            continue
            
        schedule_data = load_schedule(file_path)
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
                    return groups if groups else []
    
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
    
    # Преобразуем в наивный datetime для поиска
    if target_date.tzinfo is not None:
        search_date = target_date.replace(tzinfo=None)
    else:
        search_date = target_date
    
    lessons = []
    current_time = None
    
    # Проходим по всем строкам таблицы
    i = 0
    while i < len(schedule_data):
        row = schedule_data[i]
        
        if not row or not row[0]:
            i += 1
            continue
            
        # Парсим дату из ячейки
        date_cell = str(row[0])
        parsed_date = parse_russian_date(date_cell)
        
        if parsed_date and parsed_date.date() == search_date.date():
            print(f"✅ Найдена дата {search_date.strftime('%d.%m.%Y')} в строке {i}")
            
            # Нашли нужную дату, собираем пары до следующей даты
            j = i
            while j < len(schedule_data):
                current_row = schedule_data[j]
                
                # Проверяем время
                time = current_row[1] if len(current_row) > 1 else ""
                subject_cell = current_row[group_column] if len(current_row) > group_column else ""
                
                # Обновляем время если есть
                if time and str(time).strip():
                    current_time = str(time).strip()
                
                # Добавляем пару если есть данные
                if current_time and subject_cell and str(subject_cell).strip():
                    subject_text = str(subject_cell)
                    subject_lines = []
                    
                    for line in subject_text.split('\n'):
                        cleaned_line = line.strip().lstrip('-').strip()
                        if cleaned_line:
                            subject_lines.append(cleaned_line)
                    
                    if subject_lines:
                        # Проверяем, нет ли уже пары в это время
                        time_exists = False
                        for idx, (existing_time, existing_lines) in enumerate(lessons):
                            if existing_time == current_time:
                                # Объединяем с существующей парой
                                lessons[idx] = (current_time, existing_lines + subject_lines)
                                time_exists = True
                                break
                        
                        if not time_exists:
                            lessons.append((current_time, subject_lines))
                
                j += 1
                
                # Прерываем если нашли следующую дату
                if j < len(schedule_data) and schedule_data[j] and schedule_data[j][0]:
                    next_date_cell = str(schedule_data[j][0])
                    next_parsed_date = parse_russian_date(next_date_cell)
                    if next_parsed_date and next_parsed_date != parsed_date:
                        break
            
            return lessons
        
        i += 1
    
    print(f"❌ Дата {search_date.strftime('%d.%m.%Y')} не найдена в расписании")
    return None

def get_day_schedule(faculty: str, course: int, group: str, command: str):
    """Основная функция для получения расписания"""
    now = datetime.now(TZ)
    target_date = now

    # Определяем целевую дату
    if command == "сегодня":
        target_date = now
    elif command == "завтра":
        target_date = now + timedelta(days=1)
    else:
        # ===== ИЗМЕНЕННАЯ ЛОГИКА =====
        days_map = {"пн": 0, "вт": 1, "ср": 2, "чт": 3, "пт": 4, "сб": 5}
        today_weekday = now.weekday()  # Сегодняшний день недели (0=Пн, 6=Вс)
        target_weekday = days_map.get(command)

        if target_weekday is not None:
            # Рассчитываем разницу в днях
            shift = target_weekday - today_weekday
            
            # Если день уже прошел на этой неделе (отрицательный сдвиг),
            # то ищем его на следующей неделе.
            if shift < 0:
                shift += 7
            
            target_date = now + timedelta(days=shift)
        # ===============================
    
    print(f"🎯 Ищем расписание на: {target_date.strftime('%d.%m.%Y')}")
    
    # Пробуем оба файла (четная и нечетная неделя)
    for is_even in [False, True]:
        file_path = get_schedule_file_path(faculty, course, is_even)
        if not file_path:
            continue
            
        print(f"🔍 Проверяем файл: {'Четная' if is_even else 'Нечетная'} неделя")
        
        schedule_data = load_schedule(file_path)
        if not schedule_data:
            continue
        
        group_column = find_group_column(schedule_data, group)
        if group_column == -1:
            continue
        
        lessons = find_schedule_for_date(schedule_data, group_column, target_date)
        
        if lessons:
            print(f"✅ Найдено расписание в {'четной' if is_even else 'нечетной'} неделе")
            return format_schedule(lessons, is_even, target_date, group)
        else:
            print(f"❌ В {'четной' if is_even else 'нечетной'} неделе расписание не найдено")
    
    return "❌ Расписание на выбранную дату не найдено"

def format_schedule(lessons, is_even, date, group):
    """Форматирует расписание в красивый текст"""
    if date.tzinfo is not None:
        format_date = date.replace(tzinfo=None)
    else:
        format_date = date
        
    week_str = "Четная" if is_even else "Нечетная"
    day_short = RUS_DAYS_SHORT[format_date.weekday()]
    month_rus = RUS_MONTHS[format_date.month]
    month_rus = month_rus[0].upper() + month_rus[1:]
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
        # Сортируем пары по времени
        def time_key(lesson):
            time_str = lesson[0]
            # Пытаемся преобразовать время в минуты для сортировки
            try:
                if '-' in time_str:
                    start_time = time_str.split('-')[0].strip()
                    hours, minutes = map(int, start_time.split(':'))
                    return hours * 60 + minutes
                return 0
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

