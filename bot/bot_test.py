# bot.py
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

from dotenv import load_dotenv
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

# URL вашего Mini App (должен быть HTTPS!)
MINI_APP_URL = "https://fstbot.ru"

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Создаем клавиатуру с одной кнопкой
def get_main_keyboard():
    button = KeyboardButton(
        text="🚀 Открыть MiniApps",
        web_app=WebAppInfo(url=MINI_APP_URL)
    )
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[button]],
        resize_keyboard=True  # Автоматический размер
    )
    return keyboard

# Обработчик команды /start
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "Привет! Нажми на кнопку ниже, чтобы открыть Mini App:",
        reply_markup=get_main_keyboard()
    )

# Обработчик команды /help
@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "Нажми на кнопку 'Открыть MiniApps' чтобы запустить приложение\n"
    )

# Обработчик любых других сообщений
@dp.message()
async def echo_message(message: types.Message):
    await message.answer(
        "Используй кнопку ниже 👇",
        reply_markup=get_main_keyboard()
    )

# Запуск бота
async def main():
    print("🚀 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())