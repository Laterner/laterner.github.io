# utils.py
import random
import string
import hashlib
from typing import Optional

TEAMS = [
    'Выгода', 
    'Реклама', 
    'Город', 
    'Покупки', 
    'Путешествия', 
    'Т-Авто', 
    'Общие платформы', 
    'Команда аналитики, роста и монетизации', 
    'HR'
]

async def generate_player_id(db) -> str:
    """Генерация уникального player_id из 5 символов"""
    chars = string.ascii_uppercase + string.digits
    while True:
        player_id = ''.join(random.choices(chars, k=5))
        # Проверяем уникальность в БД
        user = await db.get_user_by_player_id(player_id)
        if not user:
            return player_id


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