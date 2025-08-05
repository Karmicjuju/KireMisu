"""Simple database utilities for common operations."""

import asyncio
import logging
import re
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, AsyncGenerator, Callable, List, Optional

from sqlalchemy import text
from sqlalchemy.exc import DisconnectionError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from .connection import get_db_session
from .config import db_config

logger = logging.getLogger(__name__)


async def check_db_health() -> bool:
    """Simple database health check with timeout protection."""
    try:
        # Use asyncio.wait_for to prevent hanging connections
        async with asyncio.timeout(db_config.HEALTH_CHECK_TIMEOUT):
            async with get_db_session() as session:
                await session.execute(text("SELECT 1"))
                return True
    except asyncio.TimeoutError:
        logger.error("Database health check timed out")
        return False
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def with_db_retry(
    max_attempts: int = db_config.DEFAULT_MAX_ATTEMPTS, 
    delay: float = db_config.DEFAULT_RETRY_DELAY
):
    """Simple retry decorator for database operations."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except (DisconnectionError, OperationalError) as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        logger.warning(f"Database operation failed (attempt {attempt + 1}), retrying: {e}")
                        await asyncio.sleep(delay * (attempt + 1))
                    else:
                        logger.error(f"Database operation failed after {max_attempts} attempts: {e}")
                        raise
                except Exception as e:
                    # Don't retry other types of errors
                    logger.error(f"Database operation failed with non-retryable error: {e}")
                    raise
            
            raise last_error
        return wrapper
    return decorator


@asynccontextmanager
async def db_transaction() -> AsyncGenerator[AsyncSession, None]:
    """Simple transaction context manager with proper error handling."""
    async with get_db_session() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Transaction rolled back due to error: {e}")
            raise


async def bulk_create(session: AsyncSession, items: List[Any]) -> None:
    """Simple bulk insert helper."""
    if not items:
        return
    
    try:
        session.add_all(items)
        await session.flush()
        logger.info(f"Bulk created {len(items)} items")
    except SQLAlchemyError as e:
        logger.error(f"Bulk create failed: {e}")
        raise


async def safe_delete(session: AsyncSession, item: Any) -> bool:
    """Safe delete with comprehensive error handling and validation."""
    if item is None:
        logger.warning("Attempted to delete None item")
        return False
    
    try:
        # Check if item is already in the session
        if item not in session:
            logger.warning("Item not found in session for deletion")
            return False
            
        session.delete(item)
        await session.flush()
        logger.debug(f"Successfully deleted item: {type(item).__name__}")
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Delete failed for {type(item).__name__}: {e}")
        # Attempt to rollback the session state
        try:
            await session.rollback()
        except Exception as rollback_error:
            logger.error(f"Failed to rollback after delete error: {rollback_error}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during delete: {e}")
        return False


def log_slow_query(query_name: str, duration_threshold: float = db_config.DEFAULT_SLOW_QUERY_THRESHOLD):
    """Decorator to log slow queries."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                if duration > duration_threshold:
                    logger.warning(f"Slow query detected: {query_name} took {duration:.2f}s")
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Query failed: {query_name} after {duration:.2f}s - {e}")
                raise
        return wrapper
    return decorator


def validate_query_params(**params) -> dict:
    """Enhanced parameter validation with comprehensive SQL injection protection."""
    cleaned_params = {}
    
    for key, value in params.items():
        if value is None:
            cleaned_params[key] = None
            continue
        
        if isinstance(value, str):
            # Enhanced SQL injection prevention with case-insensitive matching
            value_lower = value.lower()
            
            # Check for dangerous SQL patterns
            for pattern in db_config.DANGEROUS_SQL_PATTERNS:
                if pattern.lower() in value_lower:
                    raise ValueError(
                        f"Potentially unsafe parameter '{key}': contains SQL injection pattern '{pattern}'"
                    )
            
            # Additional regex-based checks for complex injection patterns
            suspicious_patterns = [
                r'\b(union\s+select)\b',  # Union-based injections
                r'\b(or\s+\d+\s*=\s*\d+)\b',  # Boolean-based injections
                r'\b(and\s+\d+\s*=\s*\d+)\b',  # Boolean-based injections
                r'[\'"]\s*;\s*\w+',  # Command chaining
                r'0x[0-9a-f]+',  # Hexadecimal values
                r'\\x[0-9a-f]{2}',  # Hex encoded characters (fixed escape)
            ]
            
            for pattern in suspicious_patterns:
                if re.search(pattern, value_lower, re.IGNORECASE):
                    raise ValueError(
                        f"Potentially unsafe parameter '{key}': matches suspicious pattern"
                    )
            
            # Limit string length to prevent DoS
            if len(value) > db_config.MAX_STRING_LENGTH:
                raise ValueError(
                    f"Parameter '{key}' too long (max {db_config.MAX_STRING_LENGTH} characters)"
                )
                
            # Check for excessive whitespace (potential obfuscation)
            if len(value.strip()) != len(value) and len(value) - len(value.strip()) > 10:
                raise ValueError(f"Parameter '{key}' contains excessive whitespace")
                
            cleaned_params[key] = value.strip()
            
        elif isinstance(value, (int, float, bool)):
            cleaned_params[key] = value
            
        elif isinstance(value, list):
            # Validate list size and each item
            if len(value) > db_config.MAX_LIST_SIZE:
                raise ValueError(
                    f"Parameter '{key}' list too long (max {db_config.MAX_LIST_SIZE} items)"
                )
            
            # Recursively validate each list item
            cleaned_list = []
            for i, item in enumerate(value):
                try:
                    cleaned_item = validate_query_params(**{f"item_{i}": item})
                    cleaned_list.append(cleaned_item[f"item_{i}"])
                except ValueError as e:
                    raise ValueError(f"Invalid item in list '{key}' at index {i}: {str(e)}")
            
            cleaned_params[key] = cleaned_list
            
        else:
            # For other types, just pass through but log for monitoring
            logger.debug(f"Parameter '{key}' has unusual type: {type(value)}")
            cleaned_params[key] = value
    
    return cleaned_params


def safe_like_pattern(search_term: str) -> str:
    """Create a safe LIKE pattern from user input with enhanced validation."""
    if not search_term:
        return "%"
    
    # First validate the search term using our comprehensive validation
    try:
        validated = validate_query_params(search=search_term)["search"]
    except ValueError as e:
        raise ValueError(f"Invalid search term: {e}")
    
    # Escape special LIKE characters
    escaped = validated.replace("%", "\\%").replace("_", "\\_")
    
    # Length validation using configuration
    if len(escaped) > db_config.MAX_SEARCH_PATTERN_LENGTH:
        raise ValueError(
            f"Search term too long (max {db_config.MAX_SEARCH_PATTERN_LENGTH} characters)"
        )
    
    return f"%{escaped}%"


async def get_connection_info() -> dict:
    """Get database connection information for monitoring."""
    try:
        async with get_db_session() as session:
            # Get database-agnostic connection info
            connection_info = {
                "engine_info": str(session.get_bind()),
                "is_connected": True,
                "pool_info": {},
            }
            
            # Try to get pool information if available
            engine = session.get_bind()
            if hasattr(engine, 'pool'):
                pool = engine.pool
                connection_info["pool_info"] = {
                    "size": getattr(pool, 'size', 'unknown'),
                    "checked_in": getattr(pool, 'checkedin', 'unknown'),
                    "checked_out": getattr(pool, 'checkedout', 'unknown'),
                    "overflow": getattr(pool, 'overflow', 'unknown'),
                    "invalid": getattr(pool, 'invalid', 'unknown'),
                }
            
            return connection_info
            
    except Exception as e:
        logger.error(f"Failed to get connection info: {e}")
        return {
            "is_connected": False,
            "error": str(e),
            "pool_info": {},
        }