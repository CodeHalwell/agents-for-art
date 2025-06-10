"""
Modern SQLAlchemy 2.x model implementation following best practices.
According to SQLAlchemy docs: Use Mapped[], mapped_column(), and async patterns.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Annotated

from sqlalchemy import String, Date, Numeric, Text, ForeignKey, TIMESTAMP, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


# ---- Modern Base with proper typing ------------------------------------------------------------------
class Base(DeclarativeBase):
    """Modern DeclarativeBase following SQLAlchemy 2.x best practices"""
    pass


# Type aliases for better readability (SQLAlchemy 2.x best practice)
str_255 = Annotated[str, mapped_column(String(255))]
str_100 = Annotated[str, mapped_column(String(100))]
money = Annotated[Decimal, mapped_column(Numeric(10, 2))]
percent = Annotated[Decimal, mapped_column(Numeric(5, 2))]


# ---- Modern Models with proper typing ---------------------------------------------------------------
class Exhibition(Base):
    __tablename__ = "exhibitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str_255]  # Using type alias for consistency
    date_start: Mapped[datetime] = mapped_column(Date)
    date_end: Mapped[datetime] = mapped_column(Date)
    venue: Mapped[str_255]
    location: Mapped[str_255]
    county: Mapped[Optional[str_100]] = None
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    url_id: Mapped[int] = mapped_column(ForeignKey("urls.id"))
    
    # Better timestamp handling with timezone awareness
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), 
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships with proper typing
    entry_fees: Mapped[List["EntryFee"]] = relationship(back_populates="exhibition", cascade="all, delete-orphan")
    prizes: Mapped[List["Prize"]] = relationship(back_populates="exhibition", cascade="all, delete-orphan")
    url: Mapped["Url"] = relationship(back_populates="exhibitions")


class EntryFee(Base):
    __tablename__ = "entry_fees"

    id: Mapped[int] = mapped_column(primary_key=True)
    exhibition_id: Mapped[int] = mapped_column(ForeignKey("exhibitions.id"))
    fee_type: Mapped[str] = mapped_column(String(10), default="tier")
    
    number_entries: Mapped[Optional[int]] = None
    fee_amount: Mapped[Optional[money]] = None  # Using type alias
    flat_rate: Mapped[Optional[money]] = None
    commission_percent: Mapped[Optional[percent]] = None

    __table_args__ = (
        UniqueConstraint("exhibition_id", "number_entries", name="u_exh_entries"),
    )

    exhibition: Mapped["Exhibition"] = relationship(back_populates="entry_fees")


class Prize(Base):
    __tablename__ = "prizes"

    id: Mapped[int] = mapped_column(primary_key=True)
    exhibition_id: Mapped[int] = mapped_column(ForeignKey("exhibitions.id"))
    prize_rank: Mapped[Optional[int]] = None
    prize_amount: Mapped[Optional[money]] = None
    prize_type: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    prize_description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), 
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    exhibition: Mapped["Exhibition"] = relationship(back_populates="prizes")


class Url(Base):
    __tablename__ = "urls"

    id: Mapped[int] = mapped_column(primary_key=True)
    raw_title: Mapped[Optional[str]] = mapped_column(Text, default=None)
    raw_date: Mapped[Optional[str]] = mapped_column(Text, default=None)
    raw_location: Mapped[Optional[str]] = mapped_column(Text, default=None)
    raw_description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    url: Mapped[str] = mapped_column(Text, unique=True)
    
    first_seen: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), 
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    exhibitions: Mapped[List["Exhibition"]] = relationship(back_populates="url")
