"""
Enhanced async database tools following SQLAlchemy 2.x best practices.
According to SQLAlchemy docs: Use async operations and proper transaction management.
"""
from decimal import Decimal
from smolagents import tool
from sqlalchemy import inspect
import json

from models.db import AsyncDatabaseManager, async_retry


# Global async database manager
_db_manager = None

async def get_db_manager() -> AsyncDatabaseManager:
    """Get or create the global database manager."""
    global _db_manager
    if _db_manager is None:
        _db_manager = AsyncDatabaseManager()
        await _db_manager.initialize_database()
    return _db_manager


# ───────────────────────────── URL ──────────────────────────────
@tool
@async_retry(max_retries=3)
async def add_url_async(
    url: str,
    raw_title: str | None = None,
    raw_date: str | None = None,
    raw_location: str | None = None,
    raw_description: str | None = None,
) -> int:
    """
    Insert a row in the **urls** table asynchronously with duplicate detection.
    According to best practices: Use async operations and handle duplicates.

    Args:
        url: The absolute URL of the page that advertised the open call.
        raw_title: Optional raw title text scraped from the page.
        raw_date: Optional raw date string scraped from the page.
        raw_location: Optional raw location string scraped from the page.
        raw_description: Optional teaser / summary text scraped from the page.

    Returns:
        The primary‑key ID of the newly‑inserted or existing :class:`models.Url` row.
    """
    db = await get_db_manager()
    result = await db.add_url(
        url=url,
        raw_title=raw_title,
        raw_date=raw_date,
        raw_location=raw_location,
        raw_description=raw_description,
    )
    return result.id


# ─────────────────────────── EXHIBITION ─────────────────────────
@tool
@async_retry(max_retries=3)
async def add_exhibition_async(
    *,
    title: str,
    date_start: str,  # YYYY-MM-DD
    date_end: str,    # YYYY-MM-DD
    venue: str,
    location: str,
    county: str | None,
    url_id: int,
    description: str | None = None,
) -> int:
    """
    Insert a row in the **exhibitions** table asynchronously.
    According to best practices: Use async operations and proper validation.

    Args:
        title: Official exhibition title.
        date_start: First public day of the exhibition (YYYY‑MM‑DD).
        date_end: Last public day of the exhibition (YYYY‑MM‑DD).
        venue: Gallery / art‑fair name.
        location: Town or city where the venue is located.
        county: Optional county / region for more granular search.
        url_id: Foreign‑key linking back to the **urls** table.
        description: Optional long‑form description scraped from the page.

    Returns:
        The ID of the new :class:`models.Exhibition` row.
    """
    from datetime import date
    
    # Validate date format
    try:
        start_date = date.fromisoformat(date_start)
        end_date = date.fromisoformat(date_end)
        
        if start_date > end_date:
            raise ValueError(f"Start date {date_start} cannot be after end date {date_end}")
            
    except ValueError as e:
        raise ValueError(f"Invalid date format: {e}")

    db = await get_db_manager()
    result = await db.add_exhibition(
        title=title,
        date_start=start_date,
        date_end=end_date,
        venue=venue,
        location=location,
        county=county,
        url_id=url_id,
        description=description,
    )
    return result.id


# ─────────────────────────── ENTRY FEE ──────────────────────────
@tool
@async_retry(max_retries=3)
async def add_entry_fee_async(
    exhibition_id: int,
    number_entries: int,
    fee_amount: str,
    flat_rate: str | None = None,
    commission_percent: str | None = None,
) -> int:
    """
    Insert a row in the **entry_fees** table asynchronously with validation.
    According to best practices: Use async operations and validate numeric data.

    Args:
        exhibition_id: Foreign‑key to the parent exhibition.
        number_entries: The *exact* number of works this tier applies to.
        fee_amount: Monetary fee *per tier* (e.g. "25.00").
        flat_rate: Optional flat fee that overrides per‑piece tiers.
        commission_percent: Optional commission percentage charged on sales.

    Returns:
        The ID of the new :class:`models.EntryFee` row.
    """
    # Validate numeric inputs
    try:
        fee_decimal = Decimal(fee_amount)
        if fee_decimal < 0:
            raise ValueError("Fee amount cannot be negative")
            
        flat_decimal = Decimal(flat_rate) if flat_rate else None
        if flat_decimal is not None and flat_decimal < 0:
            raise ValueError("Flat rate cannot be negative")
            
        commission_decimal = Decimal(commission_percent) if commission_percent else None
        if commission_decimal is not None and (commission_decimal < 0 or commission_decimal > 100):
            raise ValueError("Commission percent must be between 0 and 100")
            
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid numeric value: {e}")

    db = await get_db_manager()
    result = await db.add_entry_fee(
        exhibition_id=exhibition_id,
        number_entries=number_entries,
        fee_amount=fee_decimal,
        flat_rate=flat_decimal,
        commission_percent=commission_decimal,
    )
    return result.id


# ───────────────────────────── PRIZE ────────────────────────────
@tool
@async_retry(max_retries=3)
async def add_prize_async(
    exhibition_id: int,
    prize_rank: int | None = None,
    prize_amount: str | None = None,
    prize_type: str | None = None,
    prize_description: str | None = None,
) -> int:
    """
    Insert a row in the **prizes** table asynchronously with validation.
    According to best practices: Use async operations and validate data.

    Args:
        exhibition_id: Foreign‑key to the parent exhibition.
        prize_rank: Ordinal rank (e.g. 1 for first prize). None if unranked.
        prize_amount: Cash value ("5000.00") or None for non‑cash awards.
        prize_type: Short label for the prize type (e.g. "cash", "materials").
        prize_description: Longer human‑readable description.

    Returns:
        The ID of the new :class:`models.Prize` row.
    """
    # Validate prize amount if provided
    amount_decimal = None
    if prize_amount:
        try:
            amount_decimal = Decimal(prize_amount)
            if amount_decimal < 0:
                raise ValueError("Prize amount cannot be negative")
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid prize amount: {e}")
    
    # Validate prize rank if provided  
    if prize_rank is not None and prize_rank < 1:
        raise ValueError("Prize rank must be positive")

    db = await get_db_manager()
    result = await db.add_prize(
        exhibition_id=exhibition_id,
        prize_rank=prize_rank,
        prize_amount=amount_decimal,
        prize_type=prize_type,
        prize_description=prize_description,
    )
    return result.id


@tool
async def describe_schema_async(table_name: str) -> str:
    """
    Return the column names and types for the given table asynchronously.
    According to best practices: Use async database operations.

    Args:
        table_name: Name of the table ("exhibitions", "entry_fees", "prizes", "urls").

    Returns:
        A human-readable list of columns and their SQL types.
    """
    try:
        db = await get_db_manager()
        
        async with db.get_session() as session:
            bind = session.bind
            if bind is None:
                return "ERROR: Database connection is not available"
            
            # Run sync inspection in async context
            def inspect_table(connection):
                insp = inspect(connection)
                table_names = insp.get_table_names()
                
                if table_name not in table_names:
                    return f"ERROR: no table named '{table_name}'. Available: {table_names}"
                
                cols = insp.get_columns(table_name)
                lines = [f"{c['name']}: {c['type']}" for c in cols]
                return "\n".join(lines)
            
            # Use run_sync to run the sync operation
            result = await session.connection()
            return await result.run_sync(inspect_table)
            
    except Exception as e:
        return f"ERROR: Failed to describe schema: {str(e)}"


# ───────────────────────── QUERY HELPERS ─────────────────────────
@tool
async def get_unprocessed_urls_async(limit: int = 50) -> str:
    """
    Get URLs that haven't been processed into exhibitions yet.
    
    Args:
        limit (int): Maximum number of URLs to return.
        
    Returns:
        A JSON string containing URL data for unprocessed URLs.
    """
    try:
        db = await get_db_manager()
        urls = await db.get_urls_without_exhibitions()
        
        # Limit results and format for agent consumption
        limited_urls = urls[:limit]
        
        result_data = []
        for url in limited_urls:
            result_data.append({
                "id": url.id,
                "url": url.url,
                "raw_title": url.raw_title,
                "raw_date": url.raw_date,
                "raw_location": url.raw_location,
            })
        return json.dumps(result_data, indent=2)
        
    except Exception as e:
        return f"ERROR: Failed to get unprocessed URLs: {str(e)}"

@tool
def describe_schema(table_name: str) -> str:
    """
    Describes table schema using a direct, synchronous SQLAlchemy inspector.

    Args:
        table_name (str): Name of the table ("exhibitions", "entry_fees", "prizes", "urls").

    Returns:
        A string containing the table schema with column names and types, or an error message if the operation fails.
    """
    try:
        from sqlalchemy import create_engine, inspect
        engine = create_engine("sqlite:///art_events.db")
        inspector = inspect(engine)
        
        table_names = inspector.get_table_names()
        
        if table_name not in table_names:
            return f"ERROR: no table named '{table_name}'. Available: {table_names}"
        
        cols = inspector.get_columns(table_name)
        lines = [f"{c['name']}: {c['type']}" for c in cols]
        return "\n".join(lines)
        
    except Exception as e:
        return f"ERROR: Failed to describe schema: {str(e)}"
    
@tool
async def get_exhibition_stats_async() -> str:
    """
    Get statistics about the current database state.
    
    Args:
        None.
        
    Returns:
        A JSON string containing statistics about exhibitions, fees, and prizes.
    """
    try:
        db = await get_db_manager()
        
        async with db.get_session() as session:
            from sqlalchemy import func, select
            from models.models import Exhibition, EntryFee, Prize, Url
            
            # Count exhibitions
            result = await session.execute(select(func.count(Exhibition.id)))
            exhibition_count = result.scalar()
            
            # Count URLs
            result = await session.execute(select(func.count(Url.id)))
            url_count = result.scalar()
            
            # Count entry fees
            result = await session.execute(select(func.count(EntryFee.id)))
            fee_count = result.scalar()
            
            # Count prizes  
            result = await session.execute(select(func.count(Prize.id)))
            prize_count = result.scalar()
            
            # Get date range
            result = await session.execute(
                select(func.min(Exhibition.date_start), func.max(Exhibition.date_end))
            )
            date_range = result.first()
            
            # Safely extract date values
            earliest_date = None
            latest_date = None
            if date_range:
                earliest_date = str(date_range[0]) if date_range[0] else None
                latest_date = str(date_range[1]) if date_range[1] else None
            
            stats = {
                "total_urls": url_count,
                "total_exhibitions": exhibition_count,
                "total_entry_fees": fee_count,
                "total_prizes": prize_count,
                "date_range": {
                "earliest": earliest_date,
                "latest": latest_date,
                }
            }
            
            import json
            return json.dumps(stats, indent=2)
            
    except Exception as e:
        return f"ERROR: Failed to get statistics: {str(e)}"


# Synchronous wrappers for compatibility with existing code
@tool 
def add_url(
    url: str,
    raw_title: str | None = None,
    raw_date: str | None = None,
    raw_location: str | None = None,
    raw_description: str | None = None,
) -> int:
    """
    Insert a row in the **urls** table (synchronous wrapper).
    
    Args:
        url (str): The absolute URL of the page that advertised the open call.
        raw_title (str | None): Optional raw title text scraped from the page.
        raw_date (str | None): Optional raw date string scraped from the page.
        raw_location (str | None): Optional raw location string scraped from the page.
        raw_description (str | None): Optional teaser / summary text scraped from the page.
        
    Returns:
        An integer representing the primary‑key ID of the newly‑inserted or existing Url row.
    """
    import asyncio
    return asyncio.run(add_url_async(url, raw_title, raw_date, raw_location, raw_description))


@tool
def add_exhibition(
    *,
    title: str,
    date_start: str,
    date_end: str,
    venue: str,
    location: str,
    county: str | None,
    url_id: int,
    description: str | None = None,
) -> int:
    """
    Insert a row in the **exhibitions** table (synchronous wrapper).
    
    Args:
        title (str): Official exhibition title.
        date_start (str): First public day of the exhibition (YYYY‑MM‑DD).
        date_end (str): Last public day of the exhibition (YYYY‑MM‑DD).
        venue (str): Gallery / art‑fair name.
        location (str): Town or city where the venue is located.
        county (str | None): Optional county / region for more granular search.
        url_id (int): Foreign‑key linking back to the **urls** table.
        description (str | None): Optional long‑form description scraped from the page.
        
    Returns:
        An integer representing the ID of the new Exhibition row.
    """
    import asyncio
    return asyncio.run(add_exhibition_async(
        title=title,
        date_start=date_start,
        date_end=date_end,
        venue=venue,
        location=location,
        county=county,
        url_id=url_id,
        description=description,
    ))


@tool
def add_entry_fee(
    exhibition_id: int,
    number_entries: int,
    fee_amount: str,
    flat_rate: str | None = None,
    commission_percent: str | None = None,
) -> int:
    """
    Insert a row in the **entry_fees** table (synchronous wrapper).
    
    Args:
        exhibition_id (int): Foreign‑key to the parent exhibition.
        number_entries (int): The exact number of works this tier applies to.
        fee_amount (str): Monetary fee per tier (e.g. "25.00").
        flat_rate (str | None): Optional flat fee that overrides per‑piece tiers.
        commission_percent (str | None): Optional commission percentage charged on sales.
        
    Returns:
        An integer representing the ID of the new EntryFee row.
    """
    import asyncio
    return asyncio.run(add_entry_fee_async(
        exhibition_id, number_entries, fee_amount, flat_rate, commission_percent
    ))


@tool
def add_prize(
    exhibition_id: int,
    prize_rank: int | None = None,
    prize_amount: str | None = None,
    prize_type: str | None = None,
    prize_description: str | None = None,
) -> int:
    """
    Insert a row in the **prizes** table (synchronous wrapper).
    
    Args:
        exhibition_id (int): Foreign‑key to the parent exhibition.
        prize_rank (int | None): Ordinal rank (e.g. 1 for first prize). None if unranked.
        prize_amount (str | None): Cash value ("5000.00") or None for non‑cash awards.
        prize_type (str | None): Short label for the prize type (e.g. "cash", "materials").
        prize_description (str | None): Longer human‑readable description.
        
    Returns:
        An integer representing the ID of the new Prize row.
    """
    import asyncio
    return asyncio.run(add_prize_async(
        exhibition_id, prize_rank, prize_amount, prize_type, prize_description
    ))


@tool
def get_unprocessed_urls(limit: int = 50) -> str:
    """
    Get URLs that haven't been processed into exhibitions yet (synchronous wrapper).
    
    Args:
        limit (int): Maximum number of URLs to return.
        
    Returns:
        A JSON string containing URL data for unprocessed URLs.
    """
    import asyncio
    return asyncio.run(get_unprocessed_urls_async(limit))


@tool
def get_exhibition_stats() -> str:
    """
    Get statistics about the current database state (synchronous wrapper).
    
    Args:
        None.
        
    Returns:
        A JSON string containing statistics about exhibitions, fees, and prizes.
    """
    import asyncio
    return asyncio.run(get_exhibition_stats_async())


# ───────────────────────── ENHANCED HELPER FUNCTIONS ─────────────────────────


@tool
async def bulk_insert_exhibitions_async(exhibitions_data_json: str) -> str:
    """
    Bulk insert multiple exhibitions for better performance.
    
    Args:
        exhibitions_data_json: JSON string containing list of exhibition data dictionaries.
                              Each dict should contain all required Exhibition fields.
    
    Returns:
        A JSON string containing the results of the bulk insertion with exhibition IDs.
    """
    try:
        import json
        exhibitions_data = json.loads(exhibitions_data_json)
        
        db = await get_db_manager()
        results = await db.bulk_insert_exhibitions(exhibitions_data)
        
        result_data = []
        for exhibition in results:
            result_data.append({
                "id": exhibition.id,
                "title": exhibition.title,
                "date_start": str(exhibition.date_start),
                "date_end": str(exhibition.date_end),
                "venue": exhibition.venue,
                "location": exhibition.location
            })
        
        return json.dumps({
            "success": True,
            "count": len(result_data),
            "exhibitions": result_data
        }, indent=2)
        
    except Exception as e:
        import json
        return json.dumps({
            "success": False,
            "error": str(e),
            "count": 0,
            "exhibitions": []
        }, indent=2)


@tool
async def get_exhibitions_by_criteria_async(
    date_range_json: str | None = None,
    location: str | None = None,
    fee_range_json: str | None = None
) -> str:
    """
    Query exhibitions by multiple criteria with advanced filtering.
    
    Args:
        date_range_json: JSON string containing start and end dates: '["2023-01-01", "2024-12-31"]'
        location: Location string to search for (case-insensitive)
        fee_range_json: JSON string containing min and max fees: '[10.0, 100.0]'
    
    Returns:
        A JSON string containing exhibitions matching the criteria.
    """
    try:
        import json
        
        # Parse optional parameters
        date_range = None
        if date_range_json:
            date_range = tuple(json.loads(date_range_json))
        
        fee_range = None
        if fee_range_json:
            fee_range = tuple(json.loads(fee_range_json))
        
        db = await get_db_manager()
        exhibitions = await db.get_exhibitions_by_criteria(
            date_range=date_range,
            location=location,
            fee_range=fee_range
        )
        
        result_data = []
        for exhibition in exhibitions:
            exhibition_data = {
                "id": exhibition.id,
                "title": exhibition.title,
                "date_start": str(exhibition.date_start),
                "date_end": str(exhibition.date_end),
                "venue": exhibition.venue,
                "location": exhibition.location,
                "county": exhibition.county,
                "description": exhibition.description,
                "entry_fees": [],
                "prizes": []
            }
            
            # Add entry fees if loaded
            for fee in exhibition.entry_fees:
                exhibition_data["entry_fees"].append({
                    "id": fee.id,
                    "number_entries": fee.number_entries,
                    "fee_amount": float(fee.fee_amount) if fee.fee_amount else None,
                    "fee_type": fee.fee_type,
                    "commission_percent": float(fee.commission_percent) if fee.commission_percent else None
                })
            
            # Add prizes if loaded
            for prize in exhibition.prizes:
                exhibition_data["prizes"].append({
                    "id": prize.id,
                    "prize_rank": prize.prize_rank,
                    "prize_amount": float(prize.prize_amount) if prize.prize_amount else None,
                    "prize_type": prize.prize_type,
                    "prize_description": prize.prize_description
                })
            
            result_data.append(exhibition_data)
        
        return json.dumps({
            "success": True,
            "count": len(result_data),
            "exhibitions": result_data
        }, indent=2)
        
    except Exception as e:
        import json
        return json.dumps({
            "success": False,
            "error": str(e),
            "count": 0,
            "exhibitions": []
        }, indent=2)


@tool
async def generate_fee_analysis_report_async() -> str:
    """
    Generate comprehensive fee analysis report with statistics.
    
    Returns:
        A JSON string containing detailed fee analysis with statistics and insights.
    """
    try:
        db = await get_db_manager()
        report = await db.generate_fee_analysis_report()
        
        import json
        return json.dumps(report, indent=2)
        
    except Exception as e:
        import json
        return json.dumps({
            "success": False,
            "error": str(e),
            "summary": {},
            "tier_distribution": [],
            "commission_analysis": {},
            "fee_types": {}
        }, indent=2)


@tool 
async def cleanup_duplicate_entries_async() -> str:
    """
    Clean up duplicate entries in the database.
    
    Returns:
        A JSON string containing cleanup statistics.
    """
    try:
        db = await get_db_manager()
        cleanup_stats = await db.cleanup_duplicate_entries()
        
        import json
        return json.dumps({
            "success": True,
            "cleanup_stats": cleanup_stats
        }, indent=2)
        
    except Exception as e:
        import json
        return json.dumps({
            "success": False,
            "error": str(e),
            "cleanup_stats": {
                "duplicate_urls_removed": 0,
                "duplicate_exhibitions_removed": 0,
                "duplicate_entry_fees_removed": 0,
                "duplicate_prizes_removed": 0
            }
        }, indent=2)


@tool
async def add_database_indexes_async() -> str:
    """
    Add database indexes for query optimization.
    
    Returns:
        A JSON string containing indexing results.
    """
    try:
        db = await get_db_manager()
        index_results = await db.add_database_indexes()
        
        import json
        return json.dumps({
            "success": True,
            "index_results": index_results
        }, indent=2)
        
    except Exception as e:
        import json
        return json.dumps({
            "success": False,
            "error": str(e),
            "index_results": {
                "indexes_created": [],
                "indexes_already_exist": [],
                "errors": [str(e)]
            }
        }, indent=2)


# ───────────────────────── SYNCHRONOUS WRAPPERS FOR NEW FUNCTIONS ─────────────────────────


@tool
def bulk_insert_exhibitions(exhibitions_data_json: str) -> str:
    """
    Bulk insert multiple exhibitions for better performance (synchronous wrapper).
    
    Args:
        exhibitions_data_json: JSON string containing list of exhibition data dictionaries.
    
    Returns:
        A JSON string containing the results of the bulk insertion with exhibition IDs.
    """
    import asyncio
    import concurrent.futures
    import threading
    
    def run_in_thread():
        """Run the async function in a new thread with its own event loop."""
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(bulk_insert_exhibitions_async(exhibitions_data_json))
        finally:
            new_loop.close()
    
    try:
        # Check if we're in an async context
        loop = asyncio.get_running_loop()
        # If we get here, we're in an async context, so run in a separate thread
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result()
    except RuntimeError:
        # No running loop, safe to use asyncio.run
        return asyncio.run(bulk_insert_exhibitions_async(exhibitions_data_json))


@tool
def get_exhibitions_by_criteria(
    date_range_json: str | None = None,
    location: str | None = None,
    fee_range_json: str | None = None
) -> str:
    """
    Query exhibitions by multiple criteria with advanced filtering (synchronous wrapper).
    
    Args:
        date_range_json: JSON string containing start and end dates: '["2023-01-01", "2024-12-31"]'
        location: Location string to search for (case-insensitive)
        fee_range_json: JSON string containing min and max fees: '[10.0, 100.0]'
    
    Returns:
        A JSON string containing exhibitions matching the criteria.
    """
    import asyncio
    import concurrent.futures
    
    def run_in_thread():
        """Run the async function in a new thread with its own event loop."""
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(get_exhibitions_by_criteria_async(date_range_json, location, fee_range_json))
        finally:
            new_loop.close()
    
    try:
        # Check if we're in an async context
        loop = asyncio.get_running_loop()
        # If we get here, we're in an async context, so run in a separate thread
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result()
    except RuntimeError:
        # No running loop, safe to use asyncio.run
        return asyncio.run(get_exhibitions_by_criteria_async(date_range_json, location, fee_range_json))


@tool
def generate_fee_analysis_report() -> str:
    """
    Generate comprehensive fee analysis report with statistics (synchronous wrapper).
    
    Returns:
        A JSON string containing detailed fee analysis with statistics and insights.
    """
    import asyncio
    import concurrent.futures
    
    def run_in_thread():
        """Run the async function in a new thread with its own event loop."""
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(generate_fee_analysis_report_async())
        finally:
            new_loop.close()
    
    try:
        # Check if we're in an async context
        loop = asyncio.get_running_loop()
        # If we get here, we're in an async context, so run in a separate thread
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result()
    except RuntimeError:
        # No running loop, safe to use asyncio.run
        return asyncio.run(generate_fee_analysis_report_async())


@tool
def cleanup_duplicate_entries() -> str:
    """
    Clean up duplicate entries in the database (synchronous wrapper).
    
    Returns:
        A JSON string containing cleanup statistics.
    """
    import asyncio
    import concurrent.futures
    
    def run_in_thread():
        """Run the async function in a new thread with its own event loop."""
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(cleanup_duplicate_entries_async())
        finally:
            new_loop.close()
    
    try:
        # Check if we're in an async context
        loop = asyncio.get_running_loop()
        # If we get here, we're in an async context, so run in a separate thread
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result()
    except RuntimeError:
        # No running loop, safe to use asyncio.run
        return asyncio.run(cleanup_duplicate_entries_async())


@tool
def add_database_indexes() -> str:
    """
    Add database indexes for query optimization (synchronous wrapper).
    
    Returns:
        A JSON string containing indexing results.
    """
    import asyncio
    import concurrent.futures
    
    def run_in_thread():
        """Run the async function in a new thread with its own event loop."""
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(add_database_indexes_async())
        finally:
            new_loop.close()
    
    try:
        # Check if we're in an async context
        loop = asyncio.get_running_loop()
        # If we get here, we're in an async context, so run in a separate thread
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result()
    except RuntimeError:
        # No running loop, safe to use asyncio.run
        return asyncio.run(add_database_indexes_async())
