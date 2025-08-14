"""Integration tests for database utilities with real database connections."""

import asyncio
from unittest.mock import patch

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from kiremisu.database.config import db_config
from kiremisu.database.models import Chapter, Series
from kiremisu.database.utils import (
    bulk_create,
    check_db_health,
    db_transaction,
    get_connection_info,
    safe_delete,
    safe_like_pattern,
    validate_query_params,
    with_db_retry,
)


class TestDatabaseIntegration:
    """Integration tests using real database connections."""

    async def test_health_check_with_real_connection(self, db_session: AsyncSession):
        """Test health check with actual database."""
        result = await check_db_health()
        assert result is True

    async def test_connection_info_retrieval(self, db_session: AsyncSession):
        """Test connection information gathering."""
        info = await get_connection_info()

        assert "is_connected" in info
        assert info["is_connected"] is True
        assert "engine_info" in info
        assert "pool_info" in info

    async def test_transaction_context_with_rollback(self, db_session: AsyncSession):
        """Test transaction context manager with rollback on error."""
        initial_count = (await db_session.execute(
            select(func.count(Series.id)))).scalar()

        with pytest.raises(ValueError):
            async with db_transaction() as tx_session:
                # Add a series
                series = Series(
                    title_primary="Test Transaction Series",
                    language="en",
                    file_path="/test/transaction"
                )
                tx_session.add(series)
                await tx_session.flush()

                # Force an error to trigger rollback
                raise ValueError("Test rollback")

        # Verify the series was not persisted due to rollback
        final_count = (await db_session.execute(
            select(func.count(Series.id)))).scalar()
        assert final_count == initial_count

    async def test_bulk_operations_integration(self, db_session: AsyncSession):
        """Test bulk operations with real database."""
        # Create a test series first
        series = Series(
            title_primary="Bulk Test Series",
            language="en",
            file_path="/test/bulk"
        )
        db_session.add(series)
        await db_session.commit()
        await db_session.refresh(series)

        # Create multiple chapters
        chapters = [
            Chapter(
                series_id=series.id,
                chapter_number=i,
                file_path=f"/test/bulk/chapter_{i}.cbz",
                page_count=20
            )
            for i in range(1, 6)
        ]

        await bulk_create(db_session, chapters)
        await db_session.commit()

        # Verify chapters were created
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM chapters WHERE series_id = :series_id"),
            {"series_id": series.id}
        )
        count = result.scalar()
        assert count == 5

    async def test_safe_delete_integration(self, db_session: AsyncSession):
        """Test safe delete with real database objects."""
        # Create a test series
        series = Series(
            title_primary="Delete Test Series",
            language="en",
            file_path="/test/delete"
        )
        db_session.add(series)
        await db_session.commit()
        await db_session.refresh(series)

        # Get fresh session for deletion test
        await db_session.refresh(series)

        # Test successful deletion
        result = await safe_delete(db_session, series)
        assert result is True

        # Commit the deletion
        await db_session.commit()

        # Verify deletion in fresh session
        deleted_series = await db_session.get(Series, series.id)
        assert deleted_series is None

    async def test_retry_decorator_with_real_failures(self, db_session: AsyncSession):
        """Test retry decorator with simulated connection failures."""
        call_count = 0

        @with_db_retry(max_attempts=3, delay=0.1)
        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                from sqlalchemy.exc import DisconnectionError
                raise DisconnectionError("Simulated connection loss", None, None)
            return "success"

        result = await flaky_operation()
        assert result == "success"
        assert call_count == 3


class TestEnhancedSQLInjectionProtection:
    """Test the enhanced SQL injection protection features."""

    def test_comprehensive_sql_injection_patterns(self):
        """Test detection of various SQL injection patterns."""
        dangerous_inputs = [
            "'; DROP TABLE users; --",
            "admin'--",
            "' OR 1=1--",
            "' OR '1'='1",
            "UNION SELECT * FROM users",
            "1; EXEC xp_cmdshell('dir')",
            "'; WAITFOR DELAY '00:00:05'--",
            "admin' /*",
            "1' AND SLEEP(5)--",
            "' UNION ALL SELECT NULL,NULL,table_name FROM information_schema.tables--",
            "0x41646D696E",  # Hex encoded 'Admin'
            "CAST((SELECT COUNT(*) FROM users) AS varchar)",
        ]

        for dangerous_input in dangerous_inputs:
            with pytest.raises(ValueError, match="SQL injection pattern|suspicious pattern"):
                validate_query_params(search=dangerous_input)

    def test_case_insensitive_detection(self):
        """Test that SQL injection detection is case-insensitive."""
        case_variants = [
            "UNION select",
            "Union Select",
            "uNiOn SeLeCt",
            "DROP table",
            "DeLeTe FROM",
        ]

        for variant in case_variants:
            with pytest.raises(ValueError):
                validate_query_params(query=variant)

    def test_regex_based_injection_detection(self):
        """Test regex-based injection pattern detection."""
        regex_patterns = [
            "' OR 1=1 --",
            "admin' OR '1'='1",
            "test'; SELECT * FROM users; --",
            "0x48656C6C6F",  # Hex pattern
        ]

        for pattern in regex_patterns:
            with pytest.raises(ValueError):
                validate_query_params(input=pattern)

    def test_whitespace_obfuscation_detection(self):
        """Test detection of whitespace-based obfuscation attempts."""
        # Create input with excessive leading/trailing whitespace (more than 10 chars difference)
        # Use safe content but excessive whitespace
        obfuscated_input = "   " + "innocent search term" + "   " + " " * 15  # Total of 21 extra whitespace chars

        with pytest.raises(ValueError, match="excessive whitespace"):
            validate_query_params(search=obfuscated_input)

    def test_safe_inputs_pass_validation(self):
        """Test that legitimate inputs pass validation."""
        safe_inputs = {
            "search": "Attack on Titan",
            "author": "Hajime Isayama",
            "year": 2009,
            "active": True,
            "tags": ["action", "drama", "fantasy"],
            "rating": 4.5,
        }

        result = validate_query_params(**safe_inputs)
        assert result["search"] == "Attack on Titan"
        assert result["author"] == "Hajime Isayama"
        assert result["year"] == 2009
        assert result["active"] is True
        assert result["tags"] == ["action", "drama", "fantasy"]
        assert result["rating"] == 4.5


class TestConfigurationConstants:
    """Test that configuration constants are properly used."""

    def test_string_length_limits(self):
        """Test string length validation uses configuration."""
        long_string = "a" * (db_config.MAX_STRING_LENGTH + 1)

        with pytest.raises(ValueError, match=f"max {db_config.MAX_STRING_LENGTH} characters"):
            validate_query_params(search=long_string)

    def test_list_size_limits(self):
        """Test list size validation uses configuration."""
        large_list = list(range(db_config.MAX_LIST_SIZE + 1))

        with pytest.raises(ValueError, match=f"max {db_config.MAX_LIST_SIZE} items"):
            validate_query_params(items=large_list)

    def test_search_pattern_limits(self):
        """Test search pattern length validation."""
        long_search = "a" * (db_config.MAX_SEARCH_PATTERN_LENGTH + 1)

        with pytest.raises(ValueError, match=f"max {db_config.MAX_SEARCH_PATTERN_LENGTH} characters"):
            safe_like_pattern(long_search)


class TestPerformanceAndLoad:
    """Basic performance tests for database utilities."""

    async def test_health_check_timeout(self):
        """Test health check with timeout protection."""
        # Mock a slow database response
        with patch('kiremisu.database.utils.get_db_session') as mock_session:
            # Simulate a hanging connection
            async def slow_session():
                await asyncio.sleep(10)  # Longer than timeout

            mock_session.return_value.__aenter__ = slow_session

            result = await check_db_health()
            assert result is False

    def test_parameter_validation_performance(self):
        """Test parameter validation performance with large inputs."""
        import time

        # Test with moderate-sized inputs
        large_params = {
            f"param_{i}": f"value_{i}" * 10
            for i in range(50)
        }

        start_time = time.time()
        result = validate_query_params(**large_params)
        end_time = time.time()

        # Should complete within reasonable time
        assert end_time - start_time < 1.0
        assert len(result) == 50

    async def test_concurrent_database_health_checks(self):
        """Test concurrent health check operations."""
        # Run multiple health checks concurrently
        tasks = [check_db_health() for _ in range(5)]  # Reduce to avoid overwhelming the DB
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Most should succeed, but some might timeout in concurrent execution
        successful_results = [r for r in results if r is True]
        assert len(successful_results) >= 3  # At least 3 out of 5 should succeed
        assert len(results) == 5
