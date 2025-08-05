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

### Basic Retry Pattern
```python
from kiremisu.database import with_db_retry

@with_db_retry(max_attempts=3)
async def get_series_by_id(db: AsyncSession, series_id: UUID):
    return await db.get(Series, series_id)
```

### Safe User Input Handling
```python
from kiremisu.database import validate_query_params, safe_like_pattern

# In your API endpoint
try:
    clean_params = validate_query_params(search=search_term)
    search_pattern = safe_like_pattern(clean_params["search"])
    query = query.where(Series.title.ilike(search_pattern))
except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
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

### Performance Monitoring
```python
from kiremisu.database import log_slow_query

@log_slow_query("complex_series_query", threshold=2.0)
async def get_series_with_complex_filters(db: AsyncSession, filters: dict):
    # This will log if the query takes longer than 2 seconds
    return await db.execute(complex_query)
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

## Testing

Comprehensive test suite in `tests/database/test_utils.py` covers:
- Connection health checks and failures
- Retry logic with various error types
- Parameter validation edge cases
- Safe pattern creation
- Transaction rollback scenarios

Run tests with:
```bash
PYTHONPATH=backend:$PYTHONPATH SECRET_KEY=test-key uv run pytest tests/database/test_utils.py -v
```