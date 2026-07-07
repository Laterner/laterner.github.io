# bot.py
import asyncio
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    WebAppInfo,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from database import db
from utils import (
    generate_player_id,
    get_team_emoji,
    get_team_name,
    get_team_description,
    format_player_id,
    hash_user_id
)

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")
MINI_APP_URL = os.getenv("MINI_APP_URL")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле!")
if not MINI_APP_URL:
    raise ValueError("MINI_APP_URL не найден в .env файле!")

# Команды
TEAMS = {
    "1": {
        "name": "Выгода",
        "emoji": "👤",
        "description": "",
        "color": "#FF4444"
    },
    "2": {
        "name": "Реклама",
        "emoji": "👤",
        "description": "",
        "color": "#4444FF"
    },
    "3": {
        "name": "Город",
        "emoji": "👤",
        "description": "",
        "color": "#44FF44"
    },
    "4": {
        "name": "Покупки",
        "emoji": "👤",
        "description": "",
        "color": "#44FF44"
    },
    "5": {
        "name": "Путешествия",
        "emoji": "👤",
        "description": "",
        "color": "#44FF44"
    },
    "6": {
        "name": "Т-Авто",
        "emoji": "👤",
        "description": "",
        "color": "#44FF44"
    },
    "7": {
        "name": "Общие платформы",
        "emoji": "👤",
        "description": "",
        "color": "#44FF44"
    },
    "8": {
        "name": "Команда аналитики, роста и монетизации",
        "emoji": "👤",
        "description": "",
        "color": "#44FF44"
    },
    "9": {
        "name": "HR",
        "emoji": "👤",
        "description": "",
        "color": "#44FF44"
    }
}

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния регистрации
class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_team = State()

# Клавиатуры
def get_main_keyboard():
    """Главная клавиатура с кнопкой Mini App"""
    button_miniapp = KeyboardButton(
        text="🚀 Открыть MiniApps",
        web_app=WebAppInfo(url=MINI_APP_URL)
    )
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Мой профиль")],
            [KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="🏆 Топ игроков")],
            [button_miniapp]
            # [KeyboardButton(text="🔄 Сменить команду")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_team_keyboard():
    """Клавиатура выбора команды"""

    builder = InlineKeyboardBuilder()

    for key, team in TEAMS.items():
        builder.button(
            text=f"Команда {key}",
            callback_data=f"team_{key}"
        )
    # Распределить по строкам, например по 3 кнопки в ряд
    builder.adjust(3)
    keyboard = builder.as_markup()

    # buttons = []
    # for key, team in TEAMS.items():
    #     print("add button -------->", f"team_{key}")
    #     buttons.append(
    #         InlineKeyboardButton(
    #             text=f"{key}",
    #             callback_data=f"team_{key}"
    #         )
    #     )

        
    # keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])
    return keyboard

# Обработчики команд

@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if user and user.get('registered', False):
        # Пользователь уже зарегистрирован
        await message.answer(
            f"👋 С возвращением, {user['name']}!\n\n"
            f"🎮 Player ID: {format_player_id(user['player_id'])}\n"
            f"⚔️ Команда: {TEAMS[user['team']]['emoji']} {TEAMS[user['team']]['name']}\n"
            f"⭐ Очки: {user['score']}\n"
            f"🏆 Побед: {user['wins']} | Поражений: {user['losses']}\n\n"
            "Используй кнопки ниже:",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
        await db.add_history(user_id, "start", "Повторный запуск")
    else:
        # Начинаем регистрацию
        await state.set_state(RegistrationStates.waiting_for_name)
        await message.answer(
            "🎮 <b>Добро пожаловать в fstbot.ru!</b>\n\n"
            "Для начала игры давай познакомимся.\n"
            "Как мне к тебе обращаться?\n\n"
            "<i>Напиши свое имя (можно никнейм)</i>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )

@dp.message(Command("profile"))
async def profile_command(message: types.Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user or not user.get('registered', False):
        await message.answer(
            "❌ Ты еще не зарегистрирован!\n"
            "Напиши /start для регистрации"
        )
        return
    
    history = await db.get_user_history(user_id, 5)
    history_text = "\n".join([
        f"• {h['action']} ({h['timestamp'][:16]})" 
        for h in history
    ]) if history else "Нет записей"
    
    await message.answer(
        f"👤 <b>Твой профиль</b>\n\n"
        f"📛 Имя: {user['name']}\n"
        f"🎮 Player ID: {format_player_id(user['player_id'])}\n"
        f"⚔️ Команда: {TEAMS[user['team']]['emoji']} {TEAMS[user['team']]['name']}\n"
        f"⭐ Очки: {user['score']}\n"
        f"🏆 Побед: {user['wins']}\n"
        f"💔 Поражений: {user['losses']}\n"
        f"🎯 Игр сыграно: {user['games_played']}\n"
        f"🆔 Telegram ID: <code>{user_id}</code>\n\n"
        f"📜 <b>Последние действия:</b>\n{history_text}",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )
    
    await db.add_history(user_id, "profile", "Просмотр профиля")

@dp.message(Command("team"))
async def team_command(message: types.Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user or not user.get('registered', False):
        await message.answer("❌ Сначала зарегистрируйся: /start")
        return
    
    for key, team in TEAMS.items():
        _teams += f"{key}: {team['name']}\n"
        
    await message.answer(
        "⚔️ <b>Выбери свою команду:</b>\n\n"
        f"{_teams}\n\n"
        "Нажми на кнопку, чтобы выбрать:",
        parse_mode="HTML",
        reply_markup=get_team_keyboard()
    )

@dp.message(Command("top"))
async def top_command(message: types.Message):
    top_players = await db.get_top_players(10)
    
    if not top_players:
        await message.answer("📊 Пока нет игроков в топе!")
        return
    
    text = "🏆 <b>Топ 10 игроков</b>\n\n"
    for i, player in enumerate(top_players, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        text += (
            f"{medal} <b>{player['name']}</b>\n"
            f"   🎮 {format_player_id(player['player_id'])}\n"
            f"   ⚔️ {TEAMS[player['team']]['emoji']} {TEAMS[player['team']]['name']}\n"
            f"   ⭐ {player['score']} очков | 🏆 {player['wins']} игр\n\n"
        )
    
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user or not user.get('registered', False):
        await message.answer("❌ Сначала зарегистрируйся: /start")
        return
    
    team_stats = await db.get_team_stats(user['team'])
    
    if team_stats:
        text = (
            f"📊 <b>Статистика команды {TEAMS[user['team']]['name']}</b>\n\n"
            f"👥 Игроков: {team_stats['total_players']}\n"
            f"🎯 Игр сыграно: {team_stats['total_games']}\n"
            f"🏆 Побед: {team_stats['total_wins']}\n"
        )
    else:
        text = f"📊 Статистика команды {TEAMS[user['team']]['name']} пока пуста"
    
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("history"))
async def history_command(message: types.Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user or not user.get('registered', False):
        await message.answer("❌ Сначала зарегистрируйся: /start")
        return
    
    history = await db.get_user_history(user_id, 20)
    
    if not history:
        await message.answer("📜 История действий пуста")
        return
    
    text = "📜 <b>История действий</b>\n\n"
    for h in history:
        text += f"• {h['action']} - {h['details'] or '—'} ({h['timestamp'][:16]})\n"
    
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "🤖 <b>Помощь по боту</b>\n\n"
        "📌 <b>Доступные команды:</b>\n"
        "/start - Начать / Зарегистрироваться\n"
        "/profile - Показать профиль\n"
        # "/team - Сменить команду\n"
        "/top - Топ игроков\n"
        "/stats - Статистика команды\n"
        "/history - История действий\n"
        "/help - Показать эту справку\n\n"
        "🎮 <b>Основные функции:</b>\n"
        "• Регистрация с уникальным Player ID\n"
        "• Выбор команды из трех фракций\n"
        "• Открытие Mini App\n"
        "• Просмотр профиля и статистики\n"
        "• Топ игроков\n\n",
        parse_mode="HTML"
    )

# Обработчики сообщений

@dp.message(StateFilter(RegistrationStates.waiting_for_name))
async def process_name(message: types.Message, state: FSMContext):
    if len(message.text) > 30:
        await message.answer(
            "❌ Слишком длинное имя! Максимум 30 символов.\n"
            "Пожалуйста, введи имя короче:"
        )
        return
    
    if len(message.text) < 2:
        await message.answer(
            "❌ Слишком короткое имя! Минимум 2 символа.\n"
            "Пожалуйста, введи имя:"
        )
        return
    
    await state.update_data(name=message.text.strip())
    await state.set_state(RegistrationStates.waiting_for_team)
    
    _teams = ""
    for key, team in TEAMS.items():
        _teams += f"{key}: {team['name']}\n"
    
    await message.answer(
        f"👋 Отлично, <b>{message.text.strip()}</b>!\n\n"
        "Теперь выбери свою команду:\n\n"
        f"{_teams}",
        parse_mode="HTML",
        reply_markup=get_team_keyboard()
    )

@dp.message(F.text == "👤 Мой профиль")
async def profile_button(message: types.Message):
    await profile_command(message)

@dp.message(F.text == "📊 Статистика")
async def stats_button(message: types.Message):
    await stats_command(message)

@dp.message(F.text == "🏆 Топ игроков")
async def top_button(message: types.Message):
    await top_command(message)

# @dp.message(F.text == "🔄 Сменить команду")
# async def change_team_button(message: types.Message):
#     await team_command(message)

# @dp.message(F.text == "🚀 Открыть MiniApps")
# async def open_miniapp_button(message: types.Message):
#     user_id = message.from_user.id
#     user = await db.get_user(user_id)
    
#     if not user or not user.get('registered', False):
#         await message.answer(
#             "❌ Ты еще не зарегистрирован!\n"
#             "Напиши /start для регистрации"
#         )
#         return
    
#     await message.answer(
#         "🚀 <b>Открываю Mini App...</b>\n\n"
#         f"Игрок: {user['name']}\n"
#         f"ID: {format_player_id(user['player_id'])}\n"
#         f"Команда: {TEAMS[user['team']]['emoji']} {TEAMS[user['team']]['name']}",
#         parse_mode="HTML",
#         reply_markup=get_main_keyboard()
#     )
    
#     await db.add_history(user_id, "open_miniapp", "Открытие Mini App")

@dp.message(F.text == "📊 Общая статистика")
async def admin_stats(message: types.Message):
    # Проверка на админа (можно добавить список админов)
    admin_ids = [123456789]  # Замените на реальные ID
    if message.from_user.id not in admin_ids:
        await message.answer("❌ У вас нет прав администратора!")
        return
    
    all_users = await db.get_all_teams_stats()
    total_users = sum(s['total_players'] for s in all_users)
    
    text = "📊 <b>Общая статистика</b>\n\n"
    text += f"👥 Всего игроков: {total_users}\n\n"
    
    for team in TEAMS:
        stats = await db.get_team_stats(team)
        if stats:
            text += (
                f"{TEAMS[team]['emoji']} {TEAMS[team]['name']}:\n"
                f"   👥 {stats['total_players']} игроков\n"
                f"   🎯 {stats['total_games']} игр\n"
                f"   🏆 {stats['total_wins']} побед\n\n"
            )
    
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "👥 Список игроков")
async def admin_players(message: types.Message):
    admin_ids = [123456789]  # Замените на реальные ID
    if message.from_user.id not in admin_ids:
        await message.answer("❌ У вас нет прав администратора!")
        return
    
    # Получаем всех пользователей (нужно добавить метод в Database)
    # Здесь можно реализовать пагинацию
    
    await message.answer("👥 Функция в разработке")

@dp.message(F.text == "📈 Статистика команд")
async def admin_teams_stats(message: types.Message):
    admin_ids = [123456789]  # Замените на реальные ID
    if message.from_user.id not in admin_ids:
        await message.answer("❌ У вас нет прав администратора!")
        return
    
    stats = await db.get_all_teams_stats()
    
    if not stats:
        await message.answer("📊 Нет данных по командам")
        return
    
    text = "📈 <b>Статистика команд</b>\n\n"
    for stat in stats:
        team = stat['team']
        if team in TEAMS:
            text += (
                f"{TEAMS[team]['emoji']} {TEAMS[team]['name']}:\n"
                f"   👥 {stat['total_players']} игроков\n"
                f"   🎯 {stat['total_games']} игр\n"
                f"   🏆 {stat['total_wins']} побед\n"
                f"   📈 {round(stat['total_wins'] / stat['total_games'] * 100, 1) if stat['total_games'] > 0 else 0}% побед\n\n"
            )
    
    await message.answer(text, parse_mode="HTML")

@dp.message()
async def handle_other_messages(message: types.Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if user and user.get('registered', False):
        await message.answer(
            "Используй кнопки для навигации 👇",
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer(
            "❌ Ты еще не зарегистрирован!\n"
            "Напиши /start для регистрации"
        )

# Обработчики callback

@dp.callback_query(lambda c: c.data.startswith('team_'))
async def process_team_selection(callback: types.CallbackQuery, state: FSMContext):
    team_key = callback.data.replace('team_', '')
    
    if team_key not in TEAMS:
        await callback.answer("❌ Неверная команда!", show_alert=True)
        return
    
    user_id = callback.from_user.id
    current_state = await state.get_state()
    
    if current_state == RegistrationStates.waiting_for_team:
        # Новая регистрация
        data = await state.get_data()
        name = data.get('name', callback.from_user.first_name)
        
        # Генерируем player_id
        player_id = await generate_player_id(db)
        
        # Сохраняем пользователя
        success = await db.add_user(user_id, name, player_id, team_key)
        
        if not success:
            await callback.answer("❌ Ошибка при регистрации!", show_alert=True)
            return
        
        await state.clear()
        
        await callback.message.delete()
        await callback.message.answer(
            f"✅ <b>Регистрация завершена!</b>\n\n"
            f"👋 <b>Добро пожаловать, {name}!</b>\n"
            f"🎮 Player ID: {format_player_id(player_id)}\n"
            f"⚔️ Команда: {TEAMS[team_key]['emoji']} {TEAMS[team_key]['name']}\n\n"
            "Теперь ты можешь использовать бота.\n"
            "Нажми на кнопку ниже, чтобы открыть Mini App:",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
        
        await db.add_history(user_id, "register", 
            f"Регистрация: {name}, команда {TEAMS[team_key]['name']}")
        
        await callback.answer("✅ Регистрация завершена!")
        
    else:
        # Смена команды для существующего пользователя
        user = await db.get_user(user_id)
        
        if not user or not user.get('registered', False):
            await callback.answer("❌ Сначала зарегистрируйся!", show_alert=True)
            return
        
        if user['team'] == team_key:
            await callback.answer(
                f"❌ Ты уже в команде {TEAMS[team_key]['name']}!", 
                show_alert=True
            )
            return
        
        # Обновляем команду
        success = await db.update_user_team(user_id, team_key)
        
        if not success:
            await callback.answer("❌ Ошибка при смене команды!", show_alert=True)
            return
        
        await callback.message.delete()
        await callback.message.answer(
            f"✅ <b>Команда изменена!</b>\n\n"
            f"Было: {TEAMS[user['team']]['emoji']} {TEAMS[user['team']]['name']}\n"
            f"Стало: {TEAMS[team_key]['emoji']} {TEAMS[team_key]['name']}\n\n"
            "Твой профиль обновлен:",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
        
        await db.add_history(user_id, "change_team", 
            f"Смена команды: {user['team']} -> {team_key}")
        
        await callback.answer(f"Перешел в {TEAMS[team_key]['name']}!")

# Запуск бота
async def main():
    logger.info("🚀 Запуск бота...")
    
    # Инициализация базы данных
    await db.init_db()
    logger.info("База данных инициализирована")
    
    logger.info(f"Mini App URL: {MINI_APP_URL}")
    logger.info("Бот готов к работе!")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    # for key, team in TEAMS.items():
    #     print("add button -------->", f"team_{key}")
        