"""
Enhanced asynchronous database tools for scalability and performance.
According to SQLAlchemy docs: Use async patterns for modern, I/O-bound applications.
"""
import logging
from decimal import Decimal
from smolagents import tool
from sqlalchemy import inspect
import json

from models.db import AsyncDatabaseManager, async_retry

logger = logging.getLogger(__name__)

# Global database manager
_db_manager = None

async def get_db_manager() -> AsyncDatabaseManager:
    """Get or create the global async database manager."""
    global _db_manager
    if _db_manager is None:
        logger.info("Initializing AsyncDatabaseManager...")
        _db_manager = AsyncDatabaseManager()
        await _db_manager.initialize_database()
        logger.info("Database manager initialized.")
    return _db_manager


@tool
@async_retry(max_retries=3)
async def add_url(url: str, **kwargs) -> int:
    """Insert a row in the **urls** table asynchronously with duplicate detection."""
    logger.info(f"Adding URL to database: {url}")
    try:
        db = await get_db_manager()
        result = await db.add_url(url=url, **kwargs)
        logger.info(f"URL with ID {result.id} added successfully.")
        return result.id
    except Exception as e:
        logger.error(f"Failed to add URL {url}: {e}", exc_info=True)
        raise


@tool
@async_retry(max_retries=3)
async def add_exhibition(**kwargs) -> int:
    """Insert a row in the **exhibitions** table asynchronously."""
    logger.info(f"Adding exhibition to database: {kwargs.get('title')}")
    try:
        from datetime import date
        kwargs['date_start'] = date.fromisoformat(kwargs['date_start'])
        kwargs['date_end'] = date.fromisoformat(kwargs['date_end'])
        if kwargs['date_start'] > kwargs['date_end']:
            raise ValueError("Start date cannot be after end date.")
        
        db = await get_db_manager()
        result = await db.add_exhibition(**kwargs)
        logger.info(f"Exhibition '{kwargs.get('title')}' with ID {result.id} added successfully.")
        return result.id
    except Exception as e:
        logger.error(f"Failed to add exhibition {kwargs.get('title')}: {e}", exc_info=True)
        raise


@tool
@async_retry(max_retries=3)
async def add_entry_fee(**kwargs) -> int:
    """Insert a row in the **entry_fees** table asynchronously with validation."""
    logger.info(f"Adding entry fee for exhibition ID: {kwargs.get('exhibition_id')}")
    try:
        # Simplified validation, assuming db layer handles it
        db = await get_db_manager()
        result = await db.add_entry_fee(**kwargs)
        logger.info(f"Entry fee with ID {result.id} added successfully.")
        return result.id
    except Exception as e:
        logger.error(f"Failed to add entry fee for exhibition {kwargs.get('exhibition_id')}: {e}", exc_info=True)
        raise


@tool
@async_retry(max_retries=3)
async def add_prize(**kwargs) -> int:
    """Insert a row in the **prizes** table asynchronously with validation."""
    logger.info(f"Adding prize for exhibition ID: {kwargs.get('exhibition_id')}")
    try:
        db = await get_db_manager()
        result = await db.add_prize(**kwargs)
        logger.info(f"Prize with ID {result.id} added successfully.")
        return result.id
    except Exception as e:
        logger.error(f"Failed to add prize for exhibition {kwargs.get('exhibition_id')}: {e}", exc_info=True)
        raise


@tool
async def describe_schema(table_name: str) -> str:
    """Return the column names and types for the given table asynchronously."""
    logger.info(f"Describing schema for table: {table_name}")
    try:
        db = await get_db_manager()
        async with db.get_session() as session:
            bind = session.bind
            if bind is None:
                raise ConnectionError("Database connection is not available")
            
            def inspect_table(connection):
                insp = inspect(connection)
                if not insp.has_table(table_name):
                    return f"ERROR: no table named '{table_name}'. Available: {insp.get_table_names()}"
                cols = insp.get_columns(table_name)
                return "\n".join([f"{c['name']}: {c['type']}" for c in cols])
            
            result = await session.connection()
            schema = await result.run_sync(inspect_table)
            logger.info(f"Schema for table '{table_name}' retrieved.")
            return schema
    except Exception as e:
        logger.error(f"Failed to describe schema for {table_name}: {e}", exc_info=True)
        return f"ERROR: Failed to describe schema: {str(e)}"


@tool
async def get_unprocessed_urls(limit: int = 50) -> str:
    """Get URLs that haven't been processed into exhibitions yet."""
    logger.info(f"Fetching {limit} unprocessed URLs...")
    try:
        db = await get_db_manager()
        urls = await db.get_urls_without_exhibitions()
        limited_urls = [{"id": u.id, "url": u.url, "raw_title": u.raw_title} for u in urls[:limit]]
        logger.info(f"Found {len(limited_urls)} unprocessed URLs.")
        return json.dumps(limited_urls, indent=2)
    except Exception as e:
        logger.error(f"Failed to get unprocessed URLs: {e}", exc_info=True)
        return f"ERROR: Failed to get unprocessed URLs: {str(e)}"

    
@tool
async def get_exhibition_stats() -> str:
    """Get statistics about the current database state."""
    logger.info("Fetching exhibition statistics...")
    try:
        db = await get_db_manager()
        stats = await db.get_stats() # Assuming a get_stats method in db manager
        logger.info("Exhibition statistics fetched successfully.")
        return json.dumps(stats, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to get exhibition statistics: {e}", exc_info=True)
        return f"ERROR: Failed to get statistics: {str(e)}"


@tool
async def bulk_insert_exhibitions(exhibitions_data_json: str) -> str:
    """Bulk insert multiple exhibitions for better performance."""
    logger.info("Performing bulk insert of exhibitions...")
    try:
        exhibitions_data = json.loads(exhibitions_data_json)
        db = await get_db_manager()
        results = await db.bulk_insert_exhibitions(exhibitions_data)
        result_data = [{"id": ex.id, "title": ex.title} for ex in results]
        logger.info(f"Bulk inserted {len(result_data)} exhibitions.")
        return json.dumps({"success": True, "count": len(result_data), "exhibitions": result_data}, indent=2)
    except Exception as e:
        logger.error(f"Bulk insert failed: {e}", exc_info=True)
        return json.dumps({"success": False, "error": str(e)}, indent=2)

@tool
async def get_exhibitions_by_criteria(**kwargs) -> str:
    """Query exhibitions by multiple criteria with advanced filtering."""
    logger.info(f"Querying exhibitions with criteria: {kwargs}")
    try:
        db = await get_db_manager()
        exhibitions = await db.get_exhibitions_by_criteria(**kwargs)
        result_data = [ex.to_dict() for ex in exhibitions] # Assuming a to_dict method
        logger.info(f"Found {len(result_data)} exhibitions matching criteria.")
        return json.dumps({"success": True, "count": len(result_data), "exhibitions": result_data}, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to query exhibitions: {e}", exc_info=True)
        return json.dumps({"success": False, "error": str(e)}, indent=2)


@tool
async def generate_fee_analysis_report() -> str:
    """Generate comprehensive fee analysis report with statistics."""
    logger.info("Generating fee analysis report...")
    try:
        db = await get_db_manager()
        report = await db.generate_fee_analysis_report()
        logger.info("Fee analysis report generated successfully.")
        return json.dumps(report, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to generate fee analysis report: {e}", exc_info=True)
        return json.dumps({"success": False, "error": str(e)}, indent=2)


@tool 
async def cleanup_duplicate_entries() -> str:
    """Clean up duplicate entries in the database."""
    logger.info("Cleaning up duplicate entries...")
    try:
        db = await get_db_manager()
        cleanup_stats = await db.cleanup_duplicate_entries()
        logger.info(f"Duplicate entries cleaned up: {cleanup_stats}")
        return json.dumps({"success": True, "cleanup_stats": cleanup_stats}, indent=2)
    except Exception as e:
        logger.error(f"Failed to clean up duplicate entries: {e}", exc_info=True)
        return json.dumps({"success": False, "error": str(e)}, indent=2)


@tool
async def add_database_indexes() -> str:
    """Add database indexes for query optimization."""
    logger.info("Adding database indexes...")
    try:
        db = await get_db_manager()
        index_results = await db.add_database_indexes()
        logger.info(f"Database indexes added: {index_results}")
        return json.dumps({"success": True, "index_results": index_results}, indent=2)
    except Exception as e:
        logger.error(f"Failed to add database indexes: {e}", exc_info=True)
        return json.dumps({"success": False, "error": str(e)}, indent=2)
