"""
Modern async database manager following SQLAlchemy 2.x best practices.
According to SQLAlchemy docs: Use async sessions, proper transaction management, and connection pooling.
"""
import asyncio
import functools
import random
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, and_
from models.models import Base, Url, Exhibition, EntryFee, Prize


class AsyncDatabaseManager:
    """
    Modern async database manager with proper concurrency handling.
    According to SQLite best practices: Use WAL mode and proper transaction management.
    """
    
    def __init__(self, db_path: str = "art_events.db") -> None:
        # SQLite async URL with optimizations for concurrency
        database_url = f"sqlite+aiosqlite:///{db_path}"
        
        # Create async engine with proper SQLite optimizations
        # According to SQLite docs: Use WAL mode for better concurrency
        self.engine = create_async_engine(
            database_url,
            echo=False,  # Set to True for debugging
            pool_pre_ping=True,  # Validate connections
            connect_args={
                "check_same_thread": False,  # Required for async SQLite
            },
            # Enable WAL mode for better concurrency
            execution_options={
                "isolation_level": "AUTOCOMMIT"
            }
        )
          # Create async session maker
        self.async_session_maker = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
    async def initialize_database(self) -> None:
        """Initialize database tables and set SQLite optimizations."""
        async with self.engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            
            # Enable WAL mode for better concurrency (SQLite best practice)
            from sqlalchemy import text
            await conn.execute(text("PRAGMA journal_mode=WAL"))
            await conn.execute(text("PRAGMA synchronous=NORMAL"))
            await conn.execute(text("PRAGMA cache_size=10000"))
            await conn.execute(text("PRAGMA foreign_keys=ON"))

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager for database sessions with proper error handling.
        According to SQLAlchemy best practices: Use context managers for session management.
        """
        async with self.async_session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    @asynccontextmanager
    async def get_transaction(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager for transactions with automatic commit/rollback.
        According to SQLite best practices: Use transactions for data consistency.
        """
        async with self.get_session() as session:
            async with session.begin():
                try:
                    yield session
                    # Commit happens automatically when exiting context
                except Exception:
                    # Rollback happens automatically on exception
                    raise

    # ───── Modern CRUD operations with proper typing ────────────────────────────────────────
    
    async def add_url(self, **kwargs) -> Url:
        """Add URL with duplicate detection."""
        async with self.get_transaction() as session:
            # Check for existing URL to prevent duplicates
            stmt = select(Url).where(Url.url == kwargs.get('url'))
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                return existing
                
            url = Url(**kwargs)
            session.add(url)
            await session.flush()  # Get the ID without committing
            return url

    async def add_exhibition(self, **kwargs) -> Exhibition:
        """Add exhibition with validation."""
        async with self.get_transaction() as session:
            exhibition = Exhibition(**kwargs)
            session.add(exhibition)
            await session.flush()
            return exhibition

    async def add_entry_fee(self, **kwargs) -> EntryFee:
        """Add entry fee with duplicate checking."""
        async with self.get_transaction() as session:
            # Check for existing entry fee to prevent duplicates
            stmt = select(EntryFee).where(
                and_(
                    EntryFee.exhibition_id == kwargs.get('exhibition_id'),
                    EntryFee.number_entries == kwargs.get('number_entries')
                )
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                return existing
                
            fee = EntryFee(**kwargs)
            session.add(fee)
            await session.flush()
            return fee

    async def add_prize(self, **kwargs) -> Prize:
        """Add prize with validation."""
        async with self.get_transaction() as session:
            prize = Prize(**kwargs)
            session.add(prize)
            await session.flush()
            return prize

    async def get_exhibitions_by_date_range(
        self, 
        start_date: str, 
        end_date: str
    ) -> list[Exhibition]:
        """Query exhibitions by date range with proper async handling."""
        async with self.get_session() as session:
            stmt = select(Exhibition).where(
                and_(
                    Exhibition.date_start >= start_date,
                    Exhibition.date_end <= end_date
                )
            ).order_by(Exhibition.date_start)
            
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_urls_without_exhibitions(self) -> list[Url]:
        """Find URLs that haven't been processed yet."""
        async with self.get_session() as session:
            stmt = select(Url).outerjoin(Exhibition).where(Exhibition.id.is_(None))
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def close(self) -> None:
        """Properly dispose of the engine."""
        await self.engine.dispose()


# ───── Retry decorator for database operations ─────────────────────────────────────────

def async_retry(max_retries: int = 3, backoff_factor: float = 1.0):
    """
    Async retry decorator for database operations.
    According to best practices: Implement exponential backoff for transient errors.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == max_retries - 1:
                        break
                    
                    # Exponential backoff with jitter
                    delay = backoff_factor * (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(delay)
            
            raise last_exception
        return wrapper
    return decorator
