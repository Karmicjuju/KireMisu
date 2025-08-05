"""Simple database utilities for common operations."""

import asyncio
import logging
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, AsyncGenerator, Callable, List, Optional

from sqlalchemy import text
from sqlalchemy.exc import DisconnectionError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from .connection import get_db_session

logger = logging.getLogger(__name__)


async def check_db_health() -> bool:
    """Simple database health check."""
    try:
        async with get_db_session() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def with_db_retry(max_attempts: int = 3, delay: float = 1.0):
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
    """Safe delete with error handling."""
    try:
        await session.delete(item)
        await session.flush()
        return True
    except SQLAlchemyError as e:
        logger.error(f"Delete failed: {e}")
        return False


def log_slow_query(query_name: str, duration_threshold: float = 1.0):
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
    """Simple parameter validation to prevent basic SQL injection."""
    cleaned_params = {}
    
    for key, value in params.items():
        if value is None:
            cleaned_params[key] = None
            continue
        
        if isinstance(value, str):
            # Basic SQL injection prevention - check for dangerous patterns
            dangerous_patterns = ["'", '"', ";", "--", "/*", "*/", "xp_", "sp_", "drop ", "delete ", "truncate "]
            value_lower = value.lower()
            
            if any(pattern in value_lower for pattern in dangerous_patterns):
                raise ValueError(f"Potentially unsafe parameter '{key}': contains dangerous pattern")
            
            # Limit string length to prevent DoS
            if len(value) > 1000:
                raise ValueError(f"Parameter '{key}' too long (max 1000 characters)")
                
            cleaned_params[key] = value.strip()
        elif isinstance(value, (int, float, bool)):
            cleaned_params[key] = value
        elif isinstance(value, list):
            # Validate each item in list
            if len(value) > 100:  # Prevent huge lists
                raise ValueError(f"Parameter '{key}' list too long (max 100 items)")
            cleaned_params[key] = [validate_query_params(item=item)["item"] for item in value]
        else:
            cleaned_params[key] = value
    
    return cleaned_params


def safe_like_pattern(search_term: str) -> str:
    """Create a safe LIKE pattern from user input."""
    if not search_term:
        return "%"
    
    # Escape special LIKE characters
    escaped = search_term.replace("%", "\\%").replace("_", "\\_")
    
    # Basic validation
    if len(escaped) > 100:
        raise ValueError("Search term too long")
    
    return f"%{escaped}%"