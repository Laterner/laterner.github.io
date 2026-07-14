from pydantic import BaseModel
import hmac
import hashlib
import time
import os
from urllib.parse import parse_qsl
import json

from dataclasses import dataclass
from typing import Optional, List, Dict
from collections import defaultdict

BOT_TOKEN = os.getenv("BOT_TOKEN")

class InitData(BaseModel):
    initData: str

def eprint(text, *args):
    print(f"\033[31m{text}\033[0m", " ".join(args))
    
def validate_init_data(init_data: str):
    data = dict(parse_qsl(init_data))

    # print("TG DATA GET :::::::::::>>", data)
    if "hash" not in data:
        return None

    received_hash = data.pop("hash")

    # 1. Сортируем данные
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(data.items())
    )
    
    # 2. secret key
    secret_key = hmac.new(
        b"WebAppData",
        BOT_TOKEN.encode(),
        hashlib.sha256
    ).digest()
    
    # 3. hash
    computed_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    if computed_hash != received_hash:
        eprint("if computed_hash != received_hash", computed_hash, received_hash)
        # return None

    # 4. проверка времени (24h)
    auth_date = int(data.get("auth_date", 0))
    if time.time() - auth_date > 86400:
        eprint("if time.time() - auth_date > 86400")
    #     return None
    
    data['user'] =  json.loads(data['user'])
    return data

QUIZES = [
    {'question': '16 ночей в пятизвёздочном отеле Греции принесли путешественникам кэшбэка на сумму, способную вызвать те самые «слёзы зависти». А теперь почти как у Дудя: "Сколько они кэшбэкнули?")', 'secret_code': 'CACTD', 'answers': ['А) 127 тыс. рублей', 'Б) 218 тыс. рублей', 'В) 327 тыс. рублей', ' Г) 516 тыс. рублей'], 'ans': 3}, 
    {'question': 'Какая локация показала рекордный рост заказов — сразу на 101% в мае по сравнению с апрелем, обогнав Абу-Даби, Киото и Бали?', 'secret_code': 'DSFGS', 'answers': ['А) Абу-Даби', 'Б) Киото', 'В) Бали', 'Г) Ейск'], 'ans': 4}, 
    {'question': 'Сколько часов провёл в пути «Уставший пассажир», совершив рекордную поездку по маршруту Бали — Амстердам — Бали с пересадками в рамках одного заказа?', 'secret_code': 'EGLPZ', 'answers': ['А) 41 час', 'Б) 48 часов', 'В) 59 часов', 'Г) 72 часа'], 'ans': 3}, 
    {'question': 'Сколько заплатили за 8 ночей на Мальдивах двое взрослых, доказав, что «бабки не проблема»?', 'secret_code': 'FXZJN', 'answers': ['А) 1,2 млн рублей', 'Б) 1,8 млн рублей', 'В) 2,5 млн рублей', 'Г) 3,7 млн рублей'], 'ans': 3}, 
    {'question': 'Сколько ночей за 2025 год «Почётный резидент» провёл в одном и том же отеле — SHELTERZ Три вокзала?', 'secret_code': 'KBCFL', 'answers': ['А) 189 ночей', 'Б) 277 ночей', 'В) 224 ночи', 'Г) 315 ночей'], 'ans': 2}, 
    {'question': 'Сколько билетов на «Чебурашку 2» купили в Афише в новогодние каникулы — столько, что всем зрителям не хватило бы мест даже на крупнейшем стадионе мира?', 'secret_code': 'MLKGL', 'answers': ['А) 114 000 билетов', 'Б) 132 116 билетов', 'В) 151 240 билетов', 'Г) 207 500 билетов'], 'ans': 2}, 
    {'question': 'Сколько миллионов литров топлива каждый месяц проходит через сервис — этого хватило бы, чтобы примерно 17 тысяч раз объехать Землю?', 'secret_code': 'SQVEP', 'answers': ['А) 40 млн литров', 'Б) 55 млн литров', 'В) 68,7 млн литров', ' Г)77 млн литров'], 'ans': 2}
]


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


@dataclass
class TeamStats:
    """Статистика команды"""
    id: int
    name: str
    total_players: int = 0
    total_wins: int = 0
    total_games: int = 0
    total_score: int = 0
    
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
        self._teams_by_name = {item['name']: TeamStats(**item) for item in data}
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
            team.name 
            for team in sorted(self._teams_by_id.values(), key=lambda x: x.id)
        ]
    
    def get_team_names_with_ids(self) -> List[Dict[str, int]]:
        """Получить список словарей с id и названиями команд"""
        return [
            {'id': team.id, 'name': team.name}
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
                'name': t.name,
                'total_players': t.total_players,
                'total_wins': t.total_wins,
                'total_games': t.total_games
            }
            for t in sorted(self._teams_by_id.values(), key=lambda x: x.id)
        ]


# if __name__ == "__main__":
#     ars = [
#         ["А) 127 тыс. рублей", "Б) 218 тыс. рублей", "В) 327 тыс. рублей", " Г) 516 тыс. рублей"],
#         ["А) Абу-Даби", "Б) Киото", "В) Бали", "Г) Ейск"],
#         ["А) 41 час", "Б) 48 часов", "В) 59 часов", "Г) 72 часа"],
#         ["А) 1,2 млн рублей", "Б) 1,8 млн рублей", "В) 2,5 млн рублей", "Г) 3,7 млн рублей"],
#         ["А) 189 ночей", "Б) 277 ночей", "В) 224 ночи", "Г) 315 ночей"],
#         ["А) 114 000 билетов", "Б) 132 116 билетов", "В) 151 240 билетов", "Г) 207 500 билетов"],
#         ["А) 40 млн литров", "Б) 55 млн литров", "В) 68,7 млн литров", " Г)77 млн литров"],
#     ]
#     for i, el in enumerate(ars):
#         QUIZES[i]['answers'] = el
    