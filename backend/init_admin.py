#!/usr/bin/env python3
"""
Admin user initialization script for KireMisu manga library.

This script creates the first admin user in the database.
Run this after setting up the database and before starting the application.

Usage:
    python init_admin.py
    
    Or with environment variables:
    ADMIN_USERNAME=admin ADMIN_PASSWORD=secure123 ADMIN_EMAIL=admin@localhost python init_admin.py

Security Note:
This is the SECURE way to initialize admin credentials - no hardcoded passwords in source code.
"""

import os
import sys
import secrets
import string
from getpass import getpass
from sqlalchemy.exc import IntegrityError

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings
from app.db.database import engine, SessionLocal
from app.models.user import User
from app.services.user import UserService


def generate_secure_password(length: int = 16) -> str:
    """Generate a cryptographically secure password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_tables():
    """Create database tables if they don't exist."""
    from app.models.user import Base
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")


def get_admin_credentials():
    """Get admin credentials from environment or user input."""
    username = os.getenv('ADMIN_USERNAME')
    password = os.getenv('ADMIN_PASSWORD')
    email = os.getenv('ADMIN_EMAIL')
    
    if not username:
        username = input("Enter admin username (default: admin): ").strip() or "admin"
    
    if not email:
        email = input(f"Enter admin email (default: {username}@localhost): ").strip()
        if not email:
            email = f"{username}@localhost"
    
    if not password:
        print("\nPassword Options:")
        print("1. Enter password manually")
        print("2. Generate secure random password")
        choice = input("Choose option (1 or 2, default: 2): ").strip() or "2"
        
        if choice == "1":
            password = getpass("Enter admin password: ")
            if len(password) < 8:
                print("❌ Password must be at least 8 characters long")
                sys.exit(1)
        else:
            password = generate_secure_password()
            print(f"🔐 Generated secure password: {password}")
            print("⚠️  IMPORTANT: Save this password - it won't be shown again!")
            input("Press Enter to continue after saving the password...")
    
    return username, password, email


def main():
    print("🚀 KireMisu Admin User Initialization")
    print("=" * 50)
    
    try:
        # Create database tables
        create_tables()
        
        # Get admin credentials
        username, password, email = get_admin_credentials()
        
        # Create database session
        db = SessionLocal()
        user_service = UserService(db)
        
        try:
            # Check if admin user already exists
            existing_user = user_service.get_user_by_username(username)
            if existing_user:
                print(f"❌ User '{username}' already exists!")
                overwrite = input("Do you want to update the password? (y/N): ").lower()
                if overwrite != 'y':
                    print("Initialization cancelled.")
                    sys.exit(0)
                
                # Update existing user password
                existing_user.hashed_password = user_service.get_password_hash(password)
                existing_user.is_superuser = True
                existing_user.is_active = True
                db.commit()
                print(f"✅ Admin user '{username}' password updated successfully!")
            else:
                # Create new admin user
                admin_user = user_service.create_admin_user(
                    username=username,
                    password=password,
                    email=email,
                    full_name="System Administrator"
                )
                print(f"✅ Admin user '{username}' created successfully!")
                print(f"   User ID: {admin_user.id}")
                print(f"   Email: {admin_user.email}")
                print(f"   Superuser: {admin_user.is_superuser}")
        
        except ValueError as e:
            print(f"❌ Error creating admin user: {e}")
            sys.exit(1)
        except IntegrityError as e:
            print(f"❌ Database constraint error: {e}")
            sys.exit(1)
        finally:
            db.close()
        
        print("\n🎉 Admin initialization complete!")
        print("You can now start the KireMisu application and login with:")
        print(f"   Username: {username}")
        print("   Password: [the password you set/generated]")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Initialization cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()