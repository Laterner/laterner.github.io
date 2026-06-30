# api/database.py
import sqlite3
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

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение пользователя по user_id"""
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                'SELECT * FROM users WHERE user_id = ?', 
                (user_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Получение всех пользователей"""
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                'SELECT * FROM users ORDER BY score DESC'
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def add_score(self, player_id: str, amount: int) -> bool:
        """Добавление очков игроку"""
        try:
            async with aiosqlite.connect(self.db_name) as db:
                cursor = await db.execute(
                    'UPDATE users SET score = score + ? WHERE player_id = ?',
                    (amount, player_id)
                )
                await db.commit()
                
                if cursor.rowcount > 0:
                    # Добавляем в историю
                    user = await self.get_user_by_player_id(player_id)
                    if user:
                        await db.execute('''
                            INSERT INTO user_history (user_id, action, details, timestamp)
                            VALUES (?, ?, ?, ?)
                        ''', (
                            user['user_id'],
                            "add_score",
                            f"Добавлено {amount} очков (через API)",
                            datetime.now().isoformat()
                        ))
                        await db.commit()
                    return True
                return False
        except Exception as e:
            print(f"Error adding score: {e}")
            return False

    async def update_user_name(self, player_id: str, new_name: str) -> bool:
        """Обновление имени пользователя"""
        try:
            async with aiosqlite.connect(self.db_name) as db:
                cursor = await db.execute(
                    'UPDATE users SET name = ? WHERE player_id = ?',
                    (new_name, player_id)
                )
                await db.commit()
                
                if cursor.rowcount > 0:
                    # Добавляем в историю
                    user = await self.get_user_by_player_id(player_id)
                    if user:
                        await db.execute('''
                            INSERT INTO user_history (user_id, action, details, timestamp)
                            VALUES (?, ?, ?, ?)
                        ''', (
                            user['user_id'],
                            "update_name",
                            f"Имя изменено на '{new_name}' (через API)",
                            datetime.now().isoformat()
                        ))
                        await db.commit()
                    return True
                return False
        except Exception as e:
            print(f"Error updating name: {e}")
            return False

    async def update_user_score(self, player_id: str, new_score: int) -> bool:
        """Обновление очков пользователя"""
        try:
            async with aiosqlite.connect(self.db_name) as db:
                cursor = await db.execute(
                    'UPDATE users SET score = ? WHERE player_id = ?',
                    (new_score, player_id)
                )
                await db.commit()
                
                if cursor.rowcount > 0:
                    # Добавляем в историю
                    user = await self.get_user_by_player_id(player_id)
                    if user:
                        await db.execute('''
                            INSERT INTO user_history (user_id, action, details, timestamp)
                            VALUES (?, ?, ?, ?)
                        ''', (
                            user['user_id'],
                            "update_score",
                            f"Очки установлены на {new_score} (через API)",
                            datetime.now().isoformat()
                        ))
                        await db.commit()
                    return True
                return False
        except Exception as e:
            print(f"Error updating score: {e}")
            return False

    async def search_users(self, query: str) -> List[Dict[str, Any]]:
        """Поиск пользователей по имени или player_id"""
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM users 
                WHERE name LIKE ? OR player_id LIKE ?
                ORDER BY score DESC
            ''', (f'%{query}%', f'%{query}%'))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_top_players(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение топ игроков"""
        async with aiosqlite.connect(self.db_name) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM users 
                ORDER BY score DESC 
                LIMIT ?
            ''', (limit,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

# Создаем экземпляр базы данных
db = Database()