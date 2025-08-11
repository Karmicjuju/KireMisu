"""Configuration constants for database utilities."""

from typing import Sequence


class DatabaseConfig:
    """Configuration constants for database operations."""

    # Query parameter validation
    MAX_STRING_LENGTH = 1000
    MAX_LIST_SIZE = 100
    MAX_SEARCH_PATTERN_LENGTH = 100

    # Retry configuration
    DEFAULT_MAX_ATTEMPTS = 3
    DEFAULT_RETRY_DELAY = 1.0

    # Performance monitoring
    DEFAULT_SLOW_QUERY_THRESHOLD = 1.0

    # SQL injection protection - comprehensive list of dangerous patterns
    DANGEROUS_SQL_PATTERNS: Sequence[str] = (
        # SQL keywords
        "'",
        '"',
        ";",
        "--",
        "/*",
        "*/",
        # SQL injection attack patterns
        "union",
        "select",
        "insert",
        "update",
        "delete",
        "drop",
        "create",
        "alter",
        "truncate",
        "exec",
        "execute",
        "sp_",
        "xp_",
        # Common injection techniques
        "or 1=1",
        "or '1'='1'",
        'or "1"="1"',
        "and 1=1",
        "and '1'='1'",
        'and "1"="1"',
        "having",
        "group by",
        "order by",
        # Database-specific functions
        "concat",
        "substring",
        "ascii",
        "char",
        "nchar",
        "version",
        "user",
        "database",
        "schema",
        # File system operations
        "load_file",
        "into outfile",
        "into dumpfile",
        # Comments and bypass techniques
        "/*!",
        "/*#",
        "/*--",
        "#",
        "*/;",
        # Union-based attacks
        "union all",
        "union select",
        # Time-based attacks
        "sleep",
        "pg_sleep",
        "waitfor",
        "delay",
        # Error-based attacks
        "cast",
        "convert",
        "extractvalue",
        "updatexml",
    )

    # Connection management
    HEALTH_CHECK_TIMEOUT = 5.0
    CONNECTION_RETRY_ATTEMPTS = 3
    CONNECTION_RETRY_DELAY = 0.5


# Global configuration instance
db_config = DatabaseConfig()
