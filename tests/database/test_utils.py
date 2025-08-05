"""Tests for database utilities."""

import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.exc import DisconnectionError, OperationalError

from kiremisu.database.utils import (
    check_db_health,
    with_db_retry,
    validate_query_params,
    safe_like_pattern,
    bulk_create,
    db_transaction
)


class TestDatabaseHealth:
    """Test database health checks."""

    @patch('kiremisu.database.utils.get_db_session')
    async def test_check_db_health_success(self, mock_get_db):
        """Test successful health check."""
        mock_session = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_session
        
        result = await check_db_health()
        assert result is True
        mock_session.execute.assert_called_once()

    @patch('kiremisu.database.utils.get_db_session')
    async def test_check_db_health_failure(self, mock_get_db):
        """Test failed health check."""
        mock_get_db.side_effect = Exception("Connection failed")
        
        result = await check_db_health()
        assert result is False


class TestRetryDecorator:
    """Test retry decorator functionality."""

    async def test_retry_success_first_attempt(self):
        """Test successful operation on first attempt."""
        @with_db_retry(max_attempts=3)
        async def mock_operation():
            return "success"
        
        result = await mock_operation()
        assert result == "success"

    async def test_retry_success_after_failures(self):
        """Test successful operation after retries."""
        attempt_count = 0
        
        @with_db_retry(max_attempts=3, delay=0.1)
        async def mock_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise DisconnectionError("Connection lost", None, None)
            return "success"
        
        result = await mock_operation()
        assert result == "success"
        assert attempt_count == 3

    async def test_retry_exhausted(self):
        """Test retry exhaustion."""
        @with_db_retry(max_attempts=2, delay=0.1)
        async def mock_operation():
            raise DisconnectionError("Connection lost", None, None)
        
        with pytest.raises(DisconnectionError):
            await mock_operation()

    async def test_non_retryable_error(self):
        """Test non-retryable error."""
        @with_db_retry(max_attempts=3)
        async def mock_operation():
            raise ValueError("Invalid input")
        
        with pytest.raises(ValueError):
            await mock_operation()


class TestParameterValidation:
    """Test query parameter validation."""

    def test_validate_simple_params(self):
        """Test validation of simple parameters."""
        params = {
            "name": "test",
            "count": 42,
            "active": True,
            "optional": None
        }
        
        result = validate_query_params(**params)
        assert result["name"] == "test"
        assert result["count"] == 42
        assert result["active"] is True
        assert result["optional"] is None

    def test_validate_dangerous_strings(self):
        """Test rejection of dangerous string patterns."""
        dangerous_inputs = [
            "test'; DROP TABLE users; --",
            'test" OR 1=1',
            "test/* comment */",
            "test; DELETE FROM table",
            "UNION SELECT * FROM users",
            "' OR 1=1 --",
            "admin'--",
        ]
        
        for dangerous_input in dangerous_inputs:
            with pytest.raises(ValueError, match="SQL injection pattern|suspicious pattern"):
                validate_query_params(search=dangerous_input)

    def test_validate_long_strings(self):
        """Test rejection of overly long strings."""
        long_string = "a" * 1001
        
        with pytest.raises(ValueError, match="too long"):
            validate_query_params(search=long_string)

    def test_validate_large_lists(self):
        """Test rejection of large lists."""
        large_list = list(range(101))
        
        with pytest.raises(ValueError, match="list too long"):
            validate_query_params(items=large_list)

    def test_string_trimming(self):
        """Test string trimming."""
        result = validate_query_params(name="  test  ")
        assert result["name"] == "test"


class TestSafeLikePattern:
    """Test safe LIKE pattern creation."""

    def test_basic_pattern(self):
        """Test basic pattern creation."""
        result = safe_like_pattern("test")
        assert result == "%test%"

    def test_empty_pattern(self):
        """Test empty pattern."""
        result = safe_like_pattern("")
        assert result == "%"

    def test_escaped_patterns(self):
        """Test escaping of special LIKE characters."""
        result = safe_like_pattern("test_with%wildcards")
        assert result == "%test\\_with\\%wildcards%"

    def test_long_pattern_rejection(self):
        """Test rejection of overly long patterns."""
        long_pattern = "a" * 101
        
        with pytest.raises(ValueError, match="too long"):
            safe_like_pattern(long_pattern)


class TestBulkOperations:
    """Test bulk database operations."""

    async def test_bulk_create_empty_list(self):
        """Test bulk create with empty list."""
        mock_session = AsyncMock()
        
        await bulk_create(mock_session, [])
        
        mock_session.add_all.assert_not_called()
        mock_session.flush.assert_not_called()

    async def test_bulk_create_with_items(self):
        """Test bulk create with items."""
        mock_session = AsyncMock()
        items = ["item1", "item2", "item3"]
        
        await bulk_create(mock_session, items)
        
        mock_session.add_all.assert_called_once_with(items)
        mock_session.flush.assert_called_once()


class TestTransactionContext:
    """Test transaction context manager."""

    @patch('kiremisu.database.utils.get_db_session')
    async def test_successful_transaction(self, mock_get_db):
        """Test successful transaction."""
        mock_session = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_session
        
        async with db_transaction() as session:
            # Simulate some database work
            session.add("test_item")
        
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()

    @patch('kiremisu.database.utils.get_db_session')
    async def test_failed_transaction(self, mock_get_db):
        """Test failed transaction with rollback."""
        mock_session = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_session
        
        with pytest.raises(ValueError):
            async with db_transaction() as session:
                # Simulate database work that fails
                session.add("test_item")
                raise ValueError("Something went wrong")
        
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()