import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserUpdate


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
def user_repository(db_session):
    """Create a user repository instance."""
    return UserRepository(db_session)


@pytest.fixture
def sample_user_create():
    """Sample user creation data."""
    return UserCreate(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        password="testpassword123"
    )


class TestUserRepository:
    """Test cases for UserRepository."""

    def test_create_user_success(self, user_repository, sample_user_create):
        """Test successful user creation."""
        hashed_password = "hashed_password_123"
        
        user = user_repository.create_user(sample_user_create, hashed_password)
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.hashed_password == hashed_password
        assert user.is_active is True
        assert user.is_superuser is False
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_create_user_duplicate_username(self, user_repository, sample_user_create):
        """Test user creation with duplicate username fails."""
        hashed_password = "hashed_password_123"
        
        # Create first user
        user_repository.create_user(sample_user_create, hashed_password)
        
        # Try to create second user with same username
        duplicate_user = UserCreate(
            username="testuser",  # Same username
            email="different@example.com",
            password="differentpassword"
        )
        
        with pytest.raises(ValueError, match="Username 'testuser' already exists"):
            user_repository.create_user(duplicate_user, hashed_password)

    def test_create_user_duplicate_email(self, user_repository, sample_user_create):
        """Test user creation with duplicate email fails."""
        hashed_password = "hashed_password_123"
        
        # Create first user
        user_repository.create_user(sample_user_create, hashed_password)
        
        # Try to create second user with same email
        duplicate_user = UserCreate(
            username="differentuser",
            email="test@example.com",  # Same email
            password="differentpassword"
        )
        
        with pytest.raises(ValueError, match="Email 'test@example.com' already exists"):
            user_repository.create_user(duplicate_user, hashed_password)

    def test_get_user_by_id(self, user_repository, sample_user_create):
        """Test getting user by ID."""
        hashed_password = "hashed_password_123"
        created_user = user_repository.create_user(sample_user_create, hashed_password)
        
        retrieved_user = user_repository.get_user_by_id(created_user.id)
        
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.username == "testuser"

    def test_get_user_by_id_not_found(self, user_repository):
        """Test getting user by non-existent ID returns None."""
        user = user_repository.get_user_by_id(999)
        assert user is None

    def test_get_user_by_username(self, user_repository, sample_user_create):
        """Test getting user by username."""
        hashed_password = "hashed_password_123"
        user_repository.create_user(sample_user_create, hashed_password)
        
        retrieved_user = user_repository.get_user_by_username("testuser")
        
        assert retrieved_user is not None
        assert retrieved_user.username == "testuser"
        assert retrieved_user.email == "test@example.com"

    def test_get_user_by_username_not_found(self, user_repository):
        """Test getting user by non-existent username returns None."""
        user = user_repository.get_user_by_username("nonexistent")
        assert user is None

    def test_get_user_by_email(self, user_repository, sample_user_create):
        """Test getting user by email."""
        hashed_password = "hashed_password_123"
        user_repository.create_user(sample_user_create, hashed_password)
        
        retrieved_user = user_repository.get_user_by_email("test@example.com")
        
        assert retrieved_user is not None
        assert retrieved_user.email == "test@example.com"
        assert retrieved_user.username == "testuser"

    def test_update_user(self, user_repository, sample_user_create):
        """Test updating user information."""
        hashed_password = "hashed_password_123"
        created_user = user_repository.create_user(sample_user_create, hashed_password)
        
        update_data = UserUpdate(
            email="updated@example.com",
            full_name="Updated User",
            is_active=False
        )
        
        updated_user = user_repository.update_user(created_user.id, update_data)
        
        assert updated_user is not None
        assert updated_user.email == "updated@example.com"
        assert updated_user.full_name == "Updated User"
        assert updated_user.is_active is False
        assert updated_user.username == "testuser"  # Should not change

    def test_update_user_not_found(self, user_repository):
        """Test updating non-existent user returns None."""
        update_data = UserUpdate(email="updated@example.com")
        result = user_repository.update_user(999, update_data)
        assert result is None

    def test_delete_user(self, user_repository, sample_user_create):
        """Test deleting user."""
        hashed_password = "hashed_password_123"
        created_user = user_repository.create_user(sample_user_create, hashed_password)
        
        # Delete the user
        result = user_repository.delete_user(created_user.id)
        assert result is True
        
        # Verify user is deleted
        retrieved_user = user_repository.get_user_by_id(created_user.id)
        assert retrieved_user is None

    def test_delete_user_not_found(self, user_repository):
        """Test deleting non-existent user returns False."""
        result = user_repository.delete_user(999)
        assert result is False

    def test_is_username_taken(self, user_repository, sample_user_create):
        """Test checking if username is taken."""
        hashed_password = "hashed_password_123"
        
        # Username should not be taken initially
        assert user_repository.is_username_taken("testuser") is False
        
        # Create user
        user_repository.create_user(sample_user_create, hashed_password)
        
        # Username should now be taken
        assert user_repository.is_username_taken("testuser") is True

    def test_is_email_taken(self, user_repository, sample_user_create):
        """Test checking if email is taken."""
        hashed_password = "hashed_password_123"
        
        # Email should not be taken initially
        assert user_repository.is_email_taken("test@example.com") is False
        
        # Create user
        user_repository.create_user(sample_user_create, hashed_password)
        
        # Email should now be taken
        assert user_repository.is_email_taken("test@example.com") is True

    def test_activate_deactivate_user(self, user_repository, sample_user_create):
        """Test activating and deactivating user."""
        hashed_password = "hashed_password_123"
        created_user = user_repository.create_user(sample_user_create, hashed_password)
        
        # User should be active by default
        assert created_user.is_active is True
        
        # Deactivate user
        deactivated_user = user_repository.deactivate_user(created_user.id)
        assert deactivated_user.is_active is False
        
        # Activate user
        activated_user = user_repository.activate_user(created_user.id)
        assert activated_user.is_active is True

    def test_get_active_users_count(self, user_repository, sample_user_create):
        """Test getting count of active users."""
        hashed_password = "hashed_password_123"
        
        # Initially no users
        assert user_repository.get_active_users_count() == 0
        
        # Create active user
        created_user = user_repository.create_user(sample_user_create, hashed_password)
        assert user_repository.get_active_users_count() == 1
        
        # Deactivate user
        user_repository.deactivate_user(created_user.id)
        assert user_repository.get_active_users_count() == 0