# models.py

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    player_id: Mapped[str] = mapped_column(
        String(5),
        unique=True,
        nullable=False,
        index=True
    )

    team: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )

    registered: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    registered_date: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    games_played: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    wins: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    losses: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    last_active: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    history: Mapped[list["UserHistory"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self):
        return (
            f"<User("
            f"user_id={self.user_id}, "
            f"name='{self.name}', "
            f"player_id='{self.player_id}')>"
        )


class TeamStats(Base):
    __tablename__ = "team_stats"

    team: Mapped[str] = mapped_column(
        String(20),
        primary_key=True
    )

    total_players: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    total_wins: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    total_games: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    def __repr__(self):
        return f"<TeamStats(team='{self.team}')>"


class UserHistory(Base):
    __tablename__ = "user_history"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.user_id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    details: Mapped[str] = mapped_column(
        Text,
        default=""
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    user: Mapped["User"] = relationship(
        back_populates="history"
    )

    def __repr__(self):
        return (
            f"<UserHistory("
            f"user_id={self.user_id}, "
            f"action='{self.action}')>"
        )
