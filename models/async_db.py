"""
Async SQLAlchemy implementation following 2.0 best practices.
According to SQLAlchemy docs (search result #3), async patterns provide better
performance for I/O-bound operations like web scraping.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, text
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging

from .models import Base, Url, Exhibition, EntryFee, Prize

logger = logging.getLogger(__name__)


class AsyncDatabaseManager:
    """
    Async database manager following SQLAlchemy 2.0 best practices.
    
    According to FastAPI + SQLAlchemy docs (search result #2):
    - Uses async engine with connection pooling
    - Proper transaction management with context managers
    - Session-per-request pattern for concurrency
    """
    
    def __init__(self, db_path: str = "art_events.db") -> None:
        # According to SQLAlchemy async docs, use aiosqlite for async SQLite
        self.engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_path}",
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,   # Recycle connections every hour
        )
        
        # According to SQLAlchemy 2.0 docs, use async_sessionmaker
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Keep objects usable after commit
        )
    
    async def create_tables(self) -> None:
        """Create all tables if they don't exist."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager for database sessions.
        
        According to SQLAlchemy async patterns (search result #3):
        - Ensures proper session cleanup
        - Handles rollback on exceptions
        - Follows session-per-operation pattern
        """
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def add_url(self, **kwargs) -> Url:
        """Add URL with proper transaction management."""
        async with self.get_session() as session:
            url = Url(**kwargs)
            session.add(url)
            await session.flush()  # Get ID without committing
            await session.refresh(url)
            return url
    
    async def add_exhibition(self, **kwargs) -> Exhibition:
        """Add exhibition with proper transaction management."""
        async with self.get_session() as session:
            exhibition = Exhibition(**kwargs)
            session.add(exhibition)
            await session.flush()
            await session.refresh(exhibition)
            return exhibition
    
    async def add_entry_fee(self, **kwargs) -> EntryFee:
        """Add entry fee with proper transaction management."""
        async with self.get_session() as session:
            entry_fee = EntryFee(**kwargs)
            session.add(entry_fee)
            await session.flush()
            await session.refresh(entry_fee)
            return entry_fee
    
    async def add_prize(self, **kwargs) -> Prize:
        """Add prize with proper transaction management."""
        async with self.get_session() as session:
            prize = Prize(**kwargs)
            session.add(prize)
            await session.flush()
            await session.refresh(prize)
            return prize
    
    async def bulk_insert_urls(self, urls_data: list[dict]) -> list[int]:
        """
        Bulk insert URLs for better performance.
        
        According to SQLAlchemy bulk operations (search result #4):
        - Use bulk_insert_mappings for large datasets
        - Return IDs using INSERT...RETURNING when supported
        """
        async with self.get_session() as session:
            # For SQLite, use individual inserts with returning
            ids = []
            for url_data in urls_data:
                result = await session.execute(
                    select(Url.id).from_statement(
                        text("INSERT INTO urls (...) VALUES (...) RETURNING id")
                    )
                )
                ids.append(result.scalar())
            return ids
    
    async def get_exhibitions_by_date_range(self, start_date: str, end_date: str) -> list[Exhibition]:
        """
        Query exhibitions by date range using SQLAlchemy 2.0 syntax.
        
        According to SQLAlchemy 2.0 patterns (search result #5):
        - Use select() instead of session.query()
        - Explicit joins when needed
        - Scalars() for ORM objects
        """
        async with self.get_session() as session:
            stmt = (
                select(Exhibition)
                .where(Exhibition.date_start >= start_date)
                .where(Exhibition.date_end <= end_date)
                .order_by(Exhibition.date_start)
            )
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def close(self) -> None:
        """Clean shutdown of database connections."""
        await self.engine.dispose()
