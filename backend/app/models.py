import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _token() -> str:
    return secrets.token_urlsafe(16)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Room(Base):
    """A draft room. One room = one series (Bo1/Bo3/Bo5)."""

    __tablename__ = "rooms"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    mode: Mapped[str] = mapped_column(String(16))  # 'standard' | 'fearless'
    best_of: Mapped[int] = mapped_column(Integer, default=1)
    timer_seconds: Mapped[int] = mapped_column(Integer, default=30)
    blue_name: Mapped[str] = mapped_column(String(40), default="Equipo Azul")
    red_name: Mapped[str] = mapped_column(String(40), default="Equipo Rojo")

    # Role is ALWAYS derived from which of these tokens the client presents.
    blue_token: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, default=_token
    )
    red_token: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, default=_token
    )
    spectator_token: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, default=_token
    )

    games: Mapped[list["Game"]] = relationship(
        back_populates="room", order_by="Game.game_number"
    )


class Game(Base):
    """One draft within a series."""

    __tablename__ = "games"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id"), index=True)
    game_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(16), default="waiting"
    )  # 'waiting' | 'in_progress' | 'completed'
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    room: Mapped[Room] = relationship(back_populates="games")
    actions: Mapped[list["DraftAction"]] = relationship(
        back_populates="game", order_by="DraftAction.turn_index"
    )


class DraftAction(Base):
    """A confirmed ban or pick. champion_id is NULL for a skipped ban (timeout)."""

    __tablename__ = "draft_actions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"), index=True)
    turn_index: Mapped[int] = mapped_column(Integer)  # 0..19
    action_type: Mapped[str] = mapped_column(String(8))  # 'ban' | 'pick'
    team: Mapped[str] = mapped_column(String(8))  # 'blue' | 'red'
    champion_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_auto: Mapped[bool] = mapped_column(Boolean, default=False)
    # Lane assigned after the draft ends (picks only): 'top'|'jungle'|'mid'|
    # 'bot'|'support'. NULL until a captain assigns it. Kept for Phase 2 analysis.
    lane: Mapped[str | None] = mapped_column(String(8), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    game: Mapped[Game] = relationship(back_populates="actions")
