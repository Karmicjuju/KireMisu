# Database Layer Improvements

Simple, maintainable database utilities for robust operation.

## Features Added

### 🔧 Enhanced Connection Management
- **Better connection pooling**: Optimized pool size and timeout settings
- **Health checks**: `check_db_health()` for monitoring database connectivity
- **Graceful shutdown**: `close_db_connections()` for clean application shutdown

### 🔄 Retry Logic
- **Simple retry decorator**: `@with_db_retry()` for handling transient failures
- **Configurable**: Set max attempts and delay between retries
- **Smart error handling**: Only retries connection issues, not logic errors

### 🛡️ Security & Validation
- **Parameter validation**: `validate_query_params()` prevents basic SQL injection
- **Safe LIKE patterns**: `safe_like_pattern()` escapes user input for searches
- **Input limits**: Prevents excessively long strings and large lists

### 📈 Performance Utilities
- **Slow query logging**: `@log_slow_query()` decorator tracks performance
- **Bulk operations**: `bulk_create()` for efficient batch inserts
- **Transaction helpers**: `db_transaction()` context manager

### 🔧 Migration Safety
- **Pre-migration checks**: Validate database state before migrations
- **Migration history**: View applied migrations and current state
- **Safety warnings**: Alert about active connections and backup needs

## Usage Examples

### Enhanced Security with SQL Injection Protection
```python
from kiremisu.database import validate_query_params, safe_like_pattern

# Comprehensive input validation in API endpoints
@router.get("/api/search")
async def search_manga(
    query: str,
    author: Optional[str] = None,
    tags: List[str] = Query(default=[])
):
    try:
        # Validate all user inputs with enhanced SQL injection protection
        clean_params = validate_query_params(
            query=query,
            author=author,
            tags=tags
        )
        
        # Create safe search patterns
        search_pattern = safe_like_pattern(clean_params["query"])
        
        # Build query safely
        db_query = select(Series).where(Series.title_primary.ilike(search_pattern))
        
        if clean_params["author"]:
            author_pattern = safe_like_pattern(clean_params["author"])
            db_query = db_query.where(Series.author.ilike(author_pattern))
            
    except ValueError as e:
        # Detailed error reporting for security violations
        logger.warning(f"Invalid input detected: {e}")
        raise HTTPException(status_code=400, detail="Invalid search parameters")
```

### Advanced Retry Patterns with Configuration
```python
from kiremisu.database import with_db_retry, db_config

# Use configuration constants for consistency
@with_db_retry(
    max_attempts=db_config.CONNECTION_RETRY_ATTEMPTS,
    delay=db_config.CONNECTION_RETRY_DELAY
)
async def critical_database_operation(db: AsyncSession):
    # Critical operations with robust retry logic
    return await db.execute(complex_query)

# Custom retry for read-only operations
@with_db_retry(max_attempts=5, delay=0.5)
async def read_heavy_operation(db: AsyncSession):
    return await db.execute(analytical_query)
```

### Transaction Management
```python
from kiremisu.database import db_transaction

async def update_series_with_chapters(series_data, chapters_data):
    async with db_transaction() as db:
        # All operations in this block are wrapped in a transaction
        series = Series(**series_data)
        db.add(series)
        await db.flush()  # Get the series ID
        
        chapters = [Chapter(series_id=series.id, **ch) for ch in chapters_data]
        await bulk_create(db, chapters)
        # Automatic commit on success, rollback on error
```

### Performance Monitoring and Connection Management
```python
from kiremisu.database import log_slow_query, get_connection_info, db_config

# Monitoring slow queries with configurable thresholds
@log_slow_query("complex_series_query", threshold=db_config.DEFAULT_SLOW_QUERY_THRESHOLD)
async def get_series_with_complex_filters(db: AsyncSession, filters: dict):
    # This will log if the query takes longer than configured threshold
    return await db.execute(complex_query)

# Database connection monitoring
async def monitor_database_health():
    """Monitor database connection status and pool information."""
    health_status = await check_db_health()
    connection_info = await get_connection_info()
    
    return {
        "healthy": health_status,
        "connection_details": connection_info,
        "pool_usage": connection_info.get("pool_info", {}),
    }

# Resource monitoring for production
async def check_database_resources():
    """Check database resource utilization."""
    info = await get_connection_info()
    
    if info.get("is_connected"):
        pool_info = info.get("pool_info", {})
        checked_out = pool_info.get("checked_out", 0)
        size = pool_info.get("size", 10)
        
        if isinstance(checked_out, int) and isinstance(size, int):
            utilization = (checked_out / size) * 100
            
            if utilization > 80:
                logger.warning(f"High database connection utilization: {utilization}%")
                
            return {"utilization_percent": utilization, "available_connections": size - checked_out}
    
    return {"error": "Unable to determine resource usage"}
```

## Migration Helpers

### Check Migration Safety
```python
from kiremisu.database.migrations import validate_migration_safety

checks = await validate_migration_safety()
if not checks["database_accessible"]:
    print("Cannot run migration: database not accessible")
```

### View Migration History
```python
from kiremisu.database.migrations import get_migration_history

history = await get_migration_history()
for migration in history:
    status = "CURRENT" if migration["is_current"] else "APPLIED"
    print(f"{status}: {migration['revision']} - {migration['description']}")
```

## Configuration System

The database utilities now use a centralized configuration system for consistency and maintainability:

```python
from kiremisu.database import db_config

# All configuration constants are centralized
print(f"Max string length: {db_config.MAX_STRING_LENGTH}")
print(f"Max list size: {db_config.MAX_LIST_SIZE}") 
print(f"Default retry attempts: {db_config.DEFAULT_MAX_ATTEMPTS}")
print(f"Health check timeout: {db_config.HEALTH_CHECK_TIMEOUT}")

# Dangerous SQL patterns are comprehensively defined
print(f"Monitored patterns: {len(db_config.DANGEROUS_SQL_PATTERNS)} patterns")
```

### Customizing Configuration

```python
# For testing or special environments, you can modify configuration
db_config.MAX_STRING_LENGTH = 2000  # Increase for special use cases
db_config.DEFAULT_SLOW_QUERY_THRESHOLD = 0.5  # More sensitive monitoring

# Security patterns can be extended if needed
additional_patterns = ["custom_function", "special_keyword"]
db_config.DANGEROUS_SQL_PATTERNS = (*db_config.DANGEROUS_SQL_PATTERNS, *additional_patterns)
```

## Applied to Existing Code

The `series.py` API has been updated to demonstrate these patterns:

```python
@router.get("/", response_model=List[SeriesResponse])
@with_db_retry(max_attempts=2)  # Retry connection failures
@log_slow_query("get_series_list", 2.0)  # Log slow queries
async def get_series_list(
    search: Optional[str] = Query(None),
    # ... other params
):
    # Validate and clean user input
    try:
        clean_params = validate_query_params(search=search)
        search = clean_params.get("search")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Use safe LIKE pattern for search
    if search:
        search_term = safe_like_pattern(search)
        query = query.where(Series.title_primary.ilike(search_term))
```

## Design Philosophy

These utilities follow the principle of **simple, maintainable solutions**:

- ✅ **Easy to understand**: Clear function names and straightforward logic
- ✅ **Easy to test**: Simple functions with predictable behavior
- ✅ **Easy to maintain**: Minimal dependencies and clear separation of concerns
- ✅ **Production ready**: Handles real-world edge cases and errors
- ✅ **Gradual adoption**: Can be applied incrementally to existing code

## Advanced Usage Patterns

### Building Secure Search APIs

```python
from kiremisu.database import validate_query_params, safe_like_pattern, with_db_retry
from kiremisu.database.models import Series, Chapter
from sqlalchemy import select, and_, or_

@router.get("/api/advanced-search")
@with_db_retry(max_attempts=3)
async def advanced_search(
    db: AsyncSession,
    title: Optional[str] = None,
    author: Optional[str] = None,
    year_range: Optional[str] = None,  # Format: "2020-2023"
    tags: List[str] = Query(default=[]),
    status: Optional[str] = None,
    limit: int = Query(50, le=100)
):
    """Advanced search with comprehensive input validation and security."""
    try:
        # Validate all user inputs with enhanced security
        clean_params = validate_query_params(
            title=title,
            author=author,
            year_range=year_range,
            tags=tags,
            status=status,
            limit=limit
        )
        
        # Build base query
        query = select(Series)
        conditions = []
        
        # Add title search with safe pattern
        if clean_params.get("title"):
            title_pattern = safe_like_pattern(clean_params["title"])
            conditions.append(Series.title_primary.ilike(title_pattern))
        
        # Add author search with safe pattern  
        if clean_params.get("author"):
            author_pattern = safe_like_pattern(clean_params["author"])
            conditions.append(Series.author.ilike(author_pattern))
            
        # Parse and validate year range
        if clean_params.get("year_range"):
            try:
                start_year, end_year = clean_params["year_range"].split("-")
                start_year, end_year = int(start_year), int(end_year)
                if start_year > end_year or start_year < 1900 or end_year > 2100:
                    raise ValueError("Invalid year range")
                conditions.append(and_(
                    Series.publication_year >= start_year,
                    Series.publication_year <= end_year
                ))
            except (ValueError, IndexError):
                raise HTTPException(status_code=400, detail="Invalid year range format")
        
        # Add tag filtering (requires junction table)
        if clean_params.get("tags"):
            # Assuming a many-to-many relationship with tags
            tag_conditions = [Series.tags.any(name=tag) for tag in clean_params["tags"]]
            conditions.append(or_(*tag_conditions))
        
        # Add status filtering with enum validation
        if clean_params.get("status"):
            valid_statuses = ["ongoing", "completed", "hiatus", "cancelled"]
            if clean_params["status"] not in valid_statuses:
                raise HTTPException(status_code=400, detail="Invalid status value")
            conditions.append(Series.status == clean_params["status"])
            
        # Apply all conditions
        if conditions:
            query = query.where(and_(*conditions))
            
        # Apply limit with validation
        query = query.limit(min(clean_params["limit"], 100))
        
        # Execute with error handling
        result = await db.execute(query)
        series_list = result.scalars().all()
        
        return {
            "results": series_list,
            "count": len(series_list),
            "search_params": clean_params
        }
        
    except ValueError as e:
        logger.warning(f"Search validation failed: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid search parameters: {e}")
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail="Search operation failed")
```

### Batch Processing with Enhanced Error Handling

```python
from kiremisu.database import db_transaction, bulk_create, safe_delete, log_slow_query
from kiremisu.database.models import Series, Chapter
import asyncio

@log_slow_query("batch_import_series", threshold=5.0)
async def batch_import_series_with_chapters(import_data: List[dict]) -> dict:
    """Batch import series with chapters using enhanced safety mechanisms."""
    results = {
        "successful": 0, 
        "failed": 0, 
        "errors": []
    }
    
    # Validate all input data first
    validated_data = []
    for i, series_data in enumerate(import_data):
        try:
            # Validate series metadata
            series_params = validate_query_params(
                title=series_data.get("title"),
                author=series_data.get("author"),
                description=series_data.get("description", ""),
                file_path=series_data.get("file_path")
            )
            
            # Validate chapter data if present
            chapter_list = []
            if "chapters" in series_data:
                for chapter_data in series_data["chapters"]:
                    chapter_params = validate_query_params(
                        title=chapter_data.get("title"),
                        file_path=chapter_data.get("file_path"),
                        chapter_number=chapter_data.get("chapter_number")
                    )
                    chapter_list.append(chapter_params)
            
            validated_data.append({
                "series": series_params,
                "chapters": chapter_list,
                "original_index": i
            })
            
        except ValueError as e:
            results["failed"] += 1
            results["errors"].append({
                "index": i,
                "error": f"Validation failed: {e}",
                "data": series_data.get("title", "Unknown")
            })
    
    # Process validated data in transaction
    async with db_transaction() as db:
        for item in validated_data:
            try:
                # Create series
                series = Series(**item["series"])
                db.add(series)
                await db.flush()  # Get the series ID
                
                # Create chapters if present
                if item["chapters"]:
                    chapters = [
                        Chapter(series_id=series.id, **ch_data)
                        for ch_data in item["chapters"]
                    ]
                    await bulk_create(db, chapters)
                
                results["successful"] += 1
                
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "index": item["original_index"],
                    "error": f"Database error: {e}",
                    "series": item["series"].get("title", "Unknown")
                })
                # Transaction will rollback automatically
                raise
    
    logger.info(f"Batch import completed: {results['successful']} successful, {results['failed']} failed")
    return results
```

### Production Health Monitoring

```python
from kiremisu.database import check_db_health, get_connection_info, db_config
from datetime import datetime, timedelta
import asyncio

class DatabaseHealthMonitor:
    """Production-ready database health monitoring system."""
    
    def __init__(self):
        self.health_history = []
        self.alert_thresholds = {
            "connection_utilization": 80,  # %
            "failed_health_checks": 3,     # consecutive failures
            "slow_response_time": 2.0       # seconds
        }
    
    async def comprehensive_health_check(self) -> dict:
        """Perform comprehensive database health assessment."""
        start_time = asyncio.get_event_loop().time()
        
        # Basic connectivity check
        is_healthy = await check_db_health()
        response_time = asyncio.get_event_loop().time() - start_time
        
        # Get detailed connection information
        connection_info = await get_connection_info()
        
        # Calculate connection utilization
        utilization = 0
        if connection_info.get("is_connected"):
            pool_info = connection_info.get("pool_info", {})
            checked_out = pool_info.get("checked_out", 0)
            size = pool_info.get("size", 10)
            
            if isinstance(checked_out, int) and isinstance(size, int) and size > 0:
                utilization = (checked_out / size) * 100
        
        # Assess overall health status
        health_status = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_healthy": is_healthy,
            "response_time_seconds": round(response_time, 3),
            "connection_utilization_percent": round(utilization, 1),
            "connection_details": connection_info,
            "configuration": {
                "max_string_length": db_config.MAX_STRING_LENGTH,
                "max_list_size": db_config.MAX_LIST_SIZE,
                "health_check_timeout": db_config.HEALTH_CHECK_TIMEOUT,
                "default_retry_attempts": db_config.DEFAULT_MAX_ATTEMPTS
            },
            "alerts": []
        }
        
        # Generate alerts based on thresholds
        if utilization > self.alert_thresholds["connection_utilization"]:
            health_status["alerts"].append({
                "level": "WARNING",
                "message": f"High connection utilization: {utilization:.1f}%"
            })
            
        if response_time > self.alert_thresholds["slow_response_time"]:
            health_status["alerts"].append({
                "level": "WARNING", 
                "message": f"Slow database response: {response_time:.2f}s"
            })
            
        if not is_healthy:
            health_status["alerts"].append({
                "level": "CRITICAL",
                "message": "Database connectivity check failed"
            })
        
        # Store in history for trend analysis
        self.health_history.append(health_status)
        
        # Keep only last 100 entries
        if len(self.health_history) > 100:
            self.health_history = self.health_history[-100:]
            
        return health_status
    
    async def get_health_trends(self, hours: int = 24) -> dict:
        """Analyze health trends over specified time period."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        recent_checks = [
            check for check in self.health_history
            if datetime.fromisoformat(check["timestamp"]) > cutoff_time
        ]
        
        if not recent_checks:
            return {"message": "No recent health data available"}
        
        # Calculate statistics
        response_times = [check["response_time_seconds"] for check in recent_checks]
        utilization_values = [check["connection_utilization_percent"] for check in recent_checks]
        failed_checks = sum(1 for check in recent_checks if not check["overall_healthy"])
        
        return {
            "period_hours": hours,
            "total_checks": len(recent_checks),
            "failed_checks": failed_checks,
            "success_rate_percent": round((1 - failed_checks / len(recent_checks)) * 100, 1),
            "response_time": {
                "average_seconds": round(sum(response_times) / len(response_times), 3),
                "max_seconds": max(response_times),
                "min_seconds": min(response_times)
            },
            "connection_utilization": {
                "average_percent": round(sum(utilization_values) / len(utilization_values), 1),
                "max_percent": max(utilization_values),
                "min_percent": min(utilization_values)
            },
            "recent_alerts": [
                alert for check in recent_checks[-10:]  # Last 10 checks
                for alert in check.get("alerts", [])
            ]
        }

# Usage in FastAPI endpoint
@router.get("/api/database/health")
async def get_database_health():
    """Get comprehensive database health status."""
    monitor = DatabaseHealthMonitor()
    return await monitor.comprehensive_health_check()

@router.get("/api/database/health/trends")
async def get_database_health_trends(hours: int = Query(24, ge=1, le=168)):
    """Get database health trends over time."""
    monitor = DatabaseHealthMonitor()
    return await monitor.get_health_trends(hours)
```

### Configuration Management Examples

```python
from kiremisu.database import db_config

# Runtime configuration adjustments for different environments
def configure_for_environment(env: str):
    """Adjust database configuration based on environment."""
    if env == "development":
        db_config.MAX_STRING_LENGTH = 2000  # More lenient for testing
        db_config.DEFAULT_SLOW_QUERY_THRESHOLD = 1.0  # Stricter monitoring
        db_config.CONNECTION_RETRY_ATTEMPTS = 2  # Fewer retries for faster feedback
        
    elif env == "production":
        db_config.MAX_STRING_LENGTH = 1000  # Stricter validation
        db_config.DEFAULT_SLOW_QUERY_THRESHOLD = 5.0  # More tolerant of load
        db_config.CONNECTION_RETRY_ATTEMPTS = 5  # More resilient to transient issues
        
    elif env == "testing":
        db_config.MAX_STRING_LENGTH = 500   # Very strict for security testing
        db_config.MAX_LIST_SIZE = 10        # Smaller limits for test performance
        db_config.HEALTH_CHECK_TIMEOUT = 1.0  # Fast timeouts for test speed

# Security configuration for high-security environments
def configure_enhanced_security():
    """Apply enhanced security configuration."""
    # Add additional dangerous SQL patterns for specialized threats
    additional_patterns = [
        "benchmark(",      # MySQL timing attacks
        "sleep(",          # Timing-based blind SQL injection
        "waitfor",         # SQL Server time delays
        "pg_sleep(",       # PostgreSQL delays
        "dbms_pipe",       # Oracle timing functions
        "sys.fn_",         # SQL Server system functions
        "information_schema", # Schema enumeration attempts
        "pg_tables",       # PostgreSQL table enumeration
        "sqlite_master",   # SQLite schema access
    ]
    
    db_config.DANGEROUS_SQL_PATTERNS = (
        *db_config.DANGEROUS_SQL_PATTERNS,
        *additional_patterns
    )
    
    # Reduce limits for enhanced security
    db_config.MAX_STRING_LENGTH = 200
    db_config.MAX_LIST_SIZE = 20
    db_config.MAX_SEARCH_PATTERN_LENGTH = 50
```

## Testing

Comprehensive test suite in `tests/database/test_utils.py` covers:
- Connection health checks and failures
- Retry logic with various error types
- Parameter validation edge cases including SQL injection attempts
- Regex-based pattern detection and case-insensitive matching
- Safe pattern creation and escaping
- Transaction rollback scenarios
- Whitespace obfuscation detection
- Configuration constant validation
- Performance testing with concurrent operations
- Bulk operation error handling

Integration tests in `tests/database/test_integration.py` provide:
- Real database connection testing
- Transaction context manager validation
- Bulk operations with actual data
- Health monitoring system validation
- SQL injection protection verification
- Connection pool monitoring
- Performance benchmarking

Run tests with:
```bash
# Unit tests for database utilities
PYTHONPATH=backend:$PYTHONPATH SECRET_KEY=test-key uv run pytest tests/database/test_utils.py -v

# Integration tests with real database
PYTHONPATH=backend:$PYTHONPATH SECRET_KEY=test-key uv run pytest tests/database/test_integration.py -v

# Coverage report
PYTHONPATH=backend:$PYTHONPATH SECRET_KEY=test-key uv run pytest tests/database/ --cov=kiremisu.database --cov-report=html
```