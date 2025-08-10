"""Database package with enhanced utilities."""

from .connection import get_db, get_db_session, close_db_connections
from .utils import (
    check_db_health,
    with_db_retry,
    db_transaction,
    bulk_create,
    safe_delete,
    log_slow_query,
    validate_query_params,
    safe_like_pattern,
    get_connection_info,
)
from .config import db_config
from .migrations import (
    get_current_revision,
    validate_migration_safety,
    run_migration_with_checks,
    get_migration_history,
)

__all__ = [
    # Connection management
    "get_db",
    "get_db_session",
    "close_db_connections",
    # Database utilities
    "check_db_health",
    "with_db_retry",
    "db_transaction",
    "bulk_create",
    "safe_delete",
    "log_slow_query",
    "validate_query_params",
    "safe_like_pattern",
    "get_connection_info",
    # Configuration
    "db_config",
    # Migration utilities
    "get_current_revision",
    "validate_migration_safety",
    "run_migration_with_checks",
    "get_migration_history",
]
