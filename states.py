from aiogram.fsm.state import State, StatesGroup

class Registration(StatesGroup):
    choosing_faculty = State()
    choosing_course = State()
    choosing_group = State()

class TeacherSearch(StatesGroup):
    choosing_date = State()

# ===== НОВЫЙ КЛАСС СОСТОЯНИЙ ДЛЯ ЗАМЕТОК =====
class Notes(StatesGroup):
    writing_note = State()
