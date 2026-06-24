# database.py
import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, List, Any
import aiosqlite

DB_NAME = "users.db"

class Database:
    def __init__(self, db_name: str = DB_NAME):
        self.db_name = db_name

    async def init_db(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_name) as db:
            # Таблица пользователей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    player_id TEXT UNIQUE NOT NULL,
                    team TEXT NOT NULL,
                    registered BOOLEAN DEFAULT 1,
                    registered_date TEXT NOT NULL,
                    score INTEGER DEFAULT 0,
                    games_played INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    last_active TEXT
                )
            ''')
            
            # Таблица для статистики по командам
            await db.execute('''
                CREATE TABLE IF NOT EXISTS team_stats (
                    team TEXT PRIMARY KEY,
                    total_players INTEGER DEFAULT 0,
                    total_wins INTEGER DEFAULT 0,
                    total_games INTEGER DEFAULT 0
                )
            ''')
            
            # Таблица для истории действий
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT,
                    details TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            await db.commit()

    async def add_user(self, user_id: int, name: str, player_id: str, team: str) -> bool:
        """Добавление нового пользователя"""
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute('''
                    INSERT INTO users (
                        user_id, name, player_id, team, registered, 
                        registered_date, score, games_played, wins, losses, last_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, 
                    name, 
                    player_id, 
                    team, 
                    1,
                    datetime.now().isoformat(),
                    0,
                    0,
                    0,
                    0,
                    datetime.now().isoformat()
                ))
                await db.commit()
                
                # Обновляем статистику команды
                await self.update_team_stats(team, add_player=True)
                
                return True
        except sqlite3.IntegrityError:
            return False

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение данных пользователя"""
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                'SELECT * FROM users WHERE user_id = ?', 
                (user_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_user_by_player_id(self, player_id: str) -> Optional[Dict[str, Any]]:
        """Получение пользователя по player_id"""
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                'SELECT * FROM users WHERE player_id = ?', 
                (player_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_user_team(self, user_id: int, new_team: str) -> bool:
        """Обновление команды пользователя"""
        try:
            # Получаем старую команду
            user = await self.get_user(user_id)
            if not user:
                return False
            
            old_team = user['team']
            
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute(
                    'UPDATE users SET team = ?, last_active = ? WHERE user_id = ?',
                    (new_team, datetime.now().isoformat(), user_id)
                )
                await db.commit()
                
                # Обновляем статистику команд
                await self.update_team_stats(old_team, add_player=False)
                await self.update_team_stats(new_team, add_player=True)
                
                return True
        except Exception as e:
            print(f"Error updating team: {e}")
            return False

    async def update_user_stats(self, user_id: int, won: bool = False):
        """Обновление статистики пользователя"""
        async with aiosqlite.connect(self.db_name) as db:
            if won:
                await db.execute('''
                    UPDATE users 
                    SET games_played = games_played + 1,
                        wins = wins + 1,
                        last_active = ?
                    WHERE user_id = ?
                ''', (datetime.now().isoformat(), user_id))
                
                # Обновляем статистику команды
                user = await self.get_user(user_id)
                if user:
                    await db.execute('''
                        UPDATE team_stats 
                        SET total_games = total_games + 1,
                            total_wins = total_wins + 1
                        WHERE team = ?
                    ''', (user['team'],))
            else:
                await db.execute('''
                    UPDATE users 
                    SET games_played = games_played + 1,
                        losses = losses + 1,
                        last_active = ?
                    WHERE user_id = ?
                ''', (datetime.now().isoformat(), user_id))
                
                # Обновляем статистику команды
                user = await self.get_user(user_id)
                if user:
                    await db.execute('''
                        UPDATE team_stats 
                        SET total_games = total_games + 1
                        WHERE team = ?
                    ''', (user['team'],))
            
            await db.commit()

    async def update_team_stats(self, team: str, add_player: bool = True):
        """Обновление статистики команды"""
        async with aiosqlite.connect(self.db_name) as db:
            if add_player:
                await db.execute('''
                    INSERT INTO team_stats (team, total_players, total_wins, total_games)
                    VALUES (?, 1, 0, 0)
                    ON CONFLICT(team) DO UPDATE SET
                        total_players = total_players + 1
                ''', (team,))
            else:
                await db.execute('''
                    UPDATE team_stats 
                    SET total_players = total_players - 1
                    WHERE team = ? AND total_players > 0
                ''', (team,))
            await db.commit()

    async def get_team_stats(self, team: str) -> Optional[Dict[str, Any]]:
        """Получение статистики команды"""
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                'SELECT * FROM team_stats WHERE team = ?',
                (team,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_all_teams_stats(self) -> List[Dict[str, Any]]:
        """Получение статистики всех команд"""
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('SELECT * FROM team_stats')
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def add_history(self, user_id: int, action: str, details: str = ""):
        """Добавление записи в историю"""
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute('''
                INSERT INTO user_history (user_id, action, details, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (user_id, action, details, datetime.now().isoformat()))
            await db.commit()

    async def get_user_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение истории пользователя"""
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM user_history 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (user_id, limit))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_top_players(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение топ игроков по очкам"""
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT user_id, name, player_id, team, score, wins, games_played
                FROM users 
                ORDER BY score DESC 
                LIMIT ?
            ''', (limit,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def delete_user(self, user_id: int) -> bool:
        """Удаление пользователя"""
        try:
            user = await self.get_user(user_id)
            if not user:
                return False
            
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
                await db.commit()
                
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
        return user is not None and user.get('registered', False) == 1

# Создаем экземпляр базы данных
db = Database()