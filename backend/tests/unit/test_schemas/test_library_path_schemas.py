import pytest
from datetime import datetime
from pydantic import ValidationError

from app.schemas.library_path import (
    LibraryPathBase,
    LibraryPathCreate,
    LibraryPathUpdate,
    LibraryPathResponse,
    DirectoryItem,
    DirectoryBrowseResponse,
    PathValidationResult,
    StorageInfo
)


class TestLibraryPathBaseSchema:
    """Test LibraryPathBase schema validation."""

    def test_valid_library_path_base(self):
        """Test creation with valid data."""
        path_data = LibraryPathBase(
            name="Test Library",
            path="/home/user/manga",
            is_active=True,
            priority=5
        )
        
        assert path_data.name == "Test Library"
        assert path_data.path == "/home/user/manga"
        assert path_data.is_active is True
        assert path_data.priority == 5

    def test_path_validation_absolute_path_required(self):
        """Test that only absolute paths are accepted."""
        # Valid absolute path
        valid_data = {"name": "Test", "path": "/absolute/path"}
        path = LibraryPathBase(**valid_data)
        assert path.path == "/absolute/path"
        
        # Invalid relative path
        with pytest.raises(ValidationError) as exc_info:
            LibraryPathBase(name="Test", path="relative/path")
        
        assert "Path must be absolute" in str(exc_info.value)

    def test_path_normalization(self):
        """Test that paths are normalized correctly."""
        test_cases = [
            ("/path//with//double//slashes", "/path/with/double/slashes"),
            ("/path/with/../parent/ref", "/path/parent/ref"),
            ("/path/./current/./ref", "/path/current/ref"),
            ("/path/trailing/slash/", "/path/trailing/slash"),
        ]
        
        for input_path, expected_output in test_cases:
            path = LibraryPathBase(name="Test", path=input_path)
            assert path.path == expected_output

    def test_empty_path_validation(self):
        """Test validation of empty paths."""
        with pytest.raises(ValidationError) as exc_info:
            LibraryPathBase(name="Test", path="")
        
        assert "Path cannot be empty" in str(exc_info.value)

    def test_name_validation_empty_string(self):
        """Test name validation with empty strings."""
        with pytest.raises(ValidationError) as exc_info:
            LibraryPathBase(name="", path="/test/path")
        
        assert "Name cannot be empty" in str(exc_info.value)

    def test_name_validation_whitespace_only(self):
        """Test name validation with whitespace-only strings."""
        with pytest.raises(ValidationError) as exc_info:
            LibraryPathBase(name="   ", path="/test/path")
        
        assert "Name cannot be empty" in str(exc_info.value)

    def test_name_whitespace_trimming(self):
        """Test that leading/trailing whitespace is trimmed from names."""
        path = LibraryPathBase(name="  Test Library  ", path="/test/path")
        assert path.name == "Test Library"

    def test_default_values(self):
        """Test default values are applied correctly."""
        path = LibraryPathBase(name="Test", path="/test/path")
        
        assert path.is_active is True  # Default value
        assert path.priority == 0      # Default value

    def test_field_length_limits(self):
        """Test field length validation."""
        # Name too long (over 255 characters)
        long_name = "a" * 256
        with pytest.raises(ValidationError) as exc_info:
            LibraryPathBase(name=long_name, path="/test/path")
        
        error_str = str(exc_info.value)
        assert "ensure this value has at most 255 characters" in error_str

        # Path too long (over 1000 characters)
        long_path = "/" + "a" * 1000  # 1001 total characters
        with pytest.raises(ValidationError) as exc_info:
            LibraryPathBase(name="Test", path=long_path)
        
        error_str = str(exc_info.value)
        assert "ensure this value has at most 1000 characters" in error_str

    def test_priority_types(self):
        """Test priority field accepts various integer types."""
        # Positive integer
        path1 = LibraryPathBase(name="Test1", path="/path1", priority=10)
        assert path1.priority == 10
        
        # Negative integer
        path2 = LibraryPathBase(name="Test2", path="/path2", priority=-5)
        assert path2.priority == -5
        
        # Zero
        path3 = LibraryPathBase(name="Test3", path="/path3", priority=0)
        assert path3.priority == 0

    def test_boolean_field_validation(self):
        """Test is_active field validation."""
        # Explicit True
        path1 = LibraryPathBase(name="Test1", path="/path1", is_active=True)
        assert path1.is_active is True
        
        # Explicit False
        path2 = LibraryPathBase(name="Test2", path="/path2", is_active=False)
        assert path2.is_active is False
        
        # String representations (should be converted)
        path3 = LibraryPathBase(name="Test3", path="/path3", is_active="true")
        assert path3.is_active is True
        
        path4 = LibraryPathBase(name="Test4", path="/path4", is_active="false")
        assert path4.is_active is False


class TestLibraryPathCreateSchema:
    """Test LibraryPathCreate schema validation."""

    def test_inherits_base_validation(self):
        """Test that create schema inherits all base validations."""
        # Should work with valid data
        create_data = LibraryPathCreate(
            name="Test Library",
            path="/home/user/manga",
            is_active=True,
            priority=5
        )
        
        assert create_data.name == "Test Library"
        
        # Should fail with invalid data
        with pytest.raises(ValidationError):
            LibraryPathCreate(name="", path="/test/path")

    def test_all_fields_required_except_defaults(self):
        """Test that name and path are required, others have defaults."""
        # Minimal valid data (name and path only)
        create_data = LibraryPathCreate(name="Test", path="/test/path")
        
        assert create_data.name == "Test"
        assert create_data.path == "/test/path"
        assert create_data.is_active is True  # Default
        assert create_data.priority == 0      # Default


class TestLibraryPathUpdateSchema:
    """Test LibraryPathUpdate schema validation."""

    def test_all_fields_optional(self):
        """Test that all fields are optional in update schema."""
        # Empty update should be valid
        update_data = LibraryPathUpdate()
        
        assert update_data.name is None
        assert update_data.is_active is None
        assert update_data.priority is None

    def test_partial_updates(self):
        """Test partial updates with some fields."""
        # Update only name
        update1 = LibraryPathUpdate(name="Updated Name")
        assert update1.name == "Updated Name"
        assert update1.is_active is None
        
        # Update only is_active
        update2 = LibraryPathUpdate(is_active=False)
        assert update2.is_active is False
        assert update2.name is None
        
        # Update only priority
        update3 = LibraryPathUpdate(priority=15)
        assert update3.priority == 15
        assert update3.name is None

    def test_name_validation_in_update(self):
        """Test name validation in update schema."""
        # Valid name update
        update = LibraryPathUpdate(name="  Valid Name  ")
        assert update.name == "Valid Name"  # Should be trimmed
        
        # Invalid empty name
        with pytest.raises(ValidationError):
            LibraryPathUpdate(name="")
        
        # Invalid whitespace-only name
        with pytest.raises(ValidationError):
            LibraryPathUpdate(name="   ")

    def test_update_field_length_limits(self):
        """Test field length validation in updates."""
        # Name too long
        long_name = "a" * 256
        with pytest.raises(ValidationError):
            LibraryPathUpdate(name=long_name)


class TestLibraryPathResponseSchema:
    """Test LibraryPathResponse schema."""

    def test_response_schema_includes_metadata(self):
        """Test that response schema includes all required metadata."""
        now = datetime.now()
        
        response_data = LibraryPathResponse(
            id=1,
            name="Test Library",
            path="/test/path",
            is_active=True,
            priority=5,
            created_at=now,
            updated_at=now
        )
        
        assert response_data.id == 1
        assert response_data.name == "Test Library"
        assert response_data.created_at == now
        assert response_data.updated_at == now

    def test_response_inherits_base_validation(self):
        """Test that response schema still validates base fields."""
        now = datetime.now()
        
        # Should validate name
        with pytest.raises(ValidationError):
            LibraryPathResponse(
                id=1,
                name="",
                path="/test/path",
                is_active=True,
                priority=5,
                created_at=now,
                updated_at=now
            )


class TestDirectoryItemSchema:
    """Test DirectoryItem schema validation."""

    def test_valid_directory_item(self):
        """Test creation of valid directory items."""
        now = datetime.now()
        
        # Directory item
        dir_item = DirectoryItem(
            name="test_dir",
            path="/test/path/test_dir",
            is_directory=True,
            size=None,
            modified_at=now
        )
        
        assert dir_item.name == "test_dir"
        assert dir_item.is_directory is True
        assert dir_item.size is None
        
        # File item
        file_item = DirectoryItem(
            name="test_file.txt",
            path="/test/path/test_file.txt",
            is_directory=False,
            size=1024,
            modified_at=now
        )
        
        assert file_item.name == "test_file.txt"
        assert file_item.is_directory is False
        assert file_item.size == 1024

    def test_required_fields(self):
        """Test that required fields are validated."""
        with pytest.raises(ValidationError) as exc_info:
            DirectoryItem(
                path="/test/path",
                is_directory=True
                # Missing name
            )
        
        assert "name" in str(exc_info.value)

    def test_optional_fields(self):
        """Test that optional fields work correctly."""
        # Minimal valid item
        item = DirectoryItem(
            name="test",
            path="/test/path",
            is_directory=False
        )
        
        assert item.size is None
        assert item.modified_at is None


class TestDirectoryBrowseResponseSchema:
    """Test DirectoryBrowseResponse schema validation."""

    def test_valid_browse_response(self):
        """Test creation of valid browse response."""
        items = [
            DirectoryItem(name="dir1", path="/test/dir1", is_directory=True),
            DirectoryItem(name="file1.txt", path="/test/file1.txt", is_directory=False, size=100)
        ]
        
        response = DirectoryBrowseResponse(
            current_path="/test",
            parent_path="/",
            items=items,
            total_items=2
        )
        
        assert response.current_path == "/test"
        assert response.parent_path == "/"
        assert len(response.items) == 2
        assert response.total_items == 2

    def test_empty_items_list(self):
        """Test browse response with empty items list."""
        response = DirectoryBrowseResponse(
            current_path="/empty",
            parent_path="/",
            items=[],
            total_items=0
        )
        
        assert len(response.items) == 0
        assert response.total_items == 0

    def test_optional_parent_path(self):
        """Test that parent_path is optional (for root directory)."""
        response = DirectoryBrowseResponse(
            current_path="/",
            parent_path=None,
            items=[],
            total_items=0
        )
        
        assert response.parent_path is None


class TestPathValidationResultSchema:
    """Test PathValidationResult schema validation."""

    def test_valid_validation_result(self):
        """Test creation of valid validation results."""
        # Valid path result
        result = PathValidationResult(
            is_valid=True,
            exists=True,
            is_directory=True,
            is_readable=True,
            is_writable=True,
            error_message=None,
            total_space=1000000000,
            free_space=500000000
        )
        
        assert result.is_valid is True
        assert result.total_space == 1000000000
        
        # Invalid path result
        invalid_result = PathValidationResult(
            is_valid=False,
            exists=False,
            is_directory=False,
            is_readable=False,
            is_writable=False,
            error_message="Path does not exist",
            total_space=None,
            free_space=None
        )
        
        assert invalid_result.is_valid is False
        assert invalid_result.error_message == "Path does not exist"

    def test_boolean_fields_required(self):
        """Test that boolean fields are required."""
        with pytest.raises(ValidationError):
            PathValidationResult(
                # Missing required boolean fields
                error_message=None,
                total_space=None,
                free_space=None
            )

    def test_optional_fields(self):
        """Test that optional fields work correctly."""
        result = PathValidationResult(
            is_valid=False,
            exists=False,
            is_directory=False,
            is_readable=False,
            is_writable=False
            # Optional fields not provided
        )
        
        assert result.error_message is None
        assert result.total_space is None
        assert result.free_space is None


class TestStorageInfoSchema:
    """Test StorageInfo schema validation."""

    def test_valid_storage_info(self):
        """Test creation of valid storage info."""
        storage = StorageInfo(
            total_space=1000000000,
            used_space=600000000,
            free_space=400000000,
            usage_percentage=60.0
        )
        
        assert storage.total_space == 1000000000
        assert storage.used_space == 600000000
        assert storage.free_space == 400000000
        assert storage.usage_percentage == 60.0

    def test_all_fields_required(self):
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            StorageInfo(
                total_space=1000000000,
                used_space=600000000
                # Missing free_space and usage_percentage
            )

    def test_numeric_field_types(self):
        """Test that numeric fields accept appropriate types."""
        # Integer values
        storage1 = StorageInfo(
            total_space=1000,
            used_space=600,
            free_space=400,
            usage_percentage=60
        )
        
        assert isinstance(storage1.usage_percentage, float)
        
        # Float values
        storage2 = StorageInfo(
            total_space=1000.0,
            used_space=600.5,
            free_space=399.5,
            usage_percentage=60.05
        )
        
        assert storage2.used_space == 600.5
        assert storage2.usage_percentage == 60.05

    def test_negative_values_allowed(self):
        """Test that the schema allows negative values (edge cases)."""
        # Some filesystems might report unusual values
        storage = StorageInfo(
            total_space=1000,
            used_space=-10,  # Unusual but possible
            free_space=1010,
            usage_percentage=-1.0
        )
        
        assert storage.used_space == -10
        assert storage.usage_percentage == -1.0


class TestSchemaEdgeCases:
    """Test edge cases and error scenarios across schemas."""

    def test_unicode_handling_in_names_and_paths(self):
        """Test that schemas handle unicode characters correctly."""
        # Unicode in name
        path = LibraryPathBase(
            name="日本語 Library",
            path="/home/user/漫画"
        )
        
        assert path.name == "日本語 Library"
        assert path.path == "/home/user/漫画"

    def test_very_large_numeric_values(self):
        """Test schemas with very large numeric values."""
        import sys
        
        # Very large storage values (exabytes)
        large_value = sys.maxsize
        
        storage = StorageInfo(
            total_space=large_value,
            used_space=large_value // 2,
            free_space=large_value // 2,
            usage_percentage=50.0
        )
        
        assert storage.total_space == large_value

    def test_schema_serialization(self):
        """Test that schemas can be serialized to dict/JSON."""
        path = LibraryPathCreate(
            name="Test Library",
            path="/test/path",
            priority=5
        )
        
        # Should be able to convert to dict
        path_dict = path.dict()
        assert path_dict["name"] == "Test Library"
        assert path_dict["path"] == "/test/path"
        assert path_dict["priority"] == 5
        
        # Should be able to recreate from dict
        path_recreated = LibraryPathCreate(**path_dict)
        assert path_recreated.name == path.name
        assert path_recreated.path == path.path

    def test_field_aliases_and_descriptions(self):
        """Test that field descriptions and metadata are preserved."""
        # Access field info to verify descriptions are present
        path_fields = LibraryPathBase.__fields__
        
        assert "description" in path_fields["name"].field_info.extra
        assert "description" in path_fields["path"].field_info.extra
        
        # Verify field constraints
        assert path_fields["name"].field_info.max_length == 255
        assert path_fields["path"].field_info.max_length == 1000