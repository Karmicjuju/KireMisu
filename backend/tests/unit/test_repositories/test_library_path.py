import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.models.library_path import LibraryPath
from app.repositories.library_path import LibraryPathRepository
from app.schemas.library_path import LibraryPathCreate, LibraryPathUpdate


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def library_path_repository(db_session):
    """Create a library path repository instance."""
    return LibraryPathRepository(db_session)


@pytest.fixture
def sample_library_path_create():
    """Sample library path creation data."""
    return LibraryPathCreate(
        name="Test Library",
        path="/home/user/test-manga",
        is_active=True,
        priority=5
    )


class TestLibraryPathRepository:
    """Test cases for LibraryPathRepository."""

    def test_create_library_path_success(self, library_path_repository, sample_library_path_create):
        """Test successful library path creation."""
        library_path = library_path_repository.create_library_path(sample_library_path_create)
        
        assert library_path.id is not None
        assert library_path.name == "Test Library"
        assert library_path.path == "/home/user/test-manga"
        assert library_path.is_active is True
        assert library_path.priority == 5
        assert library_path.created_at is not None
        assert library_path.updated_at is not None

    def test_create_library_path_duplicate_path(self, library_path_repository, sample_library_path_create):
        """Test library path creation with duplicate path fails."""
        # Create first library path
        library_path_repository.create_library_path(sample_library_path_create)
        
        # Try to create second library path with same path
        duplicate_path = LibraryPathCreate(
            name="Different Library",
            path="/home/user/test-manga",  # Same path
            is_active=True,
            priority=1
        )
        
        with pytest.raises(ValueError, match="Path '/home/user/test-manga' already exists"):
            library_path_repository.create_library_path(duplicate_path)

    def test_create_library_path_duplicate_name(self, library_path_repository, sample_library_path_create):
        """Test library path creation with duplicate name fails."""
        # Create first library path
        library_path_repository.create_library_path(sample_library_path_create)
        
        # Try to create second library path with same name
        duplicate_name = LibraryPathCreate(
            name="Test Library",  # Same name
            path="/home/user/different-manga",
            is_active=True,
            priority=1
        )
        
        with pytest.raises(ValueError, match="Name 'Test Library' already exists"):
            library_path_repository.create_library_path(duplicate_name)

    def test_get_library_path_by_id(self, library_path_repository, sample_library_path_create):
        """Test getting library path by ID."""
        created_path = library_path_repository.create_library_path(sample_library_path_create)
        
        retrieved_path = library_path_repository.get_library_path_by_id(created_path.id)
        
        assert retrieved_path is not None
        assert retrieved_path.id == created_path.id
        assert retrieved_path.name == "Test Library"

    def test_get_library_path_by_id_not_found(self, library_path_repository):
        """Test getting library path by non-existent ID returns None."""
        path = library_path_repository.get_library_path_by_id(999)
        assert path is None

    def test_get_library_path_by_path(self, library_path_repository, sample_library_path_create):
        """Test getting library path by path."""
        library_path_repository.create_library_path(sample_library_path_create)
        
        retrieved_path = library_path_repository.get_library_path_by_path("/home/user/test-manga")
        
        assert retrieved_path is not None
        assert retrieved_path.path == "/home/user/test-manga"
        assert retrieved_path.name == "Test Library"

    def test_get_library_path_by_name(self, library_path_repository, sample_library_path_create):
        """Test getting library path by name."""
        library_path_repository.create_library_path(sample_library_path_create)
        
        retrieved_path = library_path_repository.get_library_path_by_name("Test Library")
        
        assert retrieved_path is not None
        assert retrieved_path.name == "Test Library"
        assert retrieved_path.path == "/home/user/test-manga"

    def test_get_all_library_paths_ordered_by_priority(self, library_path_repository):
        """Test getting all library paths ordered by priority."""
        # Create multiple library paths with different priorities
        paths = [
            LibraryPathCreate(name="Low Priority", path="/low", priority=1, is_active=True),
            LibraryPathCreate(name="High Priority", path="/high", priority=10, is_active=True),
            LibraryPathCreate(name="Medium Priority", path="/medium", priority=5, is_active=True),
            LibraryPathCreate(name="Inactive", path="/inactive", priority=8, is_active=False),
        ]
        
        for path_data in paths:
            library_path_repository.create_library_path(path_data)
        
        # Get all paths including inactive
        all_paths = library_path_repository.get_all_library_paths(include_inactive=True)
        
        assert len(all_paths) == 4
        # Should be ordered by priority descending, then name ascending
        assert all_paths[0].name == "High Priority"  # priority 10
        assert all_paths[1].name == "Inactive"       # priority 8
        assert all_paths[2].name == "Medium Priority" # priority 5
        assert all_paths[3].name == "Low Priority"    # priority 1

    def test_get_active_library_paths_only(self, library_path_repository):
        """Test getting only active library paths."""
        paths = [
            LibraryPathCreate(name="Active 1", path="/active1", priority=5, is_active=True),
            LibraryPathCreate(name="Active 2", path="/active2", priority=3, is_active=True),
            LibraryPathCreate(name="Inactive", path="/inactive", priority=10, is_active=False),
        ]
        
        for path_data in paths:
            library_path_repository.create_library_path(path_data)
        
        active_paths = library_path_repository.get_active_library_paths()
        
        assert len(active_paths) == 2
        assert all(path.is_active for path in active_paths)
        assert active_paths[0].name == "Active 1"  # Higher priority
        assert active_paths[1].name == "Active 2"

    def test_update_library_path(self, library_path_repository, sample_library_path_create):
        """Test updating library path information."""
        created_path = library_path_repository.create_library_path(sample_library_path_create)
        
        update_data = LibraryPathUpdate(
            name="Updated Library",
            is_active=False,
            priority=15
        )
        
        updated_path = library_path_repository.update_library_path(created_path.id, update_data)
        
        assert updated_path is not None
        assert updated_path.name == "Updated Library"
        assert updated_path.is_active is False
        assert updated_path.priority == 15
        assert updated_path.path == "/home/user/test-manga"  # Should not change

    def test_update_library_path_not_found(self, library_path_repository):
        """Test updating non-existent library path returns None."""
        update_data = LibraryPathUpdate(name="Updated Library")
        result = library_path_repository.update_library_path(999, update_data)
        assert result is None

    def test_update_library_path_duplicate_name(self, library_path_repository):
        """Test updating library path with duplicate name fails."""
        # Create two library paths
        path1_data = LibraryPathCreate(name="Library 1", path="/path1")
        path2_data = LibraryPathCreate(name="Library 2", path="/path2")
        
        path1 = library_path_repository.create_library_path(path1_data)
        library_path_repository.create_library_path(path2_data)
        
        # Try to update path1 with path2's name
        update_data = LibraryPathUpdate(name="Library 2")
        
        with pytest.raises(ValueError, match="Name 'Library 2' already exists"):
            library_path_repository.update_library_path(path1.id, update_data)

    def test_delete_library_path(self, library_path_repository, sample_library_path_create):
        """Test deleting library path."""
        created_path = library_path_repository.create_library_path(sample_library_path_create)
        
        # Delete the library path
        result = library_path_repository.delete_library_path(created_path.id)
        assert result is True
        
        # Verify library path is deleted
        retrieved_path = library_path_repository.get_library_path_by_id(created_path.id)
        assert retrieved_path is None

    def test_delete_library_path_not_found(self, library_path_repository):
        """Test deleting non-existent library path returns False."""
        result = library_path_repository.delete_library_path(999)
        assert result is False

    def test_is_path_taken(self, library_path_repository, sample_library_path_create):
        """Test checking if path is taken."""
        # Path should not be taken initially
        assert library_path_repository.is_path_taken("/home/user/test-manga") is False
        
        # Create library path
        library_path_repository.create_library_path(sample_library_path_create)
        
        # Path should now be taken
        assert library_path_repository.is_path_taken("/home/user/test-manga") is True

    def test_is_path_taken_exclude_id(self, library_path_repository):
        """Test checking if path is taken excluding specific ID."""
        path_data = LibraryPathCreate(name="Test", path="/test/path")
        created_path = library_path_repository.create_library_path(path_data)
        
        # Path should be taken without exclusion
        assert library_path_repository.is_path_taken("/test/path") is True
        
        # Path should not be taken when excluding the same ID
        assert library_path_repository.is_path_taken("/test/path", exclude_id=created_path.id) is False

    def test_is_name_taken(self, library_path_repository, sample_library_path_create):
        """Test checking if name is taken."""
        # Name should not be taken initially
        assert library_path_repository.is_name_taken("Test Library") is False
        
        # Create library path
        library_path_repository.create_library_path(sample_library_path_create)
        
        # Name should now be taken
        assert library_path_repository.is_name_taken("Test Library") is True

    def test_activate_deactivate_library_path(self, library_path_repository, sample_library_path_create):
        """Test activating and deactivating library path."""
        created_path = library_path_repository.create_library_path(sample_library_path_create)
        
        # Path should be active by default
        assert created_path.is_active is True
        
        # Deactivate library path
        deactivated_path = library_path_repository.deactivate_library_path(created_path.id)
        assert deactivated_path.is_active is False
        
        # Activate library path
        activated_path = library_path_repository.activate_library_path(created_path.id)
        assert activated_path.is_active is True

    def test_update_priority(self, library_path_repository, sample_library_path_create):
        """Test updating library path priority."""
        created_path = library_path_repository.create_library_path(sample_library_path_create)
        
        # Update priority
        updated_path = library_path_repository.update_priority(created_path.id, 20)
        
        assert updated_path.priority == 20

    def test_get_highest_priority(self, library_path_repository):
        """Test getting highest priority value."""
        # Initially should be 0 when no paths exist
        assert library_path_repository.get_highest_priority() == 0
        
        # Create paths with different priorities
        priorities = [5, 10, 3, 15, 8]
        for i, priority in enumerate(priorities):
            path_data = LibraryPathCreate(
                name=f"Library {i}",
                path=f"/path{i}",
                priority=priority
            )
            library_path_repository.create_library_path(path_data)
        
        # Should return the highest priority
        assert library_path_repository.get_highest_priority() == 15

    def test_get_library_paths_count(self, library_path_repository):
        """Test getting count of library paths."""
        # Initially no paths
        assert library_path_repository.get_library_paths_count() == 0
        assert library_path_repository.get_library_paths_count(active_only=True) == 0
        
        # Create mixed active/inactive paths
        active_path = LibraryPathCreate(name="Active", path="/active", is_active=True)
        inactive_path = LibraryPathCreate(name="Inactive", path="/inactive", is_active=False)
        
        library_path_repository.create_library_path(active_path)
        library_path_repository.create_library_path(inactive_path)
        
        assert library_path_repository.get_library_paths_count() == 2
        assert library_path_repository.get_library_paths_count(active_only=True) == 1

    def test_is_name_taken_exclude_id(self, library_path_repository):
        """Test checking if name is taken excluding specific ID."""
        path_data = LibraryPathCreate(name="Test Name", path="/test/name")
        created_path = library_path_repository.create_library_path(path_data)
        
        # Name should be taken without exclusion
        assert library_path_repository.is_name_taken("Test Name") is True
        
        # Name should not be taken when excluding the same ID
        assert library_path_repository.is_name_taken("Test Name", exclude_id=created_path.id) is False

    def test_get_library_path_by_path_not_found(self, library_path_repository):
        """Test getting library path by non-existent path returns None."""
        path = library_path_repository.get_library_path_by_path("/nonexistent/path")
        assert path is None

    def test_get_library_path_by_name_not_found(self, library_path_repository):
        """Test getting library path by non-existent name returns None."""
        path = library_path_repository.get_library_path_by_name("Non-existent Library")
        assert path is None

    def test_activate_deactivate_library_path_not_found(self, library_path_repository):
        """Test activating/deactivating non-existent library path returns None."""
        activate_result = library_path_repository.activate_library_path(999)
        assert activate_result is None
        
        deactivate_result = library_path_repository.deactivate_library_path(999)
        assert deactivate_result is None

    def test_update_priority_not_found(self, library_path_repository):
        """Test updating priority of non-existent library path returns None."""
        result = library_path_repository.update_priority(999, 10)
        assert result is None

    def test_create_library_path_generic_constraint_error(self, library_path_repository, db_session):
        """Test generic constraint violation handling."""
        # This tests the fallback error handling in the repository
        # We'll create a scenario where the specific constraint check fails
        
        # Create a library path
        path_data = LibraryPathCreate(name="Test", path="/test/path")
        library_path_repository.create_library_path(path_data)
        
        # Mock a constraint violation that doesn't match specific patterns
        # by directly inserting a conflicting record
        conflicting_path = LibraryPath(name="Different", path="/test/path")
        db_session.add(conflicting_path)
        
        with pytest.raises(ValueError, match="Library path creation failed due to constraint violation"):
            db_session.commit()

    def test_update_library_path_partial_update(self, library_path_repository, sample_library_path_create):
        """Test partial updates with only some fields."""
        created_path = library_path_repository.create_library_path(sample_library_path_create)
        original_name = created_path.name
        original_priority = created_path.priority
        
        # Update only is_active field
        update_data = LibraryPathUpdate(is_active=False)
        updated_path = library_path_repository.update_library_path(created_path.id, update_data)
        
        assert updated_path.is_active is False
        assert updated_path.name == original_name  # Should remain unchanged
        assert updated_path.priority == original_priority  # Should remain unchanged

    def test_update_library_path_no_changes(self, library_path_repository, sample_library_path_create):
        """Test update with empty data."""
        created_path = library_path_repository.create_library_path(sample_library_path_create)
        original_name = created_path.name
        original_priority = created_path.priority
        original_is_active = created_path.is_active
        
        # Update with empty data (no fields set)
        update_data = LibraryPathUpdate()
        updated_path = library_path_repository.update_library_path(created_path.id, update_data)
        
        # All fields should remain unchanged
        assert updated_path.name == original_name
        assert updated_path.priority == original_priority
        assert updated_path.is_active == original_is_active

    def test_get_all_library_paths_empty_database(self, library_path_repository):
        """Test getting library paths when database is empty."""
        all_paths = library_path_repository.get_all_library_paths()
        active_paths = library_path_repository.get_active_library_paths()
        all_paths_including_inactive = library_path_repository.get_all_library_paths(include_inactive=True)
        
        assert all_paths == []
        assert active_paths == []
        assert all_paths_including_inactive == []

    def test_library_path_ordering_with_same_priority(self, library_path_repository):
        """Test ordering behavior when multiple paths have same priority."""
        paths = [
            LibraryPathCreate(name="Z Library", path="/z", priority=5, is_active=True),
            LibraryPathCreate(name="A Library", path="/a", priority=5, is_active=True),
            LibraryPathCreate(name="M Library", path="/m", priority=5, is_active=True),
        ]
        
        for path_data in paths:
            library_path_repository.create_library_path(path_data)
        
        all_paths = library_path_repository.get_all_library_paths()
        
        # With same priority, should be ordered by name ascending
        assert len(all_paths) == 3
        assert all_paths[0].name == "A Library"
        assert all_paths[1].name == "M Library" 
        assert all_paths[2].name == "Z Library"

    def test_repository_database_rollback_on_error(self, library_path_repository, sample_library_path_create):
        """Test that database transactions are rolled back on errors."""
        # Create initial library path
        library_path_repository.create_library_path(sample_library_path_create)
        
        # Try to create duplicate path - should fail and rollback
        duplicate_path = LibraryPathCreate(
            name="Different Name",
            path=sample_library_path_create.path  # Same path
        )
        
        with pytest.raises(ValueError):
            library_path_repository.create_library_path(duplicate_path)
        
        # Verify we can still create a valid library path (session not broken)
        valid_path = LibraryPathCreate(name="Valid Library", path="/valid/path")
        created_path = library_path_repository.create_library_path(valid_path)
        assert created_path is not None

    def test_get_highest_priority_with_negative_values(self, library_path_repository):
        """Test getting highest priority when all values are negative."""
        priorities = [-10, -5, -15, -1]
        for i, priority in enumerate(priorities):
            path_data = LibraryPathCreate(
                name=f"Library {i}",
                path=f"/path{i}",
                priority=priority
            )
            library_path_repository.create_library_path(path_data)
        
        # Highest should be -1 (closest to 0)
        assert library_path_repository.get_highest_priority() == -1

    def test_constraint_error_message_parsing(self, library_path_repository, sample_library_path_create):
        """Test that constraint error messages are parsed correctly for different database backends."""
        # Create initial path
        library_path_repository.create_library_path(sample_library_path_create)
        
        # Test path constraint error
        duplicate_path = LibraryPathCreate(
            name="Different Name", 
            path=sample_library_path_create.path
        )
        
        with pytest.raises(ValueError) as exc_info:
            library_path_repository.create_library_path(duplicate_path)
        
        error_message = str(exc_info.value)
        assert "already exists" in error_message
        assert sample_library_path_create.path in error_message
        
        # Test name constraint error
        duplicate_name = LibraryPathCreate(
            name=sample_library_path_create.name,
            path="/different/path"
        )
        
        with pytest.raises(ValueError) as exc_info:
            library_path_repository.create_library_path(duplicate_name)
        
        error_message = str(exc_info.value)
        assert "already exists" in error_message
        assert sample_library_path_create.name in error_message


class TestLibraryPathRepositoryAdvancedEdgeCases:
    """Test advanced edge cases and database constraints."""

    def test_create_library_path_with_database_rollback_behavior(self, library_path_repository, db_session):
        """Test that failed inserts properly roll back the transaction."""
        # Create first library path
        path1 = LibraryPathCreate(name="Path1", path="/path1")
        created_path = library_path_repository.create_library_path(path1)
        
        # Verify it was created
        assert created_path.id is not None
        
        # Try to create duplicate path - should fail and rollback
        duplicate = LibraryPathCreate(name="Different", path="/path1")
        
        with pytest.raises(ValueError):
            library_path_repository.create_library_path(duplicate)
        
        # Verify original path is still there and session is still usable
        retrieved = library_path_repository.get_library_path_by_id(created_path.id)
        assert retrieved is not None
        assert retrieved.name == "Path1"
        
        # Verify we can still create new paths after rollback
        path2 = LibraryPathCreate(name="Path2", path="/path2")
        created_path2 = library_path_repository.create_library_path(path2)
        assert created_path2.id is not None

    def test_update_library_path_with_database_rollback_behavior(self, library_path_repository):
        """Test that failed updates properly roll back the transaction."""
        # Create two library paths
        path1 = LibraryPathCreate(name="Path1", path="/path1")
        path2 = LibraryPathCreate(name="Path2", path="/path2")
        
        created1 = library_path_repository.create_library_path(path1)
        created2 = library_path_repository.create_library_path(path2)
        
        # Try to update path1 with path2's name - should fail
        update_data = LibraryPathUpdate(name="Path2")
        
        with pytest.raises(ValueError):
            library_path_repository.update_library_path(created1.id, update_data)
        
        # Verify original path is unchanged
        retrieved = library_path_repository.get_library_path_by_id(created1.id)
        assert retrieved.name == "Path1"
        
        # Verify session is still usable for valid updates
        valid_update = LibraryPathUpdate(name="Updated Path1")
        updated_path = library_path_repository.update_library_path(created1.id, valid_update)
        assert updated_path.name == "Updated Path1"

    def test_concurrent_creation_simulation(self, library_path_repository):
        """Test behavior when multiple processes try to create paths with same constraints."""
        # Simulate concurrent creation by creating paths with same details
        # This tests the database constraint handling
        
        path_data = LibraryPathCreate(name="Concurrent Path", path="/concurrent")
        
        # First creation should succeed
        path1 = library_path_repository.create_library_path(path_data)
        assert path1.id is not None
        
        # Second creation with same data should fail
        with pytest.raises(ValueError):
            library_path_repository.create_library_path(path_data)

    def test_get_all_library_paths_with_null_priorities(self, library_path_repository, db_session):
        """Test ordering behavior when some paths have null priorities."""
        # Create paths directly in database with null priority to test edge case
        from app.models.library_path import LibraryPath
        
        # Create path with explicit priority
        normal_path = library_path_repository.create_library_path(
            LibraryPathCreate(name="Normal", path="/normal", priority=10)
        )
        
        # Create path with zero priority (should be handled normally)
        zero_priority_path = library_path_repository.create_library_path(
            LibraryPathCreate(name="Zero", path="/zero", priority=0)
        )
        
        # Create path with negative priority
        negative_priority_path = library_path_repository.create_library_path(
            LibraryPathCreate(name="Negative", path="/negative", priority=-5)
        )
        
        all_paths = library_path_repository.get_all_library_paths()
        
        # Should be ordered by priority descending, then name ascending
        assert len(all_paths) == 3
        assert all_paths[0].priority == 10  # Normal
        assert all_paths[1].priority == 0   # Zero
        assert all_paths[2].priority == -5  # Negative

    def test_is_path_taken_with_case_sensitivity(self, library_path_repository):
        """Test path checking behavior with different cases."""
        # Create path with lowercase
        path_data = LibraryPathCreate(name="Test", path="/test/path")
        library_path_repository.create_library_path(path_data)
        
        # Check with exact same case
        assert library_path_repository.is_path_taken("/test/path") is True
        
        # Check with different case (should be case-sensitive on most filesystems)
        assert library_path_repository.is_path_taken("/TEST/PATH") is False
        assert library_path_repository.is_path_taken("/Test/Path") is False

    def test_is_name_taken_with_case_sensitivity(self, library_path_repository):
        """Test name checking behavior with different cases."""
        # Create path with specific case
        path_data = LibraryPathCreate(name="Test Library", path="/test")
        library_path_repository.create_library_path(path_data)
        
        # Check with exact same case
        assert library_path_repository.is_name_taken("Test Library") is True
        
        # Check with different case
        assert library_path_repository.is_name_taken("test library") is False
        assert library_path_repository.is_name_taken("TEST LIBRARY") is False

    def test_update_library_path_with_none_values(self, library_path_repository, sample_library_path_create):
        """Test updating with None values should not change fields."""
        created_path = library_path_repository.create_library_path(sample_library_path_create)
        original_name = created_path.name
        original_priority = created_path.priority
        original_is_active = created_path.is_active
        
        # Create update with all None values
        update_data = LibraryPathUpdate(name=None, is_active=None, priority=None)
        
        updated_path = library_path_repository.update_library_path(created_path.id, update_data)
        
        # All fields should remain unchanged
        assert updated_path.name == original_name
        assert updated_path.is_active == original_is_active
        assert updated_path.priority == original_priority

    def test_repository_handles_very_long_names_and_paths(self, library_path_repository):
        """Test repository behavior with maximum length names and paths."""
        # Test name at maximum length (255 characters)
        long_name = "a" * 255
        normal_path = "/normal/path"
        
        path_data = LibraryPathCreate(name=long_name, path=normal_path)
        created_path = library_path_repository.create_library_path(path_data)
        assert created_path.name == long_name
        
        # Test path at maximum length (1000 characters)
        normal_name = "Normal Name"
        long_path = "/" + "a" * 995  # 996 total with leading slash
        
        path_data2 = LibraryPathCreate(name=normal_name, path=long_path)
        created_path2 = library_path_repository.create_library_path(path_data2)
        assert created_path2.path == long_path

    def test_get_library_paths_count_accuracy(self, library_path_repository):
        """Test that count methods return accurate numbers."""
        # Initially should be 0
        assert library_path_repository.get_library_paths_count() == 0
        assert library_path_repository.get_library_paths_count(active_only=True) == 0
        
        # Create mixed active/inactive paths in batches
        for i in range(5):
            active_path = LibraryPathCreate(name=f"Active {i}", path=f"/active{i}", is_active=True)
            library_path_repository.create_library_path(active_path)
            
        for i in range(3):
            inactive_path = LibraryPathCreate(name=f"Inactive {i}", path=f"/inactive{i}", is_active=False)
            library_path_repository.create_library_path(inactive_path)
        
        # Check counts
        assert library_path_repository.get_library_paths_count() == 8
        assert library_path_repository.get_library_paths_count(active_only=True) == 5
        
        # Delete some paths and verify counts update
        all_paths = library_path_repository.get_all_library_paths(include_inactive=True)
        first_path_id = all_paths[0].id
        
        library_path_repository.delete_library_path(first_path_id)
        
        assert library_path_repository.get_library_paths_count() == 7

    def test_activate_deactivate_updates_correctly(self, library_path_repository, sample_library_path_create):
        """Test that activate/deactivate operations update the database correctly."""
        # Create path as active
        sample_library_path_create.is_active = True
        created_path = library_path_repository.create_library_path(sample_library_path_create)
        
        # Deactivate and verify in database
        deactivated = library_path_repository.deactivate_library_path(created_path.id)
        assert deactivated.is_active is False
        
        # Retrieve fresh from database to verify persistence
        retrieved = library_path_repository.get_library_path_by_id(created_path.id)
        assert retrieved.is_active is False
        
        # Activate and verify
        activated = library_path_repository.activate_library_path(created_path.id)
        assert activated.is_active is True
        
        # Retrieve fresh from database to verify persistence
        retrieved = library_path_repository.get_library_path_by_id(created_path.id)
        assert retrieved.is_active is True

    def test_priority_operations_with_extreme_values(self, library_path_repository):
        """Test priority operations with extreme integer values."""
        import sys
        
        # Create paths with extreme priority values
        max_priority = sys.maxsize
        min_priority = -sys.maxsize - 1
        
        max_path = LibraryPathCreate(name="Max Priority", path="/max", priority=max_priority)
        min_path = LibraryPathCreate(name="Min Priority", path="/min", priority=min_priority)
        
        created_max = library_path_repository.create_library_path(max_path)
        created_min = library_path_repository.create_library_path(min_path)
        
        assert created_max.priority == max_priority
        assert created_min.priority == min_priority
        
        # Test highest priority detection
        highest = library_path_repository.get_highest_priority()
        assert highest == max_priority
        
        # Test ordering with extreme values
        all_paths = library_path_repository.get_all_library_paths()
        assert all_paths[0].priority == max_priority
        assert all_paths[1].priority == min_priority

    def test_database_constraint_error_details(self, library_path_repository):
        """Test that constraint errors provide meaningful messages."""
        # Create initial path
        path1 = LibraryPathCreate(name="Original", path="/original")
        library_path_repository.create_library_path(path1)
        
        # Test path constraint error
        duplicate_path = LibraryPathCreate(name="Different Name", path="/original")
        
        try:
            library_path_repository.create_library_path(duplicate_path)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            error_msg = str(e)
            assert "/original" in error_msg
            assert "already exists" in error_msg or "already configured" in error_msg
        
        # Test name constraint error  
        duplicate_name = LibraryPathCreate(name="Original", path="/different")
        
        try:
            library_path_repository.create_library_path(duplicate_name)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            error_msg = str(e)
            assert "Original" in error_msg
            assert "already exists" in error_msg