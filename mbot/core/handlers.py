from aiogram import Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from .database import get_faq_answer, insert_faq_question, is_user_registered
from .registration import start_registration, process_name, process_phone, RegistrationStates
from .generator import generate_response
# from .okdesk_integration import create_ticket  # отключено

CONTACT_KB = ReplyKeyboardMarkup(
    [[KeyboardButton(text="Поделиться контактом", request_contact=True)]],
    resize_keyboard=True, one_time_keyboard=True
)

HELP_TEXT = (
    "/start - начать\n"
    "/reg - регистрация\n"
    "/faq - задать вопрос\n"
)

async def cmd_start(message: types.Message):
    if is_user_registered(message.from_user.id):
        await message.answer("Привет! Задайте ваш вопрос.", reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer("Сначала зарегистрируйтесь:", reply_markup=CONTACT_KB)

async def cmd_help(message: types.Message):
    await message.answer(HELP_TEXT)

async def cmd_reg(message: types.Message, state: FSMContext):
    await start_registration(message, state)

async def faq_handler(message: types.Message, state: FSMContext):
    if not is_user_registered(message.from_user.id):
        return await message.answer("❌ Сначала пройдите регистрацию!", reply_markup=CONTACT_KB)
    question = message.text.strip()
    answer = get_faq_answer(question)
    if answer:
        await message.answer(answer)
    else:
        insert_faq_question(question)
        await message.answer("Вопрос принят, мы скоро дадим ответ.")

async def contact_handler(message: types.Message, state: FSMContext):
    if message.contact:
        user = message.from_user
        name = message.contact.first_name or ''
        phone = message.contact.phone_number
        from .database import insert_user
        insert_user(user.id, user.username or '', phone, name)
        await message.answer("Регистрация прошла успешно!", reply_markup=ReplyKeyboardRemove())

async def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_reg, Command("reg"), state=None)
    dp.message.register(contact_handler, lambda msg: msg.contact is not None)
    dp.message.register(process_name, state=RegistrationStates.waiting_for_name)
    dp.message.register(process_phone, state=RegistrationStates.waiting_for_phone)
    dp.message.register(faq_handler)