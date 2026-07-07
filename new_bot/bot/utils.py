# utils.py
import random
import string
import hashlib
from typing import Optional

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

async def generate_player_id(db) -> str:
    """Генерация уникального player_id из 5 символов"""
    chars = string.ascii_uppercase + string.digits
    while True:
        player_id = ''.join(random.choices(chars, k=5))
        # Проверяем уникальность в БД
        user = await db.get_user_by_player_id(player_id)
        if not user:
            return player_id

def get_team_emoji(team: str) -> str:
    """Получение эмодзи команды"""
    teams = {
        "red": "🔴",
        "blue": "🔵",
        "green": "🟢"
    }
    return teams.get(team, "⚪")

def get_team_name(team: str) -> str:
    """Получение названия команды"""
    teams = {
        "red": "Красные",
        "blue": "Синие",
        "green": "Зеленые"
    }
    return teams.get(team, "Неизвестно")

def get_team_description(team: str) -> str:
    """Получение описания команды"""
    descriptions = {
        "red": "🔥 Огненные воины - смелые и решительные",
        "blue": "💎 Стражи океана - мудрые и спокойные",
        "green": "🌿 Хранители леса - дружелюбные и сильные"
    }
    return descriptions.get(team, "❓ Неизвестная команда")

def format_player_id(player_id: str) -> str:
    """Форматирование player_id"""
    return f"<code>{player_id}</code>"

def hash_user_id(user_id: int) -> str:
    """Хэширование user_id для безопасности"""
    return hashlib.sha256(str(user_id).encode()).hexdigest()[:8]