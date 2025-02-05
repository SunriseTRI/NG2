import os
import asyncio
import logging
import sys
import re

from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

from loguru import logger
from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import create_tables, insert_user, merge_faq_from_excel, update_faq_from_excel, get_all_faq_entries, insert_faq_entry
from registration import validate_phone, validate_email, generate_password, RegistrationStates

# Для вычисления похожести строк
from rapidfuzz import fuzz


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

# Токен бота
TOKEN = "7689394185:AAF6-bgn2UowWXJje_xrF3zhTsojzNSvEGA"

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(bot=bot)

# Новый FSM-стейт для подтверждения FAQ-ответа
class FAQConfirmation(StatesGroup):
    confirm = State()
    # Здесь можно сохранить данные о найденных FAQ, если потребуется их дальнейшая обработка

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

def find_similar_faq_entries(user_question: str, threshold: float = 85.0):
    """
    Получает все записи FAQ и возвращает список записей, у которых похожесть вопроса
    с user_question не ниже threshold (в процентах). Каждая запись – кортеж (faq_question, faq_answer, similarity).
    """
    from database import get_all_faq_entries  # Функция, которая должна возвращать список всех FAQ: [(question, answer), ...]
    faq_entries = get_all_faq_entries()
    similar = []
    for faq_question, faq_answer in faq_entries:
        similarity = fuzz.ratio(user_question.lower(), faq_question.lower())
        if similarity >= threshold:
            similar.append((faq_question, faq_answer, similarity))
    # Можно отсортировать по убыванию похожести
    similar.sort(key=lambda x: x[2], reverse=True)
    return similar

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    logger.info(f"User {message.from_user.full_name} started the bot.")
    await message.answer("Привет! Я бот-помощник. Используйте /help для списка команд.")

@dp.message(Command('help'))
async def help_handler(message: Message) -> None:
    logger.info(f"User {message.from_user.full_name} requested help.")
    help_text = (
        "Вот список доступных команд:\n\n"
        "/start - Запуск бота\n"
        "/help - Список команд\n"
        "/reg - Регистрация пользователя\n"
        "/update_faq - Обновить FAQ\n"
        "/rewrite_faq - Перезаписать FAQ"
    )
    await message.answer(help_text)

# Обработчики регистрации (без изменений, см. registration.py)
@dp.message(Command("reg"))
async def start_registration(message: Message, state: FSMContext):
    await message.answer("Введите ваше имя:")
    await state.set_state(RegistrationStates.name)

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

@dp.message(Command("update_faq"))
async def update_faq_command(message: Message):
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        faq_path = os.path.join(current_dir, "faq.xlsx")
        new_entries, updated_entries = merge_faq_from_excel(faq_path)
        response = f"FAQ обновлен из Excel-файла.\nДобавлено новых вопросов: {new_entries}\nОбновлено существующих вопросов: {updated_entries}"
        await message.answer(response)
    except Exception as e:
        await message.answer(f"Ошибка при обновлении FAQ: {e}")

@dp.message(Command("rewrite_faq"))
async def rewrite_faq_command(message: Message):
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        faq_path = os.path.join(current_dir, "faq.xlsx")
        update_faq_from_excel(faq_path)
        await message.answer("FAQ перезаписан из Excel-файла.")
    except Exception as e:
        await message.answer(f"Ошибка при перезаписи FAQ: {e}")

# Новый обработчик подтверждения FAQ-ответа
@dp.message(FAQConfirmation.confirm)
async def process_confirmation(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    data = await state.get_data()
    original_question = data.get("original_question", "")
    if text in ["да", "yes"]:
        await message.answer("Рад, что смог помочь!")
    elif text in ["нет", "no"]:
        # Вносим вопрос с меткой «Необходим ответ от @админ»
        insert_faq_entry(original_question, "Необходим ответ от @админ")
        await message.answer("Ваш вопрос внесён в базу для дальнейшего рассмотрения. Спасибо за отзыв!")
    else:
        await message.answer("Пожалуйста, ответьте 'да' или 'нет'.")
        return  # Не очищаем состояние, ждем корректного ответа
    await state.clear()

# Основной обработчик текстовых сообщений
@dp.message()
async def echo_handler(message: Message, state: FSMContext) -> None:
    user_question = message.text.strip()
    username = message.from_user.full_name

    # Ищем похожие записи FAQ (с порогом 85%)
    similar_faqs = find_similar_faq_entries(user_question, threshold=85.0)

    if similar_faqs:
        # Если есть точное совпадение (100%), выдаём его сразу
        exact_matches = [entry for entry in similar_faqs if entry[2] == 100]
        if exact_matches:
            faq_q, faq_a, sim = exact_matches[0]
            response = (
                f"Пользователь: {username} спросил:\n\"{user_question}\"\n\n"
                f"Найден FAQ:\nВопрос: {faq_q}\nОтвет: {faq_a}"
            )
            await message.answer(response)
            return  # Завершаем обработку, подтверждение не требуется

        # Если совпадения есть, но они не идеальные, выводим все варианты и запрашиваем подтверждение
        response_lines = [
            f"Пользователь: {username} спросил:\n\"{user_question}\"\n",
            "Найдены похожие FAQ:"
        ]
        for idx, (faq_q, faq_a, sim) in enumerate(similar_faqs, start=1):
            response_lines.append(
                f"{idx}. Вопрос: {faq_q}\n   Ответ: {faq_a}\n   Похожесть: {sim:.1f}%"
            )
        response_lines.append("\nВаш вопрос был обработан таким образом. Всё ли корректно? (да/нет)")
        await state.update_data(original_question=user_question)
        await state.set_state(FAQConfirmation.confirm)
        await message.answer("\n".join(response_lines))
    else:
        # Если совпадений не найдено, используем NLP-модель для генерации ответа
        nlp_answer = await generate_response(user_question)
        response_lines = [
            f"Пользователь: {username} спросил:\n\"{user_question}\"\n",
            "Ответ, сгенерированный на основе NLP-модели:",
            nlp_answer,
            "\nВаш вопрос был обработан таким образом. Всё ли корректно? (да/нет)"
        ]
        await state.update_data(original_question=user_question)
        await state.set_state(FAQConfirmation.confirm)
        await message.answer("\n".join(response_lines))

    # # Ищем похожие записи FAQ (с порогом 85%)
    # similar_faqs = find_similar_faq_entries(user_question, threshold=85.0)
    #
    # if similar_faqs:
    #     response_lines = [
    #         f"Пользователь: {username} спросил:\n\"{user_question}\"\n",
    #         "Найдены похожие FAQ:"
    #     ]
    #     for idx, (faq_q, faq_a, sim) in enumerate(similar_faqs, start=1):
    #         response_lines.append(f"{idx}. Вопрос: {faq_q}\n   Ответ: {faq_a}\n   Похожесть: {sim:.1f}%")
    #     response_lines.append("\nВаш вопрос был обработан таким образом. Всё ли корректно? (да/нет)")
    #     await state.update_data(original_question=user_question)
    #     await state.set_state(FAQConfirmation.confirm)
    #     await message.answer("\n".join(response_lines))
    # else:
    #     # Если совпадений не найдено, обращаемся к NLP-модели для генерации ответа
    #     nlp_answer = await generate_response(user_question)
    #     response_lines = [
    #         f"Пользователь: {username} спросил:\n\"{user_question}\"\n",
    #         "Ответ, сгенерированный на основе NLP-модели:",
    #         nlp_answer,
    #         "\nВаш вопрос был обработан таким образом. Всё ли корректно? (да/нет)"
    #     ]
    #     await state.update_data(original_question=user_question)
    #     await state.set_state(FAQConfirmation.confirm)
    #     await message.answer("\n".join(response_lines))

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
        await bot.session.close()
        logger.info("Бот успешно завершил работу.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Выключение сервера... (нажат Ctrl+C)")
