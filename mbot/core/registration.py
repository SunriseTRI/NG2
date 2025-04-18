from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import re

# Состояния регистрации
class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()

PHONE_REGEX = r"^\+\d{1,3}\d{7,10}$"

async def start_registration(message: types.Message, state: FSMContext):
    await message.answer("Введите ваше имя:")
    await state.set_state(RegistrationStates.waiting_for_name)

async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите номер телефона (+XXXXXXXXXXX):")
    await state.set_state(RegistrationStates.waiting_for_phone)

async def process_phone(message: types.Message, state: FSMContext, db):
    if not re.match(PHONE_REGEX, message.text):
        return await message.answer("Неверный формат. Попробуйте ещё раз:")
    data = await state.get_data()
    name = data['name']
    phone = message.text
    user = message.from_user
    # Сохраняем в БД
    db.insert_user(user.id, user.username or '', phone, name)
    await message.answer(f"Регистрация завершена, {name}!")
    await state.clear()