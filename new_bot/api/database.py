from asyncpg import Pool, create_pool
from datetime import datetime
from typing import Optional, Dict, List, Any
import os

# Конфигурация из переменных окружения
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "postgres"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "user_db"),
    "user": os.getenv("DB_USER", "admin"),
    "password": os.getenv("DB_PASSWORD", ""),
}

class Database:
    def __init__(self, config: Dict[str, str] = None):
        self.config = config or DB_CONFIG
        self.pool: Optional[Pool] = None
        # print("DB_CONFIG ::::::::::::>", DB_CONFIG)

    async def init_pool(self):
        """Инициализация пула соединений"""
        if self.pool is None:
            self.pool = await create_pool(
                host=self.config["host"],
                port=self.config["port"],
                database=self.config["database"],
                user=self.config["user"],
                password=self.config["password"],
                min_size=1,
                max_size=10,
            )
        return self.pool

    async def init_db(self):
        """Инициализация базы данных"""
        if self.pool is None:
            await self.init_pool()
            
        async with self.pool.acquire() as conn:
            # Таблица пользователей
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    name TEXT NOT NULL,
                    player_id TEXT UNIQUE NOT NULL,
                    team TEXT NOT NULL,
                    registered BOOLEAN DEFAULT TRUE,
                    registered_date TIMESTAMP NOT NULL,
                    score INTEGER DEFAULT 0,
                    games_played INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    last_active TIMESTAMP
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
                    user_id BIGINT,
                    action TEXT,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                )
            ''')
            
            # Индексы для оптимизации
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_users_player_id ON users(player_id);
                CREATE INDEX IF NOT EXISTS idx_users_score ON users(score DESC);
                CREATE INDEX IF NOT EXISTS idx_user_history_user_id ON user_history(user_id);
            ''')

    async def get_user_by_player_id(self, player_id: str) -> Optional[Dict[str, Any]]:
        """Получение пользователя по player_id"""
        if self.pool is None:
            await self.init_pool()
            
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT * FROM users WHERE player_id = $1',
                player_id
            )
            return dict(row) if row else None

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение пользователя по user_id"""
        if self.pool is None:
            await self.init_pool()
            
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT * FROM users WHERE user_id = $1',
                user_id
            )
            return dict(row) if row else None

    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Получение всех пользователей"""
        if self.pool is None:
            await self.init_pool()
            
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                'SELECT * FROM users ORDER BY score DESC'
            )
            return [dict(row) for row in rows]

    async def add_score(self, player_id: str, amount: int) -> bool:
        """Добавление очков игроку"""
        try:
            if self.pool is None:
                await self.init_pool()
                
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    result = await conn.execute(
                        'UPDATE users SET score = score + $1 WHERE player_id = $2',
                        amount, player_id
                    )
                    
                    if result != "UPDATE 0":
                        # Добавляем в историю
                        user = await self.get_user_by_player_id(player_id)
                        if user:
                            await conn.execute('''
                                INSERT INTO user_history (user_id, action, details)
                                VALUES ($1, $2, $3)
                            ''', (
                                user['user_id'],
                                "add_score",
                                f"Добавлено {amount} очков (через API)"
                            ))
                        return True
                return False
        except Exception as e:
            print(f"Error adding score: {e}")
            return False

    async def update_user_name(self, player_id: str, new_name: str) -> bool:
        """Обновление имени пользователя"""
        try:
            if self.pool is None:
                await self.init_pool()
                
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    result = await conn.execute(
                        'UPDATE users SET name = $1 WHERE player_id = $2',
                        new_name, player_id
                    )
                    
                    if result != "UPDATE 0":
                        user = await self.get_user_by_player_id(player_id)
                        if user:
                            await conn.execute('''
                                INSERT INTO user_history (user_id, action, details)
                                VALUES ($1, $2, $3)
                            ''', (
                                user['user_id'],
                                "update_name",
                                f"Имя изменено на '{new_name}' (через API)"
                            ))
                        return True
                return False
        except Exception as e:
            print(f"Error updating name: {e}")
            return False

    async def update_user_score(self, player_id: str, new_score: int) -> bool:
        """Обновление очков пользователя"""
        try:
            if self.pool is None:
                await self.init_pool()
                
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    result = await conn.execute(
                        'UPDATE users SET score = $1 WHERE player_id = $2',
                        new_score, player_id
                    )
                    
                    if result != "UPDATE 0":
                        user = await self.get_user_by_player_id(player_id)
                        if user:
                            await conn.execute('''
                                INSERT INTO user_history (user_id, action, details)
                                VALUES ($1, $2, $3)
                            ''', (
                                user['user_id'],
                                "update_score",
                                f"Очки установлены на {new_score} (через API)"
                            ))
                        return True
                return False
        except Exception as e:
            print(f"Error updating score: {e}")
            return False

    async def search_users(self, query: str) -> List[Dict[str, Any]]:
        """Поиск пользователей по имени или player_id"""
        if self.pool is None:
            await self.init_pool()
            
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM users 
                WHERE name ILIKE $1 OR player_id ILIKE $1
                ORDER BY score DESC
            ''', (f'%{query}%',))
            return [dict(row) for row in rows]

    async def get_top_players(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение топ игроков"""
        if self.pool is None:
            await self.init_pool()
            
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM users 
                ORDER BY score DESC 
                LIMIT $1
            ''', limit)
            return [dict(row) for row in rows]

    async def close(self):
        """Закрытие пула соединений"""
        if self.pool:
            await self.pool.close()
            self.pool = None

# Создаем экземпляр базы данных
db = Database()