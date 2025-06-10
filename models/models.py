from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    String, Date, Numeric, Text,
    ForeignKey, Integer, TIMESTAMP, UniqueConstraint, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ---- Base ------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---- Models ---------------------------------------------------------------
class Exhibition(Base):
    __tablename__ = "exhibitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255)) # Title of the exhibition
    date_start: Mapped[datetime] = mapped_column(Date) # Start date of the exhibition
    date_end: Mapped[datetime] = mapped_column(Date) # End date of the exhibition
    venue: Mapped[str] = mapped_column(String(255)) # Venue where the exhibition is held
    location: Mapped[str] = mapped_column(String(255)) # Town or city where the exhibition is located
    county: Mapped[Optional[str]] = mapped_column(String(100)) # County of the exhibition
    description: Mapped[Optional[str]] = mapped_column(Text) # Description of the exhibition
    url_id: Mapped[int] = mapped_column(ForeignKey("urls.id")) # Foreign key to the URL table
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )  # Timestamp when the exhibition was created
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )  # Timestamp when the exhibition was last updated


    entry_fees: Mapped[List["EntryFee"]] = relationship(back_populates="exhibition")
    prizes:     Mapped[List["Prize"]]    = relationship(back_populates="exhibition")
    url:        Mapped["Url"]            = relationship(back_populates="exhibitions")


class EntryFee(Base):
    __tablename__ = "entry_fees"

    id: Mapped[int] = mapped_column(primary_key=True)
    exhibition_id: Mapped[int] = mapped_column(ForeignKey("exhibitions.id"))
    fee_type: Mapped[str] = mapped_column(
        String(10), default="tier", nullable=False
    )  # 'tier' or 'flat'

    number_entries: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # Number of entries for tiered fees, or None for flat fees
    fee_amount:     Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2)) # Amount of the fee for each entry (e.g., 25.00)
    flat_rate:      Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2)) # Flat rate fee for the exhibition, if applicable
    commission_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2)) # Commission percentage for the exhibition, if applicable

    __table_args__ = (
        # one tier per entry count
        UniqueConstraint("exhibition_id", "number_entries",
                         name="u_exh_entries"),
        # application-level rule: only one flat row per exhibition
    )

    exhibition: Mapped["Exhibition"] = relationship(back_populates="entry_fees")



class Prize(Base):
    __tablename__ = "prizes"

    id: Mapped[int] = mapped_column(primary_key=True) # Unique identifier for the prize
    exhibition_id:   Mapped[int] = mapped_column(ForeignKey("exhibitions.id")) # Foreign key to the exhibition table
    prize_rank:      Mapped[Optional[int]] = mapped_column(Integer) # Rank of the prize (e.g., 1st, 2nd, 3rd)
    prize_amount:    Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2)) # Amount of the prize for each award type
    prize_type:      Mapped[Optional[str]] = mapped_column(String(50)) # Type of the prize (e.g., cash, gift card, etc.)
    prize_description: Mapped[Optional[str]] = mapped_column(Text) # Description of the prize
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )  # Timestamp when the prize was created
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )  # Timestamp when the prize was last updated

    exhibition: Mapped["Exhibition"] = relationship(back_populates="prizes")


class Url(Base):
    __tablename__ = "urls"

    id: Mapped[int] = mapped_column(primary_key=True) # Unique identifier for the URL
    raw_title:       Mapped[Optional[str]] = mapped_column(Text) # Raw title of the webpage
    raw_date:        Mapped[Optional[str]] = mapped_column(Text) # Raw date extracted from the webpage
    raw_location:    Mapped[Optional[str]] = mapped_column(Text) # Raw location extracted from the webpage
    raw_description: Mapped[Optional[str]] = mapped_column(Text) # Raw description extracted from the webpage
    url:             Mapped[str] = mapped_column(Text, unique=True) # URL of the webpage
    # Timestamp when the URL was first seen
    first_seen:      Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    ) # Timestamp when the URL was last updated
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )  # Timestamp when the URL was last updated

    exhibitions: Mapped[List["Exhibition"]] = relationship(back_populates="url")