from aiogram.fsm.state import State, StatesGroup

class Registration(StatesGroup):
    choosing_faculty = State()
    choosing_course = State()
    choosing_group = State()

# ===== НОВЫЙ КЛАСС СОСТОЯНИЙ =====
class TeacherSearch(StatesGroup):
    choosing_date = State()
