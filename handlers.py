from aiogram import Router, F, Bot, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from config import FACULTIES, GROUP_CHAT_ID, update_user_data, remove_user_data, get_user_data
from states import Registration
from schedule_parser import get_day_schedule, get_available_groups
import os

router = Router()
bot = Bot(token=os.getenv("BOT_TOKEN"))

# ID канала для проверки подписки
CHANNEL_USERNAME = "@smartschedule0"

# Клавиатура для проверки подписки
def get_subscription_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться на канал", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_subscription")]
        ]
    )

# Клавиатура для факультетов
def get_faculties_keyboard():
    buttons = []
    row = []
    for faculty in FACULTIES.keys():
        row.append(KeyboardButton(text=faculty))
        if len(row) == 2:  # По 2 кнопки в ряду
            buttons.append(row)
            row = []
    if row:  # Добавляем оставшиеся кнопки
        buttons.append(row)
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )

# Клавиатура для курсов
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

# Клавиатура для дней расписания
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

async def check_user_subscription(user_id: int) -> bool:
    """Проверяет, подписан ли пользователь на канал"""
    try:
        chat_member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        return False

# Обработчик проверки подписки
@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    
    if await check_user_subscription(user_id):
        await callback_query.message.edit_text(
            "✅ Спасибо за подписку! Теперь вы можете пользоваться ботом.",
            reply_markup=None
        )
        
        # Показываем клавиатуру расписания, если пользователь уже зарегистрирован
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

# Старт регистрации
@router.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    # Проверяем подписку
    if not await check_user_subscription(message.from_user.id):
        await message.answer(
            "⚠️ Для использования бота необходимо подписаться на наш канал!",
            reply_markup=get_subscription_keyboard()
        )
        return
    
    # Удаляем старые данные пользователя при перезапуске
    user_id = message.from_user.id
    old_user_data = await get_user_data(user_id)
    
    if old_user_data:
        # Отправляем уведомление об удалении старой записи
        try:
            admin_message = (
                f"🗑 Удалена старая запись пользователя:\n"
                f"Имя: {old_user_data.get('full_name', 'Неизвестно')}\n"
                f"Username: {old_user_data.get('username', 'нет username')}\n"
                f"Факультет: {old_user_data.get('faculty', 'Неизвестно')}\n"
                f"Курс: {old_user_data.get('course', 'Неизвестно')}\n"
                f"Группа: {old_user_data.get('group', 'Неизвестно')}"
            )
            await bot.send_message(chat_id=GROUP_CHAT_ID, text=admin_message)
        except Exception as e:
            print(f"Не удалось отправить сообщение об удалении: {e}")
        
        await remove_user_data(user_id)
    
    await message.answer(
        "Добро пожаловать! Выберите ваш факультет:",
        reply_markup=get_faculties_keyboard()
    )
    await state.set_state(Registration.choosing_faculty)

# Выбор факультета
@router.message(Registration.choosing_faculty, F.text.in_(FACULTIES.keys()))
async def faculty_chosen(message: Message, state: FSMContext):
    # Проверяем подписку
    if not await check_user_subscription(message.from_user.id):
        await message.answer(
            "⚠️ Для использования бота необходимо подписаться на наш канал!",
            reply_markup=get_subscription_keyboard()
        )
        return
    
    faculty = message.text
    await state.update_data(faculty=faculty)
    await message.answer(
        "Отлично! Теперь выберите ваш курс:",
        reply_markup=get_courses_keyboard()
    )
    await state.set_state(Registration.choosing_course)

# Неверный выбор факультета
@router.message(Registration.choosing_faculty)
async def wrong_faculty(message: Message):
    # Проверяем подписку
    if not await check_user_subscription(message.from_user.id):
        await message.answer(
            "⚠️ Для использования бота необходимо подписаться на наш канал!",
            reply_markup=get_subscription_keyboard()
        )
        return
    
    await message.answer(
        "Пожалуйста, выберите факультет из предложенных вариантов:",
        reply_markup=get_faculties_keyboard()
    )

# Выбор курса
@router.message(Registration.choosing_course, F.text.in_(["1", "2", "3", "4", "5"]))
async def course_chosen(message: Message, state: FSMContext):
    # Проверяем подписку
    if not await check_user_subscription(message.from_user.id):
        await message.answer(
            "⚠️ Для использования бота необходимо подписаться на наш канал!",
            reply_markup=get_subscription_keyboard()
        )
        return
    
    course = message.text
    data = await state.get_data()
    faculty = data['faculty']
    
    # Получаем доступные группы для выбранного факультета и курса
    groups = get_available_groups(faculty, int(course))
    
    if not groups:
        await message.answer(
            f"Для {faculty} {course} курс не найдено расписания.\nПопробуйте выбрать другой курс или факультет:",
            reply_markup=get_courses_keyboard()
        )
        return
    
    await state.update_data(course=course, available_groups=groups)
    
    # Создаем клавиатуру с группами
    group_buttons = []
    row = []
    for group in groups:
        row.append(KeyboardButton(text=group))
        if len(row) == 3:  # По 3 кнопки в ряду
            group_buttons.append(row)
            row = []
    if row:
        group_buttons.append(row)
    
    group_keyboard = ReplyKeyboardMarkup(
        keyboard=group_buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(
        "Отлично! Теперь выберите вашу группу:",
        reply_markup=group_keyboard
    )
    await state.set_state(Registration.choosing_group)

# Неверный выбор курса
@router.message(Registration.choosing_course)
async def wrong_course(message: Message):
    # Проверяем подписку
    if not await check_user_subscription(message.from_user.id):
        await message.answer(
            "⚠️ Для использования бота необходимо подписаться на наш канал!",
            reply_markup=get_subscription_keyboard()
        )
        return
    
    await message.answer(
        "Пожалуйста, выберите курс от 1 до 5:",
        reply_markup=get_courses_keyboard()
    )

# Выбор группы
@router.message(Registration.choosing_group)
async def group_chosen(message: Message, state: FSMContext):
    # Проверяем подписку
    if not await check_user_subscription(message.from_user.id):
        await message.answer(
            "⚠️ Для использования бота необходимо подписаться на наш канал!",
            reply_markup=get_subscription_keyboard()
        )
        return
    
    group = message.text
    data = await state.get_data()
    available_groups = data.get('available_groups', [])
    
    if group not in available_groups:
        await message.answer(
            "Пожалуйста, выберите группу из предложенных вариантов:"
        )
        return
    
    # Сохраняем выбор пользователя в базу данных
    user_id = message.from_user.id
    user_info = {
        'faculty': data['faculty'],
        'course': data['course'],
        'group': group,
        'username': f"@{message.from_user.username}" if message.from_user.username else "нет username",
        'full_name': message.from_user.full_name or "Неизвестно"
    }
    
    await update_user_data(user_id, user_info)
    
    # Отправляем уведомление в группу
    admin_message = (
        f"✅ Новый пользователь зарегистрирован:\n"
        f"Имя: {user_info['full_name']}\n"
        f"Username: {user_info['username']}\n"
        f"Факультет: {user_info['faculty']}\n"
        f"Курс: {user_info['course']}\n"
        f"Группа: {user_info['group']}"
    )
    
    try:
        await bot.send_message(chat_id=GROUP_CHAT_ID, text=admin_message)
    except Exception as e:
        print(f"Не удалось отправить сообщение в группу: {e}")
        # Пробуем отправить как строку, если число не работает
        try:
            await bot.send_message(chat_id=str(GROUP_CHAT_ID), text=admin_message)
        except Exception as e2:
            print(f"Не удалось отправить сообщение в группу (строка): {e2}")
    
    await message.answer(
        f"✅ Регистрация завершена!\n"
        f"Факультет: {data['faculty']}\n"
        f"Курс: {data['course']}\n"
        f"Группа: {group}\n\n"
        f"Теперь вы можете посмотреть расписание:",
        reply_markup=get_schedule_keyboard()
    )
    await state.clear()

# Обработчик расписания для зарегистрированных пользователей
@router.message(F.text.lower().in_({"сегодня", "завтра", "пн", "вт", "ср", "чт", "пт", "сб"}))
async def day_selected(message: Message):
    user_id = message.from_user.id
    
    # Проверяем подписку
    if not await check_user_subscription(user_id):
        await message.answer(
            "⚠️ Для использования бота необходимо подписаться на наш канал!",
            reply_markup=get_subscription_keyboard()
        )
        return
    
    user_info = await get_user_data(user_id)
    
    if not user_info:
        await message.answer(
            "Сначала зарегистрируйтесь с помощью команды /start",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    text = message.text.lower()
    
    # Получаем расписание
    schedule_text = get_day_schedule(
        user_info['faculty'],
        int(user_info['course']),
        user_info['group'],
        text
    )
    
    await message.answer(schedule_text, parse_mode=ParseMode.MARKDOWN_V2)

# Команда для сброса регистрации
@router.message(Command("reset"))
async def reset_cmd(message: Message, state: FSMContext):
    # Проверяем подписку
    if not await check_user_subscription(message.from_user.id):
        await message.answer(
            "⚠️ Для использования бота необходимо подписаться на наш канал!",
            reply_markup=get_subscription_keyboard()
        )
        return
    
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

# Команда для просмотра своей текущей регистрации
@router.message(Command("me"))
async def me_cmd(message: Message):
    user_id = message.from_user.id
    
    # Проверяем подписку
    if not await check_user_subscription(user_id):
        await message.answer(
            "⚠️ Для использования бота необходимо подписаться на наш канал!",
            reply_markup=get_subscription_keyboard()
        )
        return
    
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

