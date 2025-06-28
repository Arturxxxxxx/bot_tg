from aiogram.fsm.state import StatesGroup, State

class AuthCompanyStates(StatesGroup):
    waiting_for_code = State()

class LoadDataStates(StatesGroup):
    choosing_time = State()
    choosing_week = State()  
    choosing_day = State()
    entering_portion = State()
