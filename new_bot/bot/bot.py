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
    format_player_id,
    TeamStatsManager
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

team_stats = None

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле!")
if not MINI_APP_URL:
    raise ValueError("MINI_APP_URL не найден в .env файле!")


# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния регистрации
class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_team = State()

# Клавиатуры
def get_main_keyboard(user_id=""):
    """Главная клавиатура с кнопкой Mini App"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Мой профиль")],
            [KeyboardButton(text="📊 Статистика команды")],
            [KeyboardButton(text="🏆 Топ игроков")],
            [KeyboardButton(
                text="🚀 КВЕСТ",
                web_app=WebAppInfo(url=MINI_APP_URL+f"?user_id={user_id}")
            )]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_team_keyboard():
    """Клавиатура выбора команды"""

    builder = InlineKeyboardBuilder()

    
    for key, team in enumerate(team_stats.get_all()):
        print("----->>>>>", key, type(key), team, type(team))
        builder.button(
            text=team.team,
            callback_data=f"team_{team.id}"
        )
    # Распределить по строкам, например по 3 кнопки в ряд
    builder.adjust(3)
    keyboard = builder.as_markup()

        
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
            f"⚔️ Команда: {user['team_name']}\n"
            f"⭐ Очки: {user['score']}\n"
            f"🏆 Игр сыграно: {user['wins']}"
            "Используй кнопки ниже:",
            reply_markup=get_main_keyboard(message.from_user.id),
            parse_mode="HTML"
        )
        await db.add_history(user_id, "start", "Повторный запуск")
    else:
        # Начинаем регистрацию
        await state.set_state(RegistrationStates.waiting_for_name)
        await message.answer(
            "<b>Добро пожаловать!</b>\n\n"
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
    
    await message.answer(
        f"👤 <b>Твой профиль</b>\n\n"
        f"📛 Имя: {user['name']}\n"
        f"🎮 Player ID: {format_player_id(user['player_id'])}\n"
        f"⚔️ Команда: {user['team_name']}\n"
        f"⭐ Очки: {user['score']}\n"
        f"🏆 Игр сыграно: {user['games_played']}\n",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(message.from_user.id)
    )
    
    await db.add_history(user_id, "profile", "Просмотр профиля")

@dp.message(Command("team"))
async def team_command(message: types.Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user or not user.get('registered', False):
        await message.answer("❌ Сначала зарегистрируйся: /start")
        return
    
    for team in team_stats.get_team_names():
        _teams += f"{team}\n"
        
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
            f"   {team_stats.get_by_id(player['team']).team}\n"
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
            f"📊 <b>Статистика команды {user['team_name']}</b>\n\n"
            f"👥 Игроков: {team_stats['total_players']}\n"
            f"🎯 Игр сыграно: {team_stats['total_games']}\n"
            f"🏆 Очки команды: {team_stats['total_score']}\n"
        )
    else:
        text = f"📊 Статистика команды {user['team_name']} пока пуста"
    
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
        "/top - Топ игроков\n"
        "/stats - Статистика команды\n"
        "/history - История действий\n"
        "/help - Показать эту справку\n\n"
        "🎮 <b>Основные функции:</b>\n"
        "• Регистрация с уникальным Player ID\n"
        "• Выбор команды из трех фракций\n"
        "• Открытие Квеста\n"
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
    
    
    _teams = team_stats.get_team_names()
    print(_teams)
    await message.answer(
        f"👋 Отлично, <b>{message.text.strip()}</b>!\n\n"
        "Теперь выбери свою команду:\n\n"
        f"{'\n'.join(_teams)}",
        parse_mode="HTML",
        reply_markup=get_team_keyboard()
    )

@dp.message(F.text == "👤 Мой профиль")
async def profile_button(message: types.Message):
    await profile_command(message)

@dp.message(F.text == "📊 Статистика команды")
async def stats_button(message: types.Message):
    await stats_command(message)

@dp.message(F.text == "🏆 Топ игроков")
async def top_button(message: types.Message):
    await top_command(message)


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
    
    # TODO
    # for team in TEAMS:
    #     stats = await db.get_team_stats(team)
    #     if stats:
    #         text += (
    #             f"{TEAMS[team]['team']}:\n"
    #             f"   👥 {stats['total_players']} игроков\n"
    #             f"   🎯 {stats['total_games']} игр\n"
    #             f"   🏆 {stats['total_wins']} побед\n\n"
    #         )
    
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
        text += (
            f"{team}:\n"
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
            reply_markup=get_main_keyboard(message.from_user.id)
        )
    else:
        await message.answer(
            "❌ Ты еще не зарегистрирован!\n"
            "Напиши /start для регистрации"
        )

# Обработчики callback

@dp.callback_query(lambda c: c.data.startswith('team_'))
async def process_team_selection(callback: types.CallbackQuery, state: FSMContext):
    try:
        team_id = int(callback.data.replace('team_', ''))
    except:
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
        success = await db.add_user(user_id, name, player_id, team_id)
        
        if not success:
            await callback.answer("❌ Ошибка при регистрации!", show_alert=True)
            return
        
        await state.clear()
        
        await callback.message.delete()
        await callback.message.answer(
            f"✅ <b>Регистрация завершена!</b>\n\n"
            f"👋 <b>Добро пожаловать, {name}!</b>\n"
            f"🎮 Player ID: {format_player_id(player_id)}\n"
            f"⚔️ Команда: {team_stats.get_by_id(team_id).team}\n\n"
            "Теперь ты можешь использовать бота.\n"
            "Нажми на кнопку ниже, чтобы открыть Квест:",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(callback.message.from_user.id)
        )
        
        await db.add_history(user_id, "register", 
            f"Регистрация: {name}, команда {team_stats.get_by_id(team_id)}")
        
        await callback.answer("✅ Регистрация завершена!")
        
    # else:
    #     # Смена команды для существующего пользователя
    #     user = await db.get_user(user_id)
        
    #     if not user or not user.get('registered', False):
    #         await callback.answer("❌ Сначала зарегистрируйся!", show_alert=True)
    #         return
        
    #     if user['team'] == team_id:
    #         await callback.answer(
    #             f"❌ Ты уже в команде {team_stats.get_by_id(team_id)}!", 
    #             show_alert=True
    #         )
    #         return
        
    #     # Обновляем команду
    #     success = await db.update_user_team(user_id, team_id)
        
    #     if not success:
    #         await callback.answer("❌ Ошибка при смене команды!", show_alert=True)
    #         return
        
    #     await callback.message.delete()
    #     await callback.message.answer(
    #         f"✅ <b>Команда изменена!</b>\n\n"
    #         f"Было: {user['team_name']}\n"
    #         f"Стало: {team_stats.get_by_id(team_id)}\n\n"
    #         "Твой профиль обновлен:",
    #         parse_mode="HTML",
    #         reply_markup=get_main_keyboard(callback.message.from_user.id)
    #     )
        
    #     await db.add_history(user_id, "change_team", 
    #         f"Смена команды: {user['team']} -> {team_id}")
        
    #     await callback.answer(f"Перешел в {team_stats.get_by_id(team_id)}!")

# Запуск бота
async def main():
    global team_stats
    logger.info("🚀 Запуск бота...")
    
    # Инициализация базы данных
    pupu = await db.init_db()
    team_stats = TeamStatsManager(pupu)
    print('team_stats.get_all() =======>', team_stats.get_all())
    
    
    logger.info("База данных инициализирована")
    
    logger.info(f"Mini App URL: {MINI_APP_URL}")
    logger.info("Бот готов к работе!")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
        