from aiogram.fsm.state import State, StatesGroup

class Registration(StatesGroup):
    choosing_faculty = State()
    choosing_course = State()
    choosing_group = State()

class TeacherSearch(StatesGroup):
    choosing_date = State()

class Notes(StatesGroup):
    writing_note = State()
