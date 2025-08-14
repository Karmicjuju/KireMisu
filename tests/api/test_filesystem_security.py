"""
Comprehensive security tests for filesystem API endpoints.
"""
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from kiremisu.api.filesystem import validate_path_input, validate_path_security
from kiremisu.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def temp_manga_storage():
    """Create a temporary manga storage directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manga_storage = Path(temp_dir) / "manga-storage"
        manga_storage.mkdir(parents=True, exist_ok=True)

        # Create test directory structure
        (manga_storage / "test-series").mkdir()
        (manga_storage / "test-series" / "chapter-1").mkdir()
        (manga_storage / ".hidden").mkdir()

        # Create some test files
        (manga_storage / "test-series" / "chapter-1" / "page1.jpg").write_text("test")
        (manga_storage / ".hidden" / "secret.txt").write_text("secret")

        yield manga_storage


class TestPathValidation:
    """Test path validation functions."""

    def test_validate_path_input_valid_paths(self):
        """Test validation with valid paths."""
        valid_paths = [
            "/manga-storage",
            "/manga-storage/series",
            "/manga-storage/series/chapter-1",
        ]

        for path in valid_paths:
            # Should not raise exception
            validate_path_input(path, "127.0.0.1")

    def test_validate_path_input_too_long(self):
        """Test path length validation."""
        long_path = "/manga-storage/" + "a" * 5000

        with pytest.raises(Exception) as exc_info:
            validate_path_input(long_path, "127.0.0.1")

        assert "too long" in str(exc_info.value).lower()

    @pytest.mark.parametrize("malicious_path", [
        "/manga-storage/../etc/passwd",
        "/manga-storage/../../etc/passwd",
        "/manga-storage/%2e%2e/etc/passwd",
        "/manga-storage/%252e%252e/etc/passwd",
        "/manga-storage/test<script>",
        "/manga-storage/test|rm -rf /",
        "/manga-storage/test\x00null",
        "/manga-storage/test\x1fcontrol",
    ])
    def test_validate_path_input_dangerous_patterns(self, malicious_path):
        """Test detection of dangerous patterns."""
        with pytest.raises(Exception) as exc_info:
            validate_path_input(malicious_path, "127.0.0.1")

        assert "invalid path format" in str(exc_info.value).lower()

    def test_validate_path_security_valid_path(self, temp_manga_storage):
        """Test security validation with valid path."""
        with patch('kiremisu.api.filesystem.MANGA_STORAGE_BASE', temp_manga_storage):
            valid_path = temp_manga_storage / "test-series"
            result = validate_path_security(valid_path, "127.0.0.1")
            assert result == valid_path

    def test_validate_path_security_traversal_attempt(self, temp_manga_storage):
        """Test security validation blocks path traversal."""
        with patch('kiremisu.api.filesystem.MANGA_STORAGE_BASE', temp_manga_storage):
            # Try to access parent directory
            traversal_path = temp_manga_storage.parent / "secret"

            with pytest.raises(Exception) as exc_info:
                validate_path_security(traversal_path, "127.0.0.1")

            assert "access denied" in str(exc_info.value).lower()

    def test_validate_path_security_symlink_attack(self, temp_manga_storage):
        """Test security validation blocks symlink attacks."""
        with patch('kiremisu.api.filesystem.MANGA_STORAGE_BASE', temp_manga_storage):
            # Create symlink pointing outside manga storage
            outside_dir = temp_manga_storage.parent / "outside"
            outside_dir.mkdir()

            symlink_path = temp_manga_storage / "malicious_link"
            symlink_path.symlink_to(outside_dir)

            # Resolve the symlink and try to validate
            resolved_path = symlink_path.resolve()

            with pytest.raises(Exception) as exc_info:
                validate_path_security(resolved_path, "127.0.0.1")

            assert "access denied" in str(exc_info.value).lower()


class TestBrowseEndpoint:
    """Test /api/filesystem/browse endpoint security."""

    def test_browse_valid_directory(self, client, temp_manga_storage):
        """Test browsing valid directory."""
        with patch('kiremisu.api.filesystem.MANGA_STORAGE_BASE', temp_manga_storage):
            response = client.get(f"/api/filesystem/browse?path={temp_manga_storage}")

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "total_items" in data
            assert "page" in data
            assert data["current_path"] == str(temp_manga_storage)

    def test_browse_path_traversal_blocked(self, client, temp_manga_storage):
        """Test that path traversal attempts are blocked."""
        traversal_paths = [
            str(temp_manga_storage) + "/../../../etc/passwd",
            str(temp_manga_storage) + "/../../etc",
            "/etc/passwd",
            "/../etc/passwd",
        ]

        for path in traversal_paths:
            response = client.get(f"/api/filesystem/browse?path={path}")
            assert response.status_code in [400, 403], f"Path {path} should be blocked"

    def test_browse_pagination(self, client, temp_manga_storage):
        """Test pagination functionality."""
        with patch('kiremisu.api.filesystem.MANGA_STORAGE_BASE', temp_manga_storage):
            # Create many items for pagination testing
            for i in range(15):
                (temp_manga_storage / f"item_{i:02d}").mkdir()

            # Test first page
            response = client.get(
                f"/api/filesystem/browse?path={temp_manga_storage}&page=1&page_size=10"
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) <= 10
            assert data["page"] == 1
            assert data["page_size"] == 10
            assert data["has_more"] is True

            # Test second page
            response = client.get(
                f"/api/filesystem/browse?path={temp_manga_storage}&page=2&page_size=10"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["page"] == 2

    def test_browse_hidden_files(self, client, temp_manga_storage):
        """Test hidden file handling."""
        with patch('kiremisu.api.filesystem.MANGA_STORAGE_BASE', temp_manga_storage):
            # Without show_hidden
            response = client.get(f"/api/filesystem/browse?path={temp_manga_storage}")
            assert response.status_code == 200
            data = response.json()
            item_names = [item["name"] for item in data["items"]]
            assert ".hidden" not in item_names

            # With show_hidden
            response = client.get(
                f"/api/filesystem/browse?path={temp_manga_storage}&show_hidden=true"
            )
            assert response.status_code == 200
            data = response.json()
            item_names = [item["name"] for item in data["items"]]
            assert ".hidden" in item_names

    def test_browse_nonexistent_directory(self, client, temp_manga_storage):
        """Test browsing non-existent directory."""
        with patch('kiremisu.api.filesystem.MANGA_STORAGE_BASE', temp_manga_storage):
            nonexistent = temp_manga_storage / "nonexistent"
            response = client.get(f"/api/filesystem/browse?path={nonexistent}")
            assert response.status_code == 404

    def test_browse_file_instead_of_directory(self, client, temp_manga_storage):
        """Test browsing a file instead of directory."""
        with patch('kiremisu.api.filesystem.MANGA_STORAGE_BASE', temp_manga_storage):
            file_path = temp_manga_storage / "test-series" / "chapter-1" / "page1.jpg"
            response = client.get(f"/api/filesystem/browse?path={file_path}")
            assert response.status_code == 400

    @pytest.mark.parametrize("invalid_param", [
        {"page": 0},
        {"page": -1},
        {"page_size": 0},
        {"page_size": -1},
        {"page_size": 10000},  # Exceeds MAX_ITEMS_PER_PAGE
    ])
    def test_browse_invalid_pagination_params(self, client, temp_manga_storage, invalid_param):
        """Test invalid pagination parameters."""
        with patch('kiremisu.api.filesystem.MANGA_STORAGE_BASE', temp_manga_storage):
            params = {"path": str(temp_manga_storage)}
            params.update(invalid_param)

            response = client.get("/api/filesystem/browse", params=params)
            assert response.status_code == 422  # Validation error


class TestValidatePathEndpoint:
    """Test /api/filesystem/validate-path endpoint security."""

    def test_validate_valid_path(self, client, temp_manga_storage):
        """Test validating valid path."""
        with patch('kiremisu.api.filesystem.MANGA_STORAGE_BASE', temp_manga_storage):
            response = client.get(f"/api/filesystem/validate-path?path={temp_manga_storage}")

            assert response.status_code == 200
            data = response.json()
            assert data["exists"] is True
            assert data["is_directory"] is True
            assert data["readable"] is True
            assert data["path"] == str(temp_manga_storage)

    def test_validate_traversal_attempt(self, client, temp_manga_storage):
        """Test validation blocks path traversal."""
        traversal_paths = [
            str(temp_manga_storage) + "/../../../etc/passwd",
            "/etc/passwd",
            "/../etc/passwd",
        ]

        for path in traversal_paths:
            response = client.get(f"/api/filesystem/validate-path?path={path}")
            assert response.status_code == 200  # Endpoint returns 200 but with error
            data = response.json()
            assert data["exists"] is False
            assert "error" in data

    def test_validate_nonexistent_path(self, client, temp_manga_storage):
        """Test validating non-existent path."""
        with patch('kiremisu.api.filesystem.MANGA_STORAGE_BASE', temp_manga_storage):
            nonexistent = temp_manga_storage / "nonexistent"
            response = client.get(f"/api/filesystem/validate-path?path={nonexistent}")

            assert response.status_code == 200
            data = response.json()
            assert data["exists"] is False
            assert data["is_directory"] is False
            assert data["readable"] is False


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_browse_rate_limit(self, client, temp_manga_storage):
        """Test rate limiting on browse endpoint."""
        with patch('kiremisu.api.filesystem.MANGA_STORAGE_BASE', temp_manga_storage):
            # Make many requests quickly to trigger rate limit
            # Note: This test might be flaky in CI, consider mocking rate limiter
            responses = []
            for _ in range(35):  # Exceeds 30/minute limit
                response = client.get(f"/api/filesystem/browse?path={temp_manga_storage}")
                responses.append(response.status_code)

            # Should eventually get rate limited (429)
            assert 429 in responses

    def test_validate_rate_limit(self, client, temp_manga_storage):
        """Test rate limiting on validate endpoint."""
        with patch('kiremisu.api.filesystem.MANGA_STORAGE_BASE', temp_manga_storage):
            # Make many requests quickly to trigger rate limit
            responses = []
            for _ in range(65):  # Exceeds 60/minute limit
                response = client.get(f"/api/filesystem/validate-path?path={temp_manga_storage}")
                responses.append(response.status_code)

            # Should eventually get rate limited (429)
            assert 429 in responses


class TestSecurityLogging:
    """Test security audit logging."""

    def test_access_attempts_logged(self, client, temp_manga_storage, caplog):
        """Test that access attempts are logged."""
        with patch('kiremisu.api.filesystem.MANGA_STORAGE_BASE', temp_manga_storage):
            client.get(f"/api/filesystem/browse?path={temp_manga_storage}")

            # Check that access was logged
            assert "Path access attempt" in caplog.text
            assert str(temp_manga_storage) in caplog.text

    def test_traversal_attempts_logged(self, client, temp_manga_storage, caplog):
        """Test that path traversal attempts are logged."""
        traversal_path = str(temp_manga_storage) + "/../../../etc/passwd"
        client.get(f"/api/filesystem/browse?path={traversal_path}")

        # Check that security violation was logged
        assert any(
            level in caplog.text.lower()
            for level in ["warning", "error", "dangerous pattern", "traversal"]
        )

    def test_successful_access_logged(self, client, temp_manga_storage, caplog):
        """Test that successful access is logged."""
        with patch('kiremisu.api.filesystem.MANGA_STORAGE_BASE', temp_manga_storage):
            client.get(f"/api/filesystem/browse?path={temp_manga_storage}")

            assert "Directory access successful" in caplog.text


class TestIntegrationSecurity:
    """Integration tests for security scenarios."""

    def test_end_to_end_security_flow(self, client, temp_manga_storage):
        """Test complete security flow from input to response."""
        with patch('kiremisu.api.filesystem.MANGA_STORAGE_BASE', temp_manga_storage):
            # 1. Valid access should work
            response = client.get(f"/api/filesystem/browse?path={temp_manga_storage}")
            assert response.status_code == 200

            # 2. Path traversal should be blocked at input validation
            response = client.get("/api/filesystem/browse?path=/../etc/passwd")
            assert response.status_code in [400, 403]

            # 3. Long path should be rejected
            long_path = "/manga-storage/" + "a" * 5000
            response = client.get(f"/api/filesystem/browse?path={long_path}")
            assert response.status_code == 400

            # 4. Dangerous characters should be rejected
            response = client.get("/api/filesystem/browse?path=/manga-storage/test<script>")
            assert response.status_code == 400

    def test_information_disclosure_prevention(self, client, temp_manga_storage):
        """Test that sensitive information is not disclosed."""
        with patch('kiremisu.api.filesystem.MANGA_STORAGE_BASE', temp_manga_storage):
            # Try to access restricted path
            response = client.get("/api/filesystem/browse?path=/etc")

            # Should not reveal system details in error messages
            if response.status_code != 200:
                error_text = response.text.lower()
                sensitive_terms = ["etc", "passwd", "system", "root", "bin"]
                for term in sensitive_terms:
                    assert term not in error_text, f"Sensitive term '{term}' found in error"
