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
from sqlalchemy import select, and_, func, text
from sqlalchemy.orm import selectinload
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

    # ───── Enhanced Helper Functions ────────────────────────────────────────────────────────

    async def bulk_insert_exhibitions(self, exhibitions_data: list[dict]) -> list[Exhibition]:
        """
        Bulk insert multiple exhibitions for better performance.
        According to SQLAlchemy best practices: Use bulk operations for large datasets.
        
        Args:
            exhibitions_data: List of dictionaries containing exhibition data.
                            Each dict should contain all required Exhibition fields.
        
        Returns:
            List of inserted Exhibition objects with their IDs.
        """
        if not exhibitions_data:
            return []
            
        async with self.get_transaction() as session:
            exhibitions = []
            
            for data in exhibitions_data:
                # Validate required fields
                required_fields = ['title', 'date_start', 'date_end', 'venue', 'location', 'url_id']
                for field in required_fields:
                    if field not in data:
                        raise ValueError(f"Missing required field: {field}")
                
                exhibition = Exhibition(**data)
                session.add(exhibition)
                exhibitions.append(exhibition)
            
            # Flush to get IDs for all exhibitions
            await session.flush()
            return exhibitions

    async def get_exhibitions_by_criteria(
        self, 
        date_range: tuple[str, str] | None = None,
        location: str | None = None, 
        fee_range: tuple[float, float] | None = None
    ) -> list[Exhibition]:
        """
        Query exhibitions by multiple criteria with proper filtering.
        According to SQLAlchemy best practices: Use parameterized queries and joins.
        
        Args:
            date_range: Tuple of (start_date, end_date) in YYYY-MM-DD format, or None for no date filter
            location: Location string to search for (case-insensitive), or None for no location filter  
            fee_range: Tuple of (min_fee, max_fee) for entry fee filtering, or None for no fee filter
            
        Returns:
            List of Exhibition objects matching the criteria.
        """
        async with self.get_session() as session:
            # Start with base query, eager load related data
            stmt = select(Exhibition).options(
                selectinload(Exhibition.entry_fees),
                selectinload(Exhibition.prizes)
            )
            
            # Apply date range filter
            if date_range:
                start_date, end_date = date_range
                stmt = stmt.where(
                    and_(
                        Exhibition.date_start >= start_date,
                        Exhibition.date_end <= end_date
                    )
                )
            
            # Apply location filter (case-insensitive)
            if location:
                stmt = stmt.where(
                    Exhibition.location.ilike(f"%{location}%")
                )
            
            # Apply fee range filter (requires join with entry_fees)
            if fee_range:
                min_fee, max_fee = fee_range
                stmt = stmt.join(EntryFee).where(
                    and_(
                        EntryFee.fee_amount >= min_fee,
                        EntryFee.fee_amount <= max_fee
                    )
                ).distinct()  # Avoid duplicate exhibitions
            
            # Order by date for consistent results
            stmt = stmt.order_by(Exhibition.date_start)
            
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def generate_fee_analysis_report(self) -> dict:
        """
        Generate comprehensive fee analysis report with statistics.
        According to SQLAlchemy best practices: Use aggregate functions for analytics.
        
        Returns:
            Dictionary containing fee analysis statistics and insights.
        """
        async with self.get_session() as session:
            # Basic fee statistics
            fee_stats_stmt = select(
                func.count(EntryFee.id).label('total_fees'),
                func.avg(EntryFee.fee_amount).label('avg_fee'),
                func.min(EntryFee.fee_amount).label('min_fee'),
                func.max(EntryFee.fee_amount).label('max_fee'),
                func.sum(EntryFee.fee_amount).label('total_fee_value')
            ).where(EntryFee.fee_amount.is_not(None))
            
            result = await session.execute(fee_stats_stmt)
            fee_stats = result.first()
            
            # Fee distribution by tier
            tier_stats_stmt = select(
                EntryFee.number_entries,
                func.count(EntryFee.id).label('count'),
                func.avg(EntryFee.fee_amount).label('avg_fee')
            ).where(
                and_(
                    EntryFee.fee_amount.is_not(None),
                    EntryFee.number_entries.is_not(None)
                )
            ).group_by(EntryFee.number_entries).order_by(EntryFee.number_entries)
            
            result = await session.execute(tier_stats_stmt)
            tier_distribution = []
            for row in result:
                tier_distribution.append({
                    'tier': row.number_entries,
                    'count': row.count,
                    'avg_fee': float(row.avg_fee) if row.avg_fee else 0
                })
            
            # Commission analysis
            commission_stats_stmt = select(
                func.count(EntryFee.id).label('total_with_commission'),
                func.avg(EntryFee.commission_percent).label('avg_commission'),
                func.min(EntryFee.commission_percent).label('min_commission'),
                func.max(EntryFee.commission_percent).label('max_commission')
            ).where(EntryFee.commission_percent.is_not(None))
            
            result = await session.execute(commission_stats_stmt)
            commission_stats = result.first()
            
            # Fee type analysis
            fee_types_stmt = select(
                EntryFee.fee_type,
                func.count(EntryFee.id).label('count')
            ).group_by(EntryFee.fee_type)
            
            result = await session.execute(fee_types_stmt)
            fee_types = {}
            for row in result:
                fee_types[row.fee_type] = row.count
            
            return {
                'summary': {
                    'total_fees': fee_stats.total_fees or 0,
                    'average_fee': float(fee_stats.avg_fee) if fee_stats.avg_fee else 0,
                    'min_fee': float(fee_stats.min_fee) if fee_stats.min_fee else 0,
                    'max_fee': float(fee_stats.max_fee) if fee_stats.max_fee else 0,
                    'total_fee_value': float(fee_stats.total_fee_value) if fee_stats.total_fee_value else 0
                },
                'tier_distribution': tier_distribution,
                'commission_analysis': {
                    'total_with_commission': commission_stats.total_with_commission or 0,
                    'avg_commission': float(commission_stats.avg_commission) if commission_stats.avg_commission else 0,
                    'min_commission': float(commission_stats.min_commission) if commission_stats.min_commission else 0,
                    'max_commission': float(commission_stats.max_commission) if commission_stats.max_commission else 0
                },
                'fee_types': fee_types
            }

    async def cleanup_duplicate_entries(self) -> dict:
        """
        Clean up duplicate entries in the database.
        According to SQLAlchemy best practices: Use subqueries to identify and remove duplicates.
        
        Returns:
            Dictionary with cleanup statistics.
        """
        async with self.get_transaction() as session:
            cleanup_stats = {
                'duplicate_urls_removed': 0,
                'duplicate_exhibitions_removed': 0,
                'duplicate_entry_fees_removed': 0,
                'duplicate_prizes_removed': 0
            }
            
            # Remove duplicate URLs (same URL string)
            duplicate_urls_stmt = select(Url.id).where(
                Url.id.not_in(
                    select(func.min(Url.id)).group_by(Url.url)
                )
            )
            result = await session.execute(duplicate_urls_stmt)
            duplicate_url_ids = [row[0] for row in result]
            
            if duplicate_url_ids:
                delete_urls_stmt = select(Url).where(Url.id.in_(duplicate_url_ids))
                urls_to_delete = await session.execute(delete_urls_stmt)
                for url in urls_to_delete.scalars():
                    session.delete(url)
                cleanup_stats['duplicate_urls_removed'] = len(duplicate_url_ids)
            
            # Remove duplicate exhibitions (same title, date_start, venue combination)
            duplicate_exhibitions_stmt = select(Exhibition.id).where(
                Exhibition.id.not_in(
                    select(func.min(Exhibition.id)).group_by(
                        Exhibition.title, Exhibition.date_start, Exhibition.venue
                    )
                )
            )
            result = await session.execute(duplicate_exhibitions_stmt)
            duplicate_exhibition_ids = [row[0] for row in result]
            
            if duplicate_exhibition_ids:
                delete_exhibitions_stmt = select(Exhibition).where(Exhibition.id.in_(duplicate_exhibition_ids))
                exhibitions_to_delete = await session.execute(delete_exhibitions_stmt)
                for exhibition in exhibitions_to_delete.scalars():
                    session.delete(exhibition)
                cleanup_stats['duplicate_exhibitions_removed'] = len(duplicate_exhibition_ids)
            
            # Remove duplicate entry fees (already handled by unique constraint, but clean up orphans)
            # Find orphaned entry fees (where exhibition no longer exists)
            orphaned_fees_stmt = select(EntryFee.id).outerjoin(Exhibition).where(Exhibition.id.is_(None))
            result = await session.execute(orphaned_fees_stmt)
            orphaned_fee_ids = [row[0] for row in result]
            
            if orphaned_fee_ids:
                delete_fees_stmt = select(EntryFee).where(EntryFee.id.in_(orphaned_fee_ids))
                fees_to_delete = await session.execute(delete_fees_stmt)
                for fee in fees_to_delete.scalars():
                    session.delete(fee)
                cleanup_stats['duplicate_entry_fees_removed'] = len(orphaned_fee_ids)
            
            # Remove orphaned prizes
            orphaned_prizes_stmt = select(Prize.id).outerjoin(Exhibition).where(Exhibition.id.is_(None))
            result = await session.execute(orphaned_prizes_stmt)
            orphaned_prize_ids = [row[0] for row in result]
            
            if orphaned_prize_ids:
                delete_prizes_stmt = select(Prize).where(Prize.id.in_(orphaned_prize_ids))
                prizes_to_delete = await session.execute(delete_prizes_stmt)
                for prize in prizes_to_delete.scalars():
                    session.delete(prize)
                cleanup_stats['duplicate_prizes_removed'] = len(orphaned_prize_ids)
            
            await session.flush()
            return cleanup_stats

    async def add_database_indexes(self) -> dict:
        """
        Add database indexes for query optimization.
        According to SQLite best practices: Create indexes on frequently queried columns.
        
        Returns:
            Dictionary with indexing results.
        """
        async with self.engine.begin() as conn:
            index_results = {
                'indexes_created': [],
                'indexes_already_exist': [],
                'errors': []
            }
            
            # Define indexes to create
            indexes_to_create = [
                # Exhibition indexes for common queries
                ("idx_exhibitions_date_start", "exhibitions", ["date_start"]),
                ("idx_exhibitions_date_end", "exhibitions", ["date_end"]),
                ("idx_exhibitions_location", "exhibitions", ["location"]),
                ("idx_exhibitions_venue", "exhibitions", ["venue"]),
                ("idx_exhibitions_url_id", "exhibitions", ["url_id"]),
                ("idx_exhibitions_date_range", "exhibitions", ["date_start", "date_end"]),
                
                # EntryFee indexes for fee analysis
                ("idx_entry_fees_amount", "entry_fees", ["fee_amount"]),
                ("idx_entry_fees_exhibition_id", "entry_fees", ["exhibition_id"]),
                ("idx_entry_fees_commission", "entry_fees", ["commission_percent"]),
                ("idx_entry_fees_type", "entry_fees", ["fee_type"]),
                
                # Prize indexes
                ("idx_prizes_exhibition_id", "prizes", ["exhibition_id"]),
                ("idx_prizes_amount", "prizes", ["prize_amount"]),
                ("idx_prizes_rank", "prizes", ["prize_rank"]),
                
                # URL indexes
                ("idx_urls_url", "urls", ["url"]),
            ]
            
            for index_name, table_name, columns in indexes_to_create:
                try:
                    # Check if index already exists
                    check_index_sql = f"""
                    SELECT name FROM sqlite_master 
                    WHERE type='index' AND name='{index_name}'
                    """
                    result = await conn.execute(text(check_index_sql))
                    existing = result.fetchone()
                    
                    if existing:
                        index_results['indexes_already_exist'].append(index_name)
                        continue
                    
                    # Create the index
                    columns_str = ", ".join(columns)
                    create_index_sql = f"""
                    CREATE INDEX {index_name} ON {table_name} ({columns_str})
                    """
                    await conn.execute(text(create_index_sql))
                    index_results['indexes_created'].append(index_name)
                    
                except Exception as e:
                    index_results['errors'].append(f"{index_name}: {str(e)}")
            
            # Analyze tables for query optimization (SQLite best practice)
            try:
                await conn.execute(text("ANALYZE"))
            except Exception as e:
                index_results['errors'].append(f"ANALYZE failed: {str(e)}")
            
            return index_results


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
