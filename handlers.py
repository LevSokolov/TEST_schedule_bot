from aiogram import Router, F, Bot, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from datetime import datetime, timedelta

# ✅ ИЗМЕНЕНИЕ: Импортируем TZ, новые состояния и функции
from config import FACULTIES, GROUP_CHAT_ID, update_user_data, remove_user_data, get_user_data, TZ
from states import Registration, TeacherSearch
from schedule_parser import get_day_schedule, get_available_groups, get_teacher_schedule

router = Router()

CHANNEL_USERNAME = "@smartschedule0"

# --- Клавиатуры (без изменений) ---

def get_subscription_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться на канал", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_subscription")]
        ]
    )

def get_faculties_keyboard():
    buttons = []
    row = []
    for faculty in FACULTIES.keys():
        row.append(KeyboardButton(text=faculty))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_courses_keyboard():
    buttons = [
        [KeyboardButton(text="1"), KeyboardButton(text="2"), KeyboardButton(text="3")],
        [KeyboardButton(text="4"), KeyboardButton(text="5")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_schedule_keyboard():
    buttons = [
        [KeyboardButton(text="Сегодня"), KeyboardButton(text="Завтра")],
        [KeyboardButton(text="Пн"), KeyboardButton(text="Вт"), KeyboardButton(text="Ср")],
        [KeyboardButton(text="Чт"), KeyboardButton(text="Пт"), KeyboardButton(text="Сб")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )

async def check_user_subscription(bot: Bot, user_id: int) -> bool:
    """Проверяет, подписан ли пользователь на канал"""
    try:
        chat_member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        return False

# --- Основные хендлеры ---

@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(callback_query: types.CallbackQuery, bot: Bot):
    user_id = callback_query.from_user.id
    if await check_user_subscription(bot, user_id):
        await callback_query.message.delete() # Удаляем сообщение с кнопками
        user_info = await get_user_data(user_id)
        if user_info:
            await callback_query.message.answer(
                "Теперь вы можете посмотреть расписание:",
                reply_markup=get_schedule_keyboard()
            )
        else:
            await callback_query.message.answer(
                "Для начала работы используйте команду /start",
                reply_markup=ReplyKeyboardRemove()
            )
    else:
        await callback_query.answer("❌ Вы еще не подписались на канал!", show_alert=True)

@router.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext, bot: Bot):
    if not await check_user_subscription(bot, message.from_user.id):
        await message.answer(
            "⚠️ Для использования бота необходимо подписаться на наш канал!",
            reply_markup=get_subscription_keyboard()
        )
        return
    
    user_id = message.from_user.id
    old_user_data = await get_user_data(user_id)
    
    if old_user_data:
        # ... (код отправки сообщения об удалении)
        await remove_user_data(user_id)
    
    await message.answer(
        "Добро пожаловать! Выберите ваш факультет:",
        reply_markup=get_faculties_keyboard()
    )
    await state.set_state(Registration.choosing_faculty)

@router.message(Registration.choosing_faculty, F.text.in_(FACULTIES.keys()))
async def faculty_chosen(message: Message, state: FSMContext, bot: Bot):
    if not await check_user_subscription(bot, message.from_user.id):
        # ... (код проверки подписки)
        return
    
    await state.update_data(faculty=message.text)
    await message.answer(
        "Отлично! Теперь выберите ваш курс:",
        reply_markup=get_courses_keyboard()
    )
    await state.set_state(Registration.choosing_course)

@router.message(Registration.choosing_faculty)
async def wrong_faculty(message: Message, bot: Bot):
    # ... (код для неверного выбора факультета)
    await message.answer(
        "Пожалуйста, выберите факультет из предложенных вариантов:",
        reply_markup=get_faculties_keyboard()
    )

@router.message(Registration.choosing_course, F.text.in_(["1", "2", "3", "4", "5"]))
async def course_chosen(message: Message, state: FSMContext, bot: Bot):
    if not await check_user_subscription(bot, message.from_user.id):
        # ... (код проверки подписки)
        return
    
    course = message.text
    data = await state.get_data()
    faculty = data['faculty']
    
    groups = await get_available_groups(faculty, int(course))
    
    if not groups:
        await message.answer(
            f"Для {faculty} {course} курс не найдено расписания.\nПопробуйте выбрать другой курс или факультет:",
            reply_markup=get_courses_keyboard()
        )
        return
    
    await state.update_data(course=course, available_groups=groups)
    
    group_buttons = [KeyboardButton(text=group) for group in groups]
    # Простое форматирование клавиатуры для длинных списков
    keyboard = [group_buttons[i:i + 3] for i in range(0, len(group_buttons), 3)]

    await message.answer(
        "Отлично! Теперь выберите вашу группу:",
        reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    await state.set_state(Registration.choosing_group)

@router.message(Registration.choosing_course)
async def wrong_course(message: Message, bot: Bot):
     # ... (код для неверного выбора курса)
    await message.answer(
        "Пожалуйста, выберите курс от 1 до 5:",
        reply_markup=get_courses_keyboard()
    )

@router.message(Registration.choosing_group)
async def group_chosen(message: Message, state: FSMContext, bot: Bot):
    if not await check_user_subscription(bot, message.from_user.id):
        # ... (код проверки подписки)
        return
    
    group = message.text
    data = await state.get_data()
    
    if group not in data.get('available_groups', []):
        await message.answer("Пожалуйста, выберите группу из предложенных вариантов:")
        return
    
    user_id = message.from_user.id
    user_info = {
        'faculty': data['faculty'], 'course': data['course'], 'group': group,
        'username': f"@{message.from_user.username}" if message.from_user.username else "нет username",
        'full_name': message.from_user.full_name or "Неизвестно"
    }
    
    await update_user_data(user_id, user_info)
    
    # ... (код отправки сообщения админу о новой регистрации)
    
    await message.answer(
        f"✅ Регистрация завершена!\n"
        f"Факультет: {data['faculty']}\nКурс: {data['course']}\nГруппа: {group}\n\n"
        f"Теперь вы можете посмотреть расписание:",
        reply_markup=get_schedule_keyboard()
    )
    await state.clear()

# ✅ ИЗМЕНЕНИЕ: Модифицируем этот хендлер для отмены поиска преподавателя
@router.message(F.text.lower().in_({"сегодня", "завтра", "пн", "вт", "ср", "чт", "пт", "сб"}))
async def day_selected(message: Message, state: FSMContext, bot: Bot):
    # Если пользователь был в режиме поиска преподавателя, отменяем его
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()

    user_id = message.from_user.id
    if not await check_user_subscription(bot, user_id):
        await message.answer("⚠️ Для использования бота необходимо подписаться на наш канал!", reply_markup=get_subscription_keyboard())
        return
    
    user_info = await get_user_data(user_id)
    if not user_info:
        await message.answer("Сначала зарегистрируйтесь с помощью команды /start", reply_markup=ReplyKeyboardRemove())
        return
    
    schedule_text = await get_day_schedule(
        user_info['faculty'], int(user_info['course']), user_info['group'], message.text.lower()
    )
    await message.answer(schedule_text, parse_mode=ParseMode.MARKDOWN_V2)

@router.message(Command("reset"))
async def reset_cmd(message: Message, state: FSMContext, bot: Bot):
    # ... (код для сброса регистрации)
    user_id = message.from_user.id
    if await remove_user_data(user_id):
        await message.answer(
            "Регистрация сброшена. Используйте /start для новой регистрации.",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await message.answer(
            "Вы еще не зарегистрированы. Используйте /start для регистрации.",
            reply_markup=ReplyKeyboardRemove()
        )
    await state.clear()

@router.message(Command("me"))
async def me_cmd(message: Message, bot: Bot):
    # ... (код для просмотра своей регистрации)
    user_id = message.from_user.id
    user_info = await get_user_data(user_id)
    if user_info:
        response = (
            f"Ваши данные:\n"
            f"Факультет: {user_info['faculty']}\n"
            f"Курс: {user_info['course']}\n"
            f"Группа: {user_info['group']}"
        )
    else:
        response = "Вы еще не зарегистрированы. Используйте /start для регистрации."
    await message.answer(response)


# ===== НОВЫЕ ХЕНДЛЕРЫ ДЛЯ ПОИСКА ПРЕПОДАВАТЕЛЯ =====

def get_teacher_search_keyboard():
    """Создает inline-клавиатуру с датами для поиска преподавателя."""
    now = datetime.now(TZ)
    buttons = []
    for i in range(3): # Кнопки на сегодня, завтра, послезавтра
        date = now + timedelta(days=i)
        day_str = date.strftime("%d.%m.%Y")
        callback_data = f"teacher_date_{date.strftime('%Y-%m-%d')}"
        buttons.append(InlineKeyboardButton(text=day_str, callback_data=callback_data))
    
    return InlineKeyboardMarkup(inline_keyboard=[buttons])

# 1. Хендлер, который ловит ФИО (любое сообщение из 2+ слов)
@router.message(F.text, lambda msg: len(msg.text.split()) >= 2)
async def handle_teacher_name(message: Message, state: FSMContext):
    teacher_name = message.text.strip()
    await state.set_state(TeacherSearch.choosing_date)
    await state.update_data(teacher_name=teacher_name)
    await message.answer(
        f"🧑‍🏫 Вы ищете: *{teacher_name}*\n\nВыберите дату для поиска расписания:",
        reply_markup=get_teacher_search_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

# 2. Хендлер, который обрабатывает нажатие на кнопку с датой
@router.callback_query(TeacherSearch.choosing_date, F.data.startswith("teacher_date_"))
async def handle_teacher_date_selection(callback_query: types.CallbackQuery, state: FSMContext):
    date_str = callback_query.data.split("_")[2]
    target_date = datetime.strptime(date_str, "%Y-%m-%d")
    
    data = await state.get_data()
    teacher_name = data.get("teacher_name")
    
    if not teacher_name:
        await callback_query.message.edit_text("Ошибка: не удалось найти имя преподавателя. Попробуйте снова.", reply_markup=None)
        await state.clear()
        return

    await callback_query.message.edit_text("⏳ Ищу расписание, это может занять несколько секунд...", reply_markup=None)
    
    schedule_text = await get_teacher_schedule(teacher_name, target_date)
    
    await callback_query.message.edit_text(schedule_text, parse_mode=ParseMode.MARKDOWN_V2)
    
    await state.clear()```
