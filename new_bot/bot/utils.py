# utils.py
import random
import string
import hashlib
from dataclasses import dataclass
from typing import Optional, List, Dict
from collections import defaultdict


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

def format_player_id(player_id: str) -> str:
    """Форматирование player_id"""
    return f"<code>{player_id}</code>"

def hash_user_id(user_id: int) -> str:
    """Хэширование user_id для безопасности"""
    return hashlib.sha256(str(user_id).encode()).hexdigest()[:8]


@dataclass
class TeamStats:
    """Статистика команды"""
    id: int
    team: str
    total_players: int = 0
    total_wins: int = 0
    total_games: int = 0
    
    @property
    def win_rate(self) -> float:
        """Процент побед"""
        if self.total_games == 0:
            return 0.0
        return round((self.total_wins / self.total_games) * 100, 2)


class TeamStatsManager:
    """Менеджер для работы со статистикой команд"""
    
    def __init__(self, data: List[Dict]):
        self._data = data
        self._teams_by_id = {item['id']: TeamStats(**item) for item in data}
        self._teams_by_name = {item['team']: TeamStats(**item) for item in data}
        self._update_stats()
    
    def _update_stats(self):
        """Обновление статистики (пересчет)"""
        self.total_players = sum(t.total_players for t in self._teams_by_id.values())
        self.total_wins = sum(t.total_wins for t in self._teams_by_id.values())
        self.total_games = sum(t.total_games for t in self._teams_by_id.values())
        self.active_teams = [t for t in self._teams_by_id.values() if t.total_players > 0]
    
    def get_by_id(self, team_id: int) -> Optional[TeamStats]:
        """Получить команду по ID"""
        return self._teams_by_id.get(team_id)
    
    def get_by_name(self, name: str) -> Optional[TeamStats]:
        """Получить команду по названию"""
        return self._teams_by_name.get(name)
    
    def get_all(self) -> List[TeamStats]:
        """Получить все команды"""
        return list(self._teams_by_id.values())
    
    def get_team_names(self) -> List[str]:
        """Получить список названий команд, отсортированных по id"""
        # Получаем все команды, сортируем по id и извлекаем названия
        return [
            team.team 
            for team in sorted(self._teams_by_id.values(), key=lambda x: x.id)
        ]
    
    def get_team_names_with_ids(self) -> List[Dict[str, int]]:
        """Получить список словарей с id и названиями команд"""
        return [
            {'id': team.id, 'name': team.team}
            for team in sorted(self._teams_by_id.values(), key=lambda x: x.id)
        ]
    
    def get_top_teams(self, limit: int = 3, by: str = 'total_wins') -> List[TeamStats]:
        """Получить топ команд по определенному критерию"""
        return sorted(
            self._teams_by_id.values(),
            key=lambda x: getattr(x, by, 0),
            reverse=True
        )[:limit]
    
    def to_dict(self) -> List[Dict]:
        """Вернуть данные в исходном формате"""
        return [
            {
                'id': t.id,
                'team': t.team,
                'total_players': t.total_players,
                'total_wins': t.total_wins,
                'total_games': t.total_games
            }
            for t in sorted(self._teams_by_id.values(), key=lambda x: x.id)
        ]


# # Использование
# data = [
#     {'id': 1, 'team': 'Выгода', 'total_players': 0, 'total_wins': 0, 'total_games': 0},
#     {'id': 2, 'team': 'Реклама', 'total_players': 0, 'total_wins': 0, 'total_games': 0},
#     # ... остальные команды
# ]

# stats = TeamStatsManager(data)

# # Быстрый доступ
# team = stats.get_by_id(1)
# print(f"{team.team}: {team.total_players} игроков")

# # Добавление игры
# stats.add_game(1, players=5, wins=3)

# # Получение топа
# top = stats.get_top_teams(limit=3, by='total_wins')
# for t in top:
#     print(f"{t.team} - {t.total_wins} побед")

# # Сводка
# summary = stats.get_summary()