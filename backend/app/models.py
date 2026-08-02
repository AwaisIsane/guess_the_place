import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def now() -> datetime:
    return datetime.now(UTC)


class GameStatus(enum.StrEnum):
    active = "active"
    complete = "complete"
    expired = "expired"


class LocationStatus(enum.StrEnum):
    active = "active"
    stale = "stale"
    deleted = "deleted"


class Game(Base):
    __tablename__ = "games"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[GameStatus] = mapped_column(SAEnum(GameStatus), default=GameStatus.active)
    current_round: Mapped[int] = mapped_column(Integer, default=1)
    total_score: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    rounds: Mapped[list[Round]] = relationship(
        back_populates="game", cascade="all, delete-orphan", order_by="Round.number"
    )


class PlayableLocation(Base):
    __tablename__ = "playable_locations"
    id: Mapped[int] = mapped_column(primary_key=True)
    image_id: Mapped[str] = mapped_column(String(128), unique=True)
    sequence_id: Mapped[str | None] = mapped_column(String(128))
    country_code: Mapped[str] = mapped_column(String(2), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    compass_angle: Mapped[float | None] = mapped_column(Float)
    quality: Mapped[float] = mapped_column(Float, default=1)
    status: Mapped[LocationStatus] = mapped_column(
        SAEnum(LocationStatus), default=LocationStatus.active, index=True
    )
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_selected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    __table_args__ = (
        Index("ix_location_country_status_quality", "country_code", "status", "quality"),
    )


class Round(Base):
    __tablename__ = "rounds"
    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), index=True
    )
    location_id: Mapped[int] = mapped_column(ForeignKey("playable_locations.id"))
    number: Mapped[int] = mapped_column(Integer)
    guessed: Mapped[bool] = mapped_column(Boolean, default=False)
    guess_latitude: Mapped[float | None] = mapped_column(Float)
    guess_longitude: Mapped[float | None] = mapped_column(Float)
    distance_km: Mapped[float | None] = mapped_column(Float)
    score: Mapped[int | None] = mapped_column(Integer)
    guessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[uuid.UUID | None] = mapped_column(unique=True)
    game: Mapped[Game] = relationship(back_populates="rounds")
    location: Mapped[PlayableLocation] = relationship()

    __table_args__ = (UniqueConstraint("game_id", "number"),)


class CountryCatalog(Base):
    __tablename__ = "country_catalog"
    country_code: Mapped[str] = mapped_column(String(2), primary_key=True)
    active_count: Mapped[int] = mapped_column(Integer, default=0)
    last_refilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_cursor: Mapped[str | None] = mapped_column(String(512))


class ProviderState(Base):
    __tablename__ = "provider_state"
    provider: Mapped[str] = mapped_column(String(32), primary_key=True)
    circuit_open_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
