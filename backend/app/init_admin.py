"""Initialize admin user for KireMisu."""
import asyncio
import uuid
from app.db.database import get_async_session, create_db_and_tables
from app.models.user import User
from app.users import get_user_manager
from app.db.database import get_user_db
from app.schemas.user import UserCreate


async def create_admin_user():
    """Create initial admin user if not exists."""
    await create_db_and_tables()
    
    admin_email = "admin@example.com"
    admin_username = "admin"
    admin_password = "Admin123!"
    
    async for session in get_async_session():
        async for user_db in get_user_db(session):
            async for user_manager in get_user_manager(user_db):
                # Check if admin user already exists
                try:
                    existing_user = await user_manager.get_by_email(admin_email)
                    if existing_user:
                        print(f"Admin user already exists: {admin_email}")
                        return existing_user
                except:
                    pass
                
                # Create admin user
                user_create = UserCreate(
                    email=admin_email,
                    username=admin_username,
                    password=admin_password,
                    is_superuser=True,
                    is_verified=True,
                )
                
                try:
                    user = await user_manager.create(user_create)
                    print(f"Created admin user: {admin_email}")
                    print(f"Username: {admin_username}")
                    print(f"Password: {admin_password}")
                    return user
                except Exception as e:
                    print(f"Error creating admin user: {e}")
                    return None
            break
        break


if __name__ == "__main__":
    asyncio.run(create_admin_user())