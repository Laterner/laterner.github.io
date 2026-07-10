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

from models import User, UserHistory, Quize, QuizeAnswer, TeamStats, UserQuizProgress, Base

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
                user: User = result.scalar_one_or_none()
                
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
                
                result = await session.execute(
                    select(TeamStats).where(TeamStats.id == user.team)
                )
                
                team: TeamStats = result.scalar_one_or_none()
                team.total_games += 1
                team.total_wins += 1
                
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
    
    async def get_user_rank_by_player_id(self, player_id) -> List[Dict[str, Any]]:
        """Получение своей позиции в рейтенге"""
        subquery = select(
            User.user_id,
            User.score,
            func.row_number().over(
                order_by=User.score.desc()
            ).label('rank')
        ).subquery()
        
        # Основной запрос для получения ранга конкретного пользователя
        query = select(
            subquery.c.rank
        ).where(
            subquery.c.user_id == select(User.user_id).where(User.player_id == player_id).scalar_subquery()
        )
        
        async with SessionLocal() as session:
            result = await session.execute(query)
            rank = result.scalar_one_or_none()
            
            return rank
        
    async def get_all_teams_stats(self) -> List[Dict[str, Any]]:
        """Получение статистики всех команд"""
        async with SessionLocal() as session:
            result = await session.execute(
                select(TeamStats).order_by(TeamStats.team)
            )
            stats = result.scalars().all()
            
            return [
                {
                    'name': s.team,
                    'total_players': s.total_players,
                    'total_wins': s.total_wins,
                    'total_games': s.total_games,
                }
                for s in stats
            ]
    
    async def create_quize(self, question: str, secret_code: str, answer: int, answers: list[str]) -> Quize:
        """Добавление нового опроса"""
        async with SessionLocal() as session:
            try:
                # Создаем список объектов QuizeAnswer без quize_id
                # (он проставится автоматически через relationship)
                quize_answers = [
                    QuizeAnswer(answer=el) for el in answers
                ]
                
                # Создаем опрос с ответами
                quize = Quize(
                    question=question,
                    answer=answer,
                    secret_code=secret_code,
                    quize_answers=quize_answers
                )
                
                session.add(quize)
                await session.commit()
                return Quize
            except Exception as e:
                await session.rollback()
                print(f"Error creating quiz: {e}")
                raise 
    
    
    async def get_quize(self, secret_code: int) -> Quize:
        print("secret_code in get -->", secret_code)
        async with SessionLocal() as session:
            try:
                result = await session.execute(
                    select(Quize).where(
                        Quize.secret_code == secret_code
                    )
                )
                quize = result.scalar_one_or_none()
                
                print("quiz found -->", quize)
                if quize == None:
                    return None
                
                answers = await session.execute(
                    select(QuizeAnswer).where(
                        QuizeAnswer.quize_id == quize.id
                    )
                )
                
                answers = answers.scalars().all()
                answers = [el.answer for el in answers]

                result = {
                    'id': quize.id,
                    'question': quize.question,
                    'secret_code': quize.secret_code,
                    'answers': answers
                }
                return result
            except Exception as e:
                print('error in database:', e)
    
    async def is_quiz_completed(self, player_id: int, quize_id: int) -> bool:
        """Проверка, прошел ли игрок конкретный квиз"""
        async with SessionLocal() as session:
            try:
                result = await session.execute(
                    select(UserQuizProgress).where(
                        UserQuizProgress.player_id == player_id,
                        UserQuizProgress.quize_id == quize_id,
                        UserQuizProgress.completed == True
                    )
                )
                progress = result.scalar_one_or_none()
                return progress is not None
                
            except Exception as e:
                print(f"Error checking quiz completion: {e}")
                return False
            
    async def update_quize_status(self, player_id: str, quize_id: int, is_correct: bool, amount: int):
        async with SessionLocal() as session:
            try:
                # Ищем или создаем запись прогресса
                progress = await session.execute(
                    select(UserQuizProgress).where(
                        UserQuizProgress.player_id == player_id,
                        UserQuizProgress.quize_id == quize_id
                    )
                )
                progress = progress.scalar_one_or_none()
                
                if not progress:
                    progress = UserQuizProgress(
                        player_id=player_id,
                        quize_id=quize_id
                    )
                    session.add(progress)
                
                # Обновляем статистику
                progress.attempts += 1
                
                if not is_correct:
                    progress.wrong_answers += 1
                else:
                    progress.completed = True
                    # Обновляем общую статистику пользователя
                    user = await session.get(User, player_id)
                    if user:
                        user.games_played += 1
                        user.score += amount
                
                await session.commit()
                
            except Exception as e:
                await session.rollback()
                print(f"Error recording quiz attempt: {e}")
                raise

    async def close(self):
        """Закрытие соединений с базой данных"""
        await engine.dispose()


# Создаем экземпляр базы данных
db = Database()


# Функция для получения сессии (для совместимости с существующим кодом)
async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session