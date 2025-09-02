#!/usr/bin/env python3
"""
Simple test script to verify the authentication system works.
This tests the database-backed user authentication without requiring pytest.
"""

import sys
import os
from datetime import timedelta

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.db.database import SessionLocal, engine
from app.models.user import Base
from app.services.user import UserService
from app.schemas.user import UserCreate


def test_authentication():
    """Test the complete authentication flow."""
    print("🧪 Testing Authentication System")
    print("=" * 40)
    
    # Create tables
    print("1. Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("   ✅ Tables created")
    
    # Create database session
    db = SessionLocal()
    user_service = UserService(db)
    
    try:
        # Test user creation
        print("2. Testing user creation...")
        test_user = UserCreate(
            username="testadmin",
            password="testpass123",
            email="test@example.com",
            full_name="Test Administrator"
        )
        
        # Clean up any existing test user
        existing_user = user_service.get_user_by_username("testadmin")
        if existing_user:
            db.delete(existing_user)
            db.commit()
        
        user = user_service.create_admin_user(
            username=test_user.username,
            password=test_user.password,
            email=test_user.email,
            full_name=test_user.full_name
        )
        
        print(f"   ✅ User created: {user.username} (ID: {user.id})")
        print(f"   ✅ Email: {user.email}")
        print(f"   ✅ Superuser: {user.is_superuser}")
        print(f"   ✅ Active: {user.is_active}")
        
        # Test authentication
        print("3. Testing authentication...")
        
        # Test valid credentials
        auth_user = user_service.authenticate_user("testadmin", "testpass123")
        if auth_user:
            print("   ✅ Valid credentials accepted")
            print(f"   ✅ Authenticated user: {auth_user.username}")
        else:
            print("   ❌ Valid credentials rejected")
            return False
        
        # Test invalid credentials
        auth_user = user_service.authenticate_user("testadmin", "wrongpass")
        if not auth_user:
            print("   ✅ Invalid credentials rejected")
        else:
            print("   ❌ Invalid credentials accepted")
            return False
        
        # Test nonexistent user
        auth_user = user_service.authenticate_user("nonexistent", "password")
        if not auth_user:
            print("   ✅ Nonexistent user rejected")
        else:
            print("   ❌ Nonexistent user accepted")
            return False
        
        # Test password hashing
        print("4. Testing password security...")
        if user.hashed_password != "testpass123":
            print("   ✅ Password is properly hashed")
            print(f"   ✅ Hash length: {len(user.hashed_password)} characters")
        else:
            print("   ❌ Password is not hashed!")
            return False
        
        # Clean up test user
        db.delete(user)
        db.commit()
        print("   ✅ Test user cleaned up")
        
        print("\n🎉 All authentication tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    try:
        success = test_authentication()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test cancelled by user")
        sys.exit(1)