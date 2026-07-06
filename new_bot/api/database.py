# database.py
import os
from datetime import datetime
from typing import Optional, Dict, List, Any

from sqlalchemy import select, func, or_, desc
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.exc import IntegrityError

from models import User, UserHistory, Base

# Конфигурация из переменных окружения
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "postgres"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "user_db"),
    "user": os.getenv("DB_USER", "admin"),
    "password": os.getenv("DB_PASSWORD", ""),
}

# Формирование URL для подключения к PostgreSQL
DATABASE_URL = (
    f"postgresql+asyncpg://"
    f"{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}"
    f"/{DB_CONFIG['database']}"
)

# Создание асинхронного движка
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Для отладки можно установить True
    pool_pre_ping=True,  # Проверка соединения перед использованием
    pool_size=10,  # Размер пула соединений
    max_overflow=20,  # Максимальное количество дополнительных соединений
)

# Создание фабрики сессий
SessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Database:
    """Класс для работы с базой данных с использованием SQLAlchemy 2.0 Async"""

    def __init__(self, config: Dict[str, str] = None):
        self.config = config or DB_CONFIG

    async def init_db(self):
        """Инициализация базы данных (создание таблиц)"""
        async with engine.begin() as conn:
            # Создаем все таблицы
            await conn.run_sync(Base.metadata.create_all)
            
            # Создаем индексы для оптимизации (если их нет)
            # await self._create_indexes()

    async def _create_indexes(self):
        """Создание индексов для оптимизации запросов"""
        async with engine.begin() as conn:
            # Индексы создаются через сырой SQL, так как SQLAlchemy не всегда
            # автоматически создает индексы, определенные в моделях
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_users_player_id ON users(player_id)
            ''')
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_users_score ON users(score DESC)
            ''')
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_history_user_id ON user_history(user_id)
            ''')

    async def get_user_by_player_id(self, player_id: str) -> Optional[Dict[str, Any]]:
        """Получение пользователя по player_id"""
        async with SessionLocal() as session:
            result = await session.execute(
                select(User).where(User.player_id == player_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                return {
                    'user_id': user.user_id,
                    'name': user.name,
                    'player_id': user.player_id,
                    'team': user.team,
                    'registered': user.registered,
                    'registered_date': user.registered_date,
                    'score': user.score,
                    'games_played': user.games_played,
                    'wins': user.wins,
                    'losses': user.losses,
                    'last_active': user.last_active,
                }
            return None

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение пользователя по user_id"""
        async with SessionLocal() as session:
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                return {
                    'user_id': user.user_id,
                    'name': user.name,
                    'player_id': user.player_id,
                    'team': user.team,
                    'registered': user.registered,
                    'registered_date': user.registered_date,
                    'score': user.score,
                    'games_played': user.games_played,
                    'wins': user.wins,
                    'losses': user.losses,
                    'last_active': user.last_active,
                }
            return None

    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Получение всех пользователей"""
        async with SessionLocal() as session:
            result = await session.execute(
                select(User).order_by(desc(User.score))
            )
            users = result.scalars().all()
            
            return [
                {
                    'user_id': u.user_id,
                    'name': u.name,
                    'player_id': u.player_id,
                    'team': u.team,
                    'registered': u.registered,
                    'registered_date': u.registered_date,
                    'score': u.score,
                    'games_played': u.games_played,
                    'wins': u.wins,
                    'losses': u.losses,
                    'last_active': u.last_active,
                }
                for u in users
            ]

    async def add_score(self, player_id: str, amount: int) -> bool:
        """Добавление очков игроку"""
        async with SessionLocal() as session:
            try:
                # Получаем пользователя
                result = await session.execute(
                    select(User).where(User.player_id == player_id)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    return False
                
                # Обновляем очки
                user.score += amount
                user.games_played += 1
                user.wins += 1
                user.last_active = datetime.utcnow()
                
                # Добавляем запись в историю
                history = UserHistory(
                    user_id=user.user_id,
                    action="add_score",
                    details=f"Добавлено {amount} очков (через API)"
                )
                session.add(history)
                
                await session.commit()
                return True
                
            except Exception as e:
                await session.rollback()
                print(f"Error adding score: {e}")
                return False

    async def update_user_name(self, player_id: str, new_name: str) -> bool:
        """Обновление имени пользователя"""
        async with SessionLocal() as session:
            try:
                # Получаем пользователя
                result = await session.execute(
                    select(User).where(User.player_id == player_id)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    return False
                
                # Обновляем имя
                old_name = user.name
                user.name = new_name
                user.last_active = datetime.utcnow()
                
                # Добавляем запись в историю
                history = UserHistory(
                    user_id=user.user_id,
                    action="update_name",
                    details=f"Имя изменено с '{old_name}' на '{new_name}' (через API)"
                )
                session.add(history)
                
                await session.commit()
                return True
                
            except Exception as e:
                await session.rollback()
                print(f"Error updating name: {e}")
                return False

    async def update_user_score(self, player_id: str, new_score: int) -> bool:
        """Обновление очков пользователя"""
        async with SessionLocal() as session:
            try:
                # Получаем пользователя
                result = await session.execute(
                    select(User).where(User.player_id == player_id)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    return False
                
                # Обновляем очки
                old_score = user.score
                user.score = new_score
                user.last_active = datetime.utcnow()
                
                # Добавляем запись в историю
                history = UserHistory(
                    user_id=user.user_id,
                    action="update_score",
                    details=f"Очки изменены с {old_score} на {new_score} (через API)"
                )
                session.add(history)
                
                await session.commit()
                return True
                
            except Exception as e:
                await session.rollback()
                print(f"Error updating score: {e}")
                return False

    async def search_users(self, query: str) -> List[Dict[str, Any]]:
        """Поиск пользователей по имени или player_id"""
        async with SessionLocal() as session:
            # Используем ILIKE для регистронезависимого поиска
            search_pattern = f"%{query}%"
            result = await session.execute(
                select(User)
                .where(
                    or_(
                        User.name.ilike(search_pattern),
                        User.player_id.ilike(search_pattern)
                    )
                )
                .order_by(desc(User.score))
            )
            users = result.scalars().all()
            
            return [
                {
                    'user_id': u.user_id,
                    'name': u.name,
                    'player_id': u.player_id,
                    'team': u.team,
                    'registered': u.registered,
                    'registered_date': u.registered_date,
                    'score': u.score,
                    'games_played': u.games_played,
                    'wins': u.wins,
                    'losses': u.losses,
                    'last_active': u.last_active,
                }
                for u in users
            ]

    async def get_top_players(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение топ игроков"""
        async with SessionLocal() as session:
            result = await session.execute(
                select(User)
                .where(User.registered == True)
                .order_by(desc(User.score))
                .limit(limit)
            )
            users = result.scalars().all()
            
            return [
                {
                    'user_id': u.user_id,
                    'name': u.name,
                    'player_id': u.player_id,
                    'team': u.team,
                    'registered': u.registered,
                    'registered_date': u.registered_date,
                    'score': u.score,
                    'games_played': u.games_played,
                    'wins': u.wins,
                    'losses': u.losses,
                    'last_active': u.last_active,
                }
                for u in users
            ]

    async def close(self):
        """Закрытие соединений с базой данных"""
        await engine.dispose()


# Создаем экземпляр базы данных
db = Database()


# Функция для получения сессии (для совместимости с существующим кодом)
async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session