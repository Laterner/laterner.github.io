# models.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class User:
    user_id: int
    name: str
    player_id: str
    team: str
    registered: bool = True
    registered_date: str = None
    score: int = 0
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    last_active: str = None

    def __post_init__(self):
        if self.registered_date is None:
            self.registered_date = datetime.now().isoformat()
        if self.last_active is None:
            self.last_active = datetime.now().isoformat()

@dataclass
class TeamStats:
    team: str
    total_players: int = 0
    total_wins: int = 0
    total_games: int = 0

@dataclass
class History:
    id: int
    user_id: int
    action: str
    details: str = ""
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()