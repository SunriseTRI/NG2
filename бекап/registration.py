import re
import secrets
import string
from aiogram.fsm.state import State, StatesGroup

from aiogram.fsm.state import State, StatesGroup

# Состояния для регистрации
class RegistrationStates(StatesGroup):
    name = State()
    surname = State()
    age = State()
    phone = State()
    email = State()
    user_type = State()

def validate_phone(phone: str) -> bool:
    return re.match(r"^\+\d{10,12}$", phone) is not None

def validate_email(email: str) -> bool:
    return re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email) is not None

def generate_password(length=8) -> str:
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))
command_functions = {}