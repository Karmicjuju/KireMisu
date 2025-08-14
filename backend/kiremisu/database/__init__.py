"""Database package with enhanced utilities."""

from .config import db_config
from .connection import close_db_connections, get_db, get_db_session
from .migrations import (
    get_current_revision,
    get_migration_history,
    run_migration_with_checks,
    validate_migration_safety,
)
from .utils import (
    bulk_create,
    check_db_health,
    db_transaction,
    get_connection_info,
    log_slow_query,
    safe_delete,
    safe_like_pattern,
    validate_query_params,
    with_db_retry,
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
