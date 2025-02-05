import os
import asyncio
import logging
import sys
import re
import secrets
import string
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import yaml

from loguru import logger
from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import *
from registration import *

print(yaml.__version__)

# Загрузка модели и токенизатора
MODEL_NAME = "gpt2"  # Используем ~"gpt2"~ для тестирования
# MODEL_NAME = "deepseek-ai/DeepSeek-R1"
# MODEL_NAME = "burgasdotpro/Sebushka-llama-3.1-8B"
# MODEL_NAME = ""IlyaGusev/saiga_llama3_8b""
# MODEL_NAME = "vikras/rugpt3small_shtirlitz_joke"
# MODEL_NAME = "getdiffus/SDPB2-DivineEleganceMix"
# MODEL_NAME = "SiberiaSoft/SiberianFredT5-instructor"
# DEFAULT_SYSTEM_PROMPT = "Ты — Сайга, русскоязычный автоматический ассистент. Ты разговариваешь с людьми и помогаешь им."
tokenizer = None
model = None

# Настройка логирования
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# Токен бота
TOKEN = "7689394185:AAF6-bgn2UowWXJje_xrF3zhTsojzNSvEGA"

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(bot=bot)


# Функция для генерации ответа с использованием модели
async def generate_response(question: str) -> str:
    try:
        inputs = tokenizer(question, return_tensors="pt")
        outputs = model.generate(**inputs, max_length=100, num_return_sequences=1)
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return response
    except Exception as e:
        logger.error(f"Ошибка при генерации ответа: {e}")
        return "Извините, произошла ошибка при обработке вашего запроса."

# Обработчик команды /start
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
        Команда, которая здаровкается.
    """
    logger.info(f"User {message.from_user.full_name} started the bot.")
    await message.answer("Привет! Я бот-помощник. Используйте /help для списка команд.")

# command_functions = {}

# Обработчик команды /help


@dp.message(Command('help'))
async def help_handler(message: Message) -> None:
    logger.info(f"User {message.from_user.full_name} requested help.")
    help_text = "Вот список доступных команд:\n\n"
    help_text += "/start - Запуск бота\n"
    help_text += "/help - Список команд\n"
    help_text += "/reg - Регистрация пользователя\n"
    # help_text += "/get_faq - Получить FAQ\n"
    help_text += "/update_faq - Обновить FAQ\n"
    help_text += "/rewrite_faq - Перезаписать FAQ\n"
    await message.answer(help_text)

# Обработчик команды /reg
@dp.message(Command("reg"))
async def start_registration(message: Message, state: FSMContext):
    """
    Команда, которая крысит ваши данные под видом регистрации.
    """
    await message.answer("Введите ваше имя:")
    await state.set_state(RegistrationStates.name)

# Обработчики для регистрации
@dp.message(RegistrationStates.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите вашу фамилию:")
    await state.set_state(RegistrationStates.surname)

@dp.message(RegistrationStates.surname)
async def process_surname(message: Message, state: FSMContext):
    await state.update_data(surname=message.text)
    await message.answer("Введите ваш возраст:")
    await state.set_state(RegistrationStates.age)

@dp.message(RegistrationStates.age)
async def process_age(message: Message, state: FSMContext):
    if message.text.isdigit() and 0 < int(message.text) < 120:
        await state.update_data(age=int(message.text))
        await message.answer("Введите ваш номер телефона (в формате +1234567890):")
        await state.set_state(RegistrationStates.phone)
    else:
        await message.answer("Введите корректный возраст!")

@dp.message(RegistrationStates.phone)
async def process_phone(message: Message, state: FSMContext):
    if validate_phone(message.text.strip()):
        await state.update_data(phone=message.text.strip())
        await message.answer("Введите ваш email:")
        await state.set_state(RegistrationStates.email)
    else:
        await message.answer("Введите корректный номер телефона!")

@dp.message(RegistrationStates.email)
async def process_email(message: Message, state: FSMContext):
    if validate_email(message.text.strip()):
        await state.update_data(email=message.text.strip())
        await message.answer("Выберите тип пользователя (patient, worker, admin, creator):")
        await state.set_state(RegistrationStates.user_type)
    else:
        await message.answer("Введите корректный email!")

@dp.message(RegistrationStates.user_type)
async def process_user_type(message: Message, state: FSMContext):
    user_type = message.text.strip().lower()
    if user_type in ["patient", "worker", "admin", "creator"]:
        await state.update_data(user_type=user_type)
        user_data = await state.get_data()
        password = generate_password()

        user_data_tuple = (
            message.from_user.username, user_data['name'], user_data['surname'],
            user_data['age'], user_data['phone'], user_data['email'],
            user_data['user_type'], password
        )
        insert_user(user_data_tuple)

        await message.answer(f"Регистрация завершена!\nВаш пароль: {password}")
        await state.clear()
    else:
        await message.answer("Выберите корректный тип пользователя!")

# Обработчик команд FAQ
@dp.message(Command("update_faq"))
async def update_faq_command(message: Message):
    """
    Команда, которая обновляет фак методом миграции.
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        faq_path = os.path.join(current_dir, "faq.xlsx")

        new_entries, updated_entries = merge_faq_from_excel(faq_path)

        response = f"FAQ обновлен из Excel-файла.\n"
        response += f"Добавлено новых вопросов: {new_entries}\n"
        response += f"Обновлено существующих вопросов: {updated_entries}"

        await message.answer(response)
    except Exception as e:
        await message.answer(f"Ошибка при обновлении FAQ: {e}")

@dp.message(Command("rewrite_faq"))
async def update_faq_command(message: Message):
    """
    Команда, которая дает унечтожит текущий фак и перезапишет его тем что есть в эксель.
    """
    try:
        # Получаем путь к директории, в которой находится текущий скрипт
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Формируем путь к файлу FAQ относительно текущей директории
        faq_path = os.path.join(current_dir, "faq.xlsx")

        update_faq_from_excel(faq_path)
        await message.answer("FAQ перезаписан из Excel-файла.")
    except Exception as e:
        await message.answer(f"Ошибка при перезаписи FAQ: {e}")



# Обработчик текстовых сообщений
@dp.message()
async def echo_handler(message: Message) -> None:
    question = message.text.strip()
    answer = get_faq_answer(question)

    if answer == "Необходим ответ от @админ":
        answer = await generate_response(question)

    await message.answer(answer)

# Запуск бота
async def main() -> None:
    global tokenizer, model
    try:
        create_tables()  # Создание таблиц в базе данных, если их нет
        logger.info("Загрузка модели...")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
        logger.info("Модель и токенизатор успешно загружены.")
        logger.info("Бот запущен! Ожидание сообщений...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при работе бота: {e}")
    finally:
        await bot.session.close()  # Закрываем сессию бота
        logger.info("Бот успешно завершил работу.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Выключение сервера... (нажат Ctrl+C)")