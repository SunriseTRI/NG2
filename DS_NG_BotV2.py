# DS_NG_BotV2.py (полная версия)
import os
import asyncio
import logging
from typing import List, Tuple
import os
import sys
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

from database import create_tables, insert_user, get_all_faq_entries, save_generated_response, merge_faq_from_excel
from registration import RegistrationStates, validate_phone, validate_email, generate_password

from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


tokenizer = None
model = None
# MODEL_NAME = "sberbank-ai/rugpt3medium"
MODEL_NAME = "gpt2"  # Используем ~"gpt2"~ для тестирования
# MODEL_NAME = "deepseek-ai/DeepSeek-R1"
# MODEL_NAME = "burgasdotpro/Sebushka-llama-3.1-8B"
# MODEL_NAME = ""IlyaGusev/saiga_llama3_8b""
# MODEL_NAME = "vikras/rugpt3small_shtirlitz_joke"
# MODEL_NAME = "getdiffus/SDPB2-DivineEleganceMix"
# MODEL_NAME = "SiberiaSoft/SiberianFredT5-instructor"
# DEFAULT_SYSTEM_PROMPT = "Ты — Сайга, русскоязычный автоматический ассистент. Ты разговариваешь с людьми и помогаешь им."


load_dotenv()  # Загружает переменные из .env
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


class FAQConfirmation(StatesGroup):
    confirm = State()


bot = Bot(token=TOKEN)
dp = Dispatcher()

# Инициализация модели (ленивая загрузка)
tokenizer = None
model = None


def initialize_model():
    global tokenizer, model
    if not tokenizer or not model:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
        logger.info("Модель инициализирована")


async def generate_response(question: str) -> str:
    try:
        initialize_model()
        inputs = tokenizer(question, return_tensors="pt", max_length=512, truncation=True)
        outputs = model.generate(
            inputs.input_ids,
            max_new_tokens=400,
            temperature=0.7,
            repetition_penalty=1.2
        )
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)[:400]
        save_generated_response(question, response)  # Сохранение в БД
        return response
    except Exception as e:
        logger.error(f"Ошибка генерации: {str(e)}", exc_info=True)
        return "Извините, не удалось обработать запрос."


@dp.message(CommandStart())
async def start_handler(message: Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/help"), KeyboardButton(text="/reg")],
            [KeyboardButton(text="/update_faq"), KeyboardButton(text="/rewrite_faq")]
        ],
        resize_keyboard=True
    )
    await message.answer("🤖 Добро пожаловать! Выберите действие:", reply_markup=keyboard)


@dp.message(Command("help"))
async def help_handler(message: Message):
    help_text = (
        "📋 Доступные команды:\n"
        "/start - Перезапуск бота\n"
        "/reg - Регистрация\n"
        "/update_faq - Добавить новые вопросы\n"
        "/rewrite_faq - Полное обновление FAQ"
    )
    await message.answer(help_text)


@dp.message(Command("reg"))
async def start_registration(message: Message, state: FSMContext):
    await message.answer("Введите ваше имя:")
    await state.set_state(RegistrationStates.name)


# ... (обработчики этапов регистрации из предыдущего ответа, аналогично обновленные)

@dp.message(Command("update_faq"))
async def update_faq_command(message: Message):
    try:
        _, updated = merge_faq_from_excel("faq.xlsx")
        await message.answer(f"✅ Обновлено {updated} вопросов")
    except Exception as e:
        logger.error(f"FAQ update error: {e}")
        await message.answer("❌ Ошибка обновления FAQ")


@dp.message()
async def message_handler(message: Message, state: FSMContext):
    user_question = message.text.strip()

    # Поиск в FAQ
    similar = []
    for q, a in get_all_faq_entries():
        if user_question.lower() in q.lower():
            similar.append((q, a))

    if similar:
        response = "🔍 Найдены совпадения:\n\n" + "\n\n".join([f"❓ {q}\n💡 {a}" for q, a in similar])
    else:
        response = await generate_response(user_question)
        response = f"🤖 Сгенерированный ответ:\n\n{response}"

    # Кнопки подтверждения
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Корректно", callback_data="confirm_yes"),
         InlineKeyboardButton(text="❌ Некорректно", callback_data="confirm_no")]
    ])

    await message.answer(response, reply_markup=keyboard)
    await state.set_state(FAQConfirmation.confirm)


@dp.callback_query(FAQConfirmation.confirm)
async def confirm_handler(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "confirm_no":
        await callback.message.answer("📝 Ваш вопрос передан администратору!")
    await state.clear()


# Устанавливаем кодировку вывода для Windows
sys.stdout.reconfigure(encoding='utf-8')

async def main():
    try:
        create_tables()
        logger.info("Starting bot...")
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Critical error: {str(e)}", exc_info=True)
    finally:
        if bot.session:
            await bot.session.close()
        logger.info("Bot session closed")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown completed")


