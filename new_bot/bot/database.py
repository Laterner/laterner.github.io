# database.py
import os
import random
import string
from datetime import datetime
from typing import Optional, Dict, List, Any

from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.exc import IntegrityError

from models import User, TeamStats, UserHistory, Base
from utils import TEAMS


# Загрузка переменных окружения
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

    async def init_db(self):
        """Инициализация базы данных (создание таблиц)"""
        async with engine.begin() as conn:
            # Создаем все таблицы
            await conn.run_sync(Base.metadata.create_all)
            
            # Инициализируем статистику команд
            await self._init_team_stats()
            
            return await self.get_all_teams_stats()
            
    async def _init_team_stats(self):
        """Инициализация записей статистики для всех команд"""
        async with SessionLocal() as session:
            for _team in TEAMS:
                print("--------->", _team)
                # Проверяем, существует ли запись для команды
                result = await session.execute(
                    select(TeamStats).where(TeamStats.team == _team)
                )
                stats = result.scalar_one_or_none()
                
                if stats is None:
                    # Создаем запись для команды
                    new_stats = TeamStats(team=_team)
                    session.add(new_stats)
            
            await session.commit()

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение данных пользователя"""
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
                    'team_name': user.team_name,
                    'registered': user.registered,
                    'registered_date': user.registered_date,
                    'score': user.score,
                    'games_played': user.games_played,
                    'wins': user.wins,
                    'losses': user.losses,
                    'last_active': user.last_active,
                }
            return None

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

    async def add_user(self, user_id: int, name: str, player_id: str, team_id: int) -> bool:
        """Добавление нового пользователя"""
        async with SessionLocal() as session:
            try:
                # Обновляем статистику команды
                result = await session.execute(
                    select(TeamStats).where(TeamStats.id == team_id)
                )
                team_stats = result.scalar_one_or_none()
                
                if team_stats:
                    team_stats.total_players += 1
                else:
                    return False

                # Создаем пользователя
                user = User(
                    user_id=user_id,
                    name=name,
                    player_id=player_id,
                    team=team_id,
                    team_name=team_stats.team,
                    registered=True,
                )
                
                session.add(user)
                
                await session.commit()
                return True
                
            except IntegrityError:
                await session.rollback()
                return False
            except Exception as e:
                await session.rollback()
                print(f"Error adding user: {e}")
                return False

    async def update_user_team(self, user_id: int, new_team: int) -> bool:
        """Обновление команды пользователя"""
        async with SessionLocal() as session:
            try:
                # Получаем пользователя
                result = await session.execute(
                    select(User).where(User.user_id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    return False
                
                old_team = user.team
                
                # Обновляем команду пользователя
                user.team = new_team
                user.last_active = datetime.utcnow()
                
                # Обновляем статистику команд
                # Уменьшаем для старой команды
                result_old = await session.execute(
                    select(TeamStats).where(TeamStats.team == old_team)
                )
                old_stats = result_old.scalar_one_or_none()
                if old_stats and old_stats.total_players > 0:
                    old_stats.total_players -= 1
                
                # Увеличиваем для новой команды
                result_new = await session.execute(
                    select(TeamStats).where(TeamStats.id == new_team)
                )
                new_stats = result_new.scalar_one_or_none()
                if new_stats:
                    new_stats.total_players += 1
                else:
                    return False
                
                await session.commit()
                return True
                
            except Exception as e:
                await session.rollback()
                print(f"Error updating team: {e}")
                return False

    async def update_user_score(self, user_id: int, score_change: int, win: bool = False) -> bool:
        """Обновление очков пользователя и статистики"""
        async with SessionLocal() as session:
            try:
                # Получаем пользователя
                result = await session.execute(
                    select(User).where(User.user_id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    return False
                
                # Обновляем пользователя
                user.score += score_change
                user.games_played += 1
                user.last_active = datetime.utcnow()
                
                if win:
                    user.wins += 1
                else:
                    user.losses += 1
                
                # Обновляем статистику команды
                result_team = await session.execute(
                    select(TeamStats).where(TeamStats.team == user.team)
                )
                team_stats = result_team.scalar_one_or_none()
                if team_stats:
                    team_stats.total_games += 1
                    if win:
                        team_stats.total_wins += 1
                
                await session.commit()
                return True
                
            except Exception as e:
                await session.rollback()
                print(f"Error updating score: {e}")
                return False

    async def update_team_stats(self, team: str, add_player: bool = True):
        """Обновление статистики команды"""
        async with SessionLocal() as session:
            try:
                result = await session.execute(
                    select(TeamStats).where(TeamStats.team == team)
                )
                team_stats = result.scalar_one_or_none()
                
                if team_stats:
                    if add_player:
                        team_stats.total_players += 1
                    else:
                        team_stats.total_players = max(0, team_stats.total_players - 1)
                else:
                    # Если записи нет, создаем
                    team_stats = TeamStats(
                        team=team,
                        total_players=1 if add_player else 0
                    )
                    session.add(team_stats)
                
                await session.commit()
                
            except Exception as e:
                await session.rollback()
                print(f"Error updating team stats: {e}")

    async def get_team_stats(self, team_id: int) -> Optional[Dict[str, Any]]:
        """Получение статистики команды"""
        async with SessionLocal() as session:
            result = await session.execute(
                select(TeamStats).where(TeamStats.id == team_id)
            )
            stats = result.scalar_one_or_none()
            
            if stats:
                return {
                    'team': stats.team,
                    'total_players': stats.total_players,
                    'total_wins': stats.total_wins,
                    'total_games': stats.total_games,
                }
            return None

    async def get_all_teams_stats(self) -> List[Dict[str, Any]]:
        """Получение статистики всех команд"""
        async with SessionLocal() as session:
            result = await session.execute(
                select(TeamStats).order_by(TeamStats.id)
            )
            stats = result.scalars().all()
            
            return [
                {
                    'id': s.id,
                    'team': s.team,
                    'total_players': s.total_players,
                    'total_wins': s.total_wins,
                    'total_games': s.total_games,
                }
                for s in stats
            ]

    async def add_history(self, user_id: int, action: str, details: str = ""):
        """Добавление записи в историю"""
        async with SessionLocal() as session:
            try:
                history = UserHistory(
                    user_id=user_id,
                    action=action,
                    details=details,
                )
                session.add(history)
                await session.commit()
            except Exception as e:
                await session.rollback()
                print(f"Error adding history: {e}")

    async def get_user_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение истории пользователя"""
        async with SessionLocal() as session:
            result = await session.execute(
                select(UserHistory)
                .where(UserHistory.user_id == user_id)
                .order_by(desc(UserHistory.timestamp))
                .limit(limit)
            )
            history = result.scalars().all()
            
            return [
                {
                    'id': h.id,
                    'user_id': h.user_id,
                    'action': h.action,
                    'details': h.details,
                    'timestamp': h.timestamp.isoformat(),
                }
                for h in history
            ]

    async def get_top_players(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение топ игроков по очкам"""
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
                    'score': u.score,
                    'wins': u.wins,
                    'games_played': u.games_played,
                }
                for u in users
            ]

    async def delete_user(self, user_id: int) -> bool:
        """Удаление пользователя"""
        async with SessionLocal() as session:
            try:
                # Получаем пользователя
                result = await session.execute(
                    select(User).where(User.user_id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    return False
                
                team = user.team
                
                # Удаляем пользователя
                await session.delete(user)
                
                # Обновляем статистику команды
                result_team = await session.execute(
                    select(TeamStats).where(TeamStats.team == team)
                )
                team_stats = result_team.scalar_one_or_none()
                if team_stats and team_stats.total_players > 0:
                    team_stats.total_players -= 1
                
                await session.commit()
                return True
                
            except Exception as e:
                await session.rollback()
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
        """Закрытие соединений с базой данных"""
        await engine.dispose()


# Функция для генерации уникального player_id
async def generate_player_id(db_instance: Database) -> str:
    """Генерация уникального 5-значного player_id"""
    async with SessionLocal() as session:
        while True:
            # Генерируем 5-значный ID
            player_id = ''.join(random.choices(string.digits, k=5))
            
            # Проверяем, не занят ли ID
            result = await session.execute(
                select(User).where(User.player_id == player_id)
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                return player_id


# Создаем экземпляр базы данных для использования в боте
db = Database()


# Функция для получения сессии (для совместимости с существующим кодом)
async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session