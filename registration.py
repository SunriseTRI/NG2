
import re
import secrets
import string
import logging
from email_validator import validate_email, EmailNotValidError
from aiogram.fsm.state import State, StatesGroup

logger = logging.getLogger(__name__)

class RegistrationStates(StatesGroup):
    name = State()
    surname = State()
    age = State()
    phone = State()
    email = State()
    user_type = State()

def validate_phone(phone: str) -> bool:
    pattern = r"^\+\d{1,3}\d{10}$"  # Обновленный паттерн для телефона
    return re.match(pattern, phone) is not None

def validate_email(email: str) -> bool:
    try:
        validate_email(email)
        return True
    except EmailNotValidError:
        return False

def generate_password(length=12) -> str:  # Увеличенная длина пароля
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

command_functions = {}