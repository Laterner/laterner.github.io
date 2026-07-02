import os
import json
from datetime import datetime
from typing import Optional, Dict, List, Any
import asyncpg
from asyncpg import Pool, Record

# Конфигурация из переменных окружения
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "postgres"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "user_db"),
    "user": os.getenv("DB_USER", "admin"),
    "password": os.getenv("DB_PASSWORD", ""),
}

class Database:
    def __init__(self):
        self.pool: Optional[Pool] = None

    async def init_pool(self):
        """Создание пула соединений с PostgreSQL"""
        self.pool = await asyncpg.create_pool(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            database=DB_CONFIG["database"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            min_size=1,
            max_size=10,
        )

    async def init_db(self):
        """Инициализация базы данных (создание таблиц)"""
        async with self.pool.acquire() as conn:
            # Таблица пользователей
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    name TEXT NOT NULL,
                    player_id TEXT UNIQUE NOT NULL,
                    team TEXT NOT NULL,
                    registered BOOLEAN DEFAULT TRUE,
                    registered_date TEXT NOT NULL,
                    score INTEGER DEFAULT 0,
                    games_played INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    last_active TEXT
                )
            ''')
            
            # Таблица для статистики по командам
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS team_stats (
                    team TEXT PRIMARY KEY,
                    total_players INTEGER DEFAULT 0,
                    total_wins INTEGER DEFAULT 0,
                    total_games INTEGER DEFAULT 0
                )
            ''')
            
            # Таблица для истории действий
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS user_history (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                    action TEXT,
                    details TEXT,
                    timestamp TEXT
                )
            ''')

    async def add_user(self, user_id: int, name: str, player_id: str, team: str) -> bool:
        """Добавление нового пользователя"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO users (
                        user_id, name, player_id, team, registered,
                        registered_date, score, games_played, wins, losses, last_active
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ''',
                    user_id,
                    name,
                    player_id,
                    team,
                    True,
                    datetime.now().isoformat(),
                    0,
                    0,
                    0,
                    0,
                    datetime.now().isoformat()
                )
                
                # Обновляем статистику команды
                await self.update_team_stats(team, add_player=True)
                
                return True
        except asyncpg.IntegrityConstraintViolationError:
            return False

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение данных пользователя"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT * FROM users WHERE user_id = $1',
                user_id
            )
            return dict(row) if row else None

    async def get_user_by_player_id(self, player_id: str) -> Optional[Dict[str, Any]]:
        """Получение пользователя по player_id"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT * FROM users WHERE player_id = $1',
                player_id
            )
            return dict(row) if row else None

    async def update_user_team(self, user_id: int, new_team: str) -> bool:
        """Обновление команды пользователя"""
        try:
            # Получаем старую команду
            user = await self.get_user(user_id)
            if not user:
                return False
            
            old_team = user['team']
            
            async with self.pool.acquire() as conn:
                await conn.execute(
                    'UPDATE users SET team = $1, last_active = $2 WHERE user_id = $3',
                    new_team, datetime.now().isoformat(), user_id
                )
                
                # Обновляем статистику команд
                await self.update_team_stats(old_team, add_player=False)
                await self.update_team_stats(new_team, add_player=True)
                
                return True
        except Exception as e:
            print(f"Error updating team: {e}")
            return False

    async def update_user_stats(self, user_id: int, won: bool = False):
        """Обновление статистики пользователя"""
        async with self.pool.acquire() as conn:
            if won:
                await conn.execute('''
                    UPDATE users
                    SET games_played = games_played + 1,
                        wins = wins + 1,
                        last_active = $1
                    WHERE user_id = $2
                ''', datetime.now().isoformat(), user_id)
                
                # Обновляем статистику команды
                user = await self.get_user(user_id)
                if user:
                    await conn.execute('''
                        UPDATE team_stats
                        SET total_games = total_games + 1,
                            total_wins = total_wins + 1
                        WHERE team = $1
                    ''', user['team'])
            else:
                await conn.execute('''
                    UPDATE users
                    SET games_played = games_played + 1,
                        losses = losses + 1,
                        last_active = $1
                    WHERE user_id = $2
                ''', datetime.now().isoformat(), user_id)
                
                # Обновляем статистику команды
                user = await self.get_user(user_id)
                if user:
                    await conn.execute('''
                        UPDATE team_stats
                        SET total_games = total_games + 1
                        WHERE team = $1
                    ''', user['team'])

    async def update_team_stats(self, team: str, add_player: bool = True):
        """Обновление статистики команды"""
        async with self.pool.acquire() as conn:
            if add_player:
                await conn.execute('''
                    INSERT INTO team_stats (team, total_players, total_wins, total_games)
                    VALUES ($1, 1, 0, 0)
                    ON CONFLICT (team) DO UPDATE SET
                        total_players = team_stats.total_players + 1
                ''', team)
            else:
                await conn.execute('''
                    UPDATE team_stats
                    SET total_players = total_players - 1
                    WHERE team = $1 AND total_players > 0
                ''', team)

    async def get_team_stats(self, team: str) -> Optional[Dict[str, Any]]:
        """Получение статистики команды"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT * FROM team_stats WHERE team = $1',
                team
            )
            return dict(row) if row else None

    async def get_all_teams_stats(self) -> List[Dict[str, Any]]:
        """Получение статистики всех команд"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT * FROM team_stats')
            return [dict(row) for row in rows]

    async def add_history(self, user_id: int, action: str, details: str = ""):
        """Добавление записи в историю"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO user_history (user_id, action, details, timestamp)
                VALUES ($1, $2, $3, $4)
            ''', user_id, action, details, datetime.now().isoformat())

    async def get_user_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение истории пользователя"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM user_history
                WHERE user_id = $1
                ORDER BY timestamp DESC
                LIMIT $2
            ''', user_id, limit)
            return [dict(row) for row in rows]

    async def get_top_players(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение топ игроков по очкам"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT user_id, name, player_id, team, score, wins, games_played
                FROM users
                ORDER BY score DESC
                LIMIT $1
            ''', limit)
            return [dict(row) for row in rows]

    async def delete_user(self, user_id: int) -> bool:
        """Удаление пользователя"""
        try:
            user = await self.get_user(user_id)
            if not user:
                return False
            
            async with self.pool.acquire() as conn:
                await conn.execute('DELETE FROM users WHERE user_id = $1', user_id)
                
                # Обновляем статистику команды
                await self.update_team_stats(user['team'], add_player=False)
                
                return True
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False

    async def user_exists(self, user_id: int) -> bool:
        """Проверка существования пользователя"""
        user = await self.get_user(user_id)
        return user is not None

    async def is_registered(self, user_id: int) -> bool:
        """Проверка регистрации пользователя"""
        user = await self.get_user(user_id)
        return user is not None and user.get('registered', False) is True

    async def close(self):
        """Закрытие пула соединений"""
        if self.pool:
            await self.pool.close()

# Создаем экземпляр базы данных
db = Database()