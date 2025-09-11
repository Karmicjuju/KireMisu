from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc, asc, select

from app.models.library_path import LibraryPath
from app.schemas.library_path import LibraryPathCreate, LibraryPathUpdate


class LibraryPathRepository:
    """Repository layer for library path data access operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_library_path(self, library_path_data: LibraryPathCreate) -> LibraryPath:
        """Create a new library path in the database."""
        db_library_path = LibraryPath(
            name=library_path_data.name,
            path=library_path_data.path,
            is_active=library_path_data.is_active,
            priority=library_path_data.priority,
        )
        
        try:
            self.db.add(db_library_path)
            await self.db.commit()
            await self.db.refresh(db_library_path)
            return db_library_path
        except IntegrityError as e:
            await self.db.rollback()
            # Check which constraint failed based on error message
            error_msg = str(e.orig)
            if "path" in error_msg or "uq_library_paths_path" in error_msg:
                raise ValueError(f"Path '{library_path_data.path}' already exists")
            elif "name" in error_msg or "uq_library_paths_name" in error_msg:
                raise ValueError(f"Name '{library_path_data.name}' already exists")
            else:
                raise ValueError("Library path creation failed due to constraint violation")
    
    async def get_library_path_by_id(self, library_path_id: int) -> Optional[LibraryPath]:
        """Get library path by ID."""
        result = await self.db.execute(select(LibraryPath).filter(LibraryPath.id == library_path_id))
        return result.scalar_one_or_none()
    
    async def get_library_path_by_path(self, path: str) -> Optional[LibraryPath]:
        """Get library path by path."""
        result = await self.db.execute(select(LibraryPath).filter(LibraryPath.path == path))
        return result.scalar_one_or_none()
    
    async def get_library_path_by_name(self, name: str) -> Optional[LibraryPath]:
        """Get library path by name."""
        result = await self.db.execute(select(LibraryPath).filter(LibraryPath.name == name))
        return result.scalar_one_or_none()
    
    async def get_all_library_paths(self, include_inactive: bool = False) -> List[LibraryPath]:
        """Get all library paths ordered by priority (descending)."""
        query = select(LibraryPath)
        
        if not include_inactive:
            query = query.filter(LibraryPath.is_active == True)
        
        query = query.order_by(desc(LibraryPath.priority), asc(LibraryPath.name))
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_active_library_paths(self) -> List[LibraryPath]:
        """Get only active library paths ordered by priority (descending)."""
        return await self.get_all_library_paths(include_inactive=False)
    
    async def update_library_path(self, library_path_id: int, library_path_data: LibraryPathUpdate) -> Optional[LibraryPath]:
        """Update library path information."""
        db_library_path = await self.get_library_path_by_id(library_path_id)
        if not db_library_path:
            return None
        
        update_data = library_path_data.model_dump(exclude_unset=True)
        
        try:
            for field, value in update_data.items():
                setattr(db_library_path, field, value)
            
            await self.db.commit()
            await self.db.refresh(db_library_path)
            return db_library_path
        except IntegrityError as e:
            await self.db.rollback()
            error_msg = str(e.orig)
            if "name" in error_msg or "uq_library_paths_name" in error_msg:
                raise ValueError(f"Name '{library_path_data.name}' already exists")
            else:
                raise ValueError("Library path update failed due to constraint violation")
    
    async def delete_library_path(self, library_path_id: int) -> bool:
        """Delete library path by ID."""
        db_library_path = await self.get_library_path_by_id(library_path_id)
        if not db_library_path:
            return False
        
        self.db.delete(db_library_path)
        await self.db.commit()
        return True
    
    async def is_path_taken(self, path: str, exclude_id: Optional[int] = None) -> bool:
        """Check if path is already taken by another library path."""
        query = select(LibraryPath).filter(LibraryPath.path == path)
        
        if exclude_id is not None:
            query = query.filter(LibraryPath.id != exclude_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def is_name_taken(self, name: str, exclude_id: Optional[int] = None) -> bool:
        """Check if name is already taken by another library path."""
        query = select(LibraryPath).filter(LibraryPath.name == name)
        
        if exclude_id is not None:
            query = query.filter(LibraryPath.id != exclude_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def get_library_paths_count(self, active_only: bool = False) -> int:
        """Get count of library paths."""
        query = select(LibraryPath)
        
        if active_only:
            query = query.filter(LibraryPath.is_active == True)
        
        result = await self.db.execute(query)
        return len(list(result.scalars().all()))
    
    async def activate_library_path(self, library_path_id: int) -> Optional[LibraryPath]:
        """Activate a library path."""
        db_library_path = await self.get_library_path_by_id(library_path_id)
        if not db_library_path:
            return None
        
        db_library_path.is_active = True
        await self.db.commit()
        await self.db.refresh(db_library_path)
        return db_library_path
    
    async def deactivate_library_path(self, library_path_id: int) -> Optional[LibraryPath]:
        """Deactivate a library path."""
        db_library_path = await self.get_library_path_by_id(library_path_id)
        if not db_library_path:
            return None
        
        db_library_path.is_active = False
        await self.db.commit()
        await self.db.refresh(db_library_path)
        return db_library_path
    
    async def update_priority(self, library_path_id: int, new_priority: int) -> Optional[LibraryPath]:
        """Update the priority of a library path."""
        db_library_path = await self.get_library_path_by_id(library_path_id)
        if not db_library_path:
            return None
        
        db_library_path.priority = new_priority
        await self.db.commit()
        await self.db.refresh(db_library_path)
        return db_library_path
    
    async def get_highest_priority(self) -> int:
        """Get the highest priority value among all library paths."""
        result = await self.db.execute(select(LibraryPath.priority).order_by(desc(LibraryPath.priority)))
        priority = result.scalar()
        return priority if priority is not None else 0