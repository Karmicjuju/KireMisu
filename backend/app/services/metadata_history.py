from typing import Dict, List, Optional, Any, Union
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.metadata_history import MetadataHistoryRepository
from app.models.metadata_history import MetadataHistory


class MetadataHistoryService:
    """Service for managing metadata history operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = MetadataHistoryRepository(db)

    async def record_change(
        self,
        entity_type: str,
        entity_id: int,
        user_id: Optional[Union[str, uuid.UUID]],
        action: str,
        previous_data: Optional[Dict[str, Any]] = None,
        new_data: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
    ) -> MetadataHistory:
        """Record a metadata change."""
        
        # Calculate changed fields if both previous and new data are provided
        changed_fields = None
        if previous_data and new_data:
            changed_fields = []
            for key in new_data:
                if key not in previous_data or previous_data[key] != new_data[key]:
                    changed_fields.append(key)

        # Convert user_id to UUID if it's a string
        uuid_user_id = None
        if user_id:
            if isinstance(user_id, str):
                try:
                    uuid_user_id = uuid.UUID(user_id)
                except ValueError:
                    # If it's not a valid UUID string, skip storing user_id
                    uuid_user_id = None
            else:
                uuid_user_id = user_id

        return await self.repository.create_history_entry(
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=uuid_user_id,
            action=action,
            previous_data=previous_data,
            new_data=new_data,
            changed_fields=changed_fields,
            description=description,
        )

    async def get_entity_history(
        self,
        entity_type: str,
        entity_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> List[MetadataHistory]:
        """Get change history for an entity."""
        return await self.repository.get_entity_history(
            entity_type=entity_type,
            entity_id=entity_id,
            limit=limit,
            offset=offset,
        )

    async def get_history_by_id(self, history_id: int) -> Optional[MetadataHistory]:
        """Get a specific history entry."""
        return await self.repository.get_history_by_id(history_id)

    async def get_restore_data(self, history_id: int) -> Optional[Dict[str, Any]]:
        """Get data needed to restore to a previous state."""
        history = await self.repository.get_history_by_id(history_id)
        if not history:
            return None
        
        # Return the previous_data for restoration
        return history.previous_data

    async def create_diff_preview(
        self,
        current_data: Dict[str, Any],
        new_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a preview of changes without saving."""
        
        # Create a diff showing what would change
        diff = {
            "changes": {},
            "additions": {},
            "removals": {},
        }
        
        # Find changes and additions
        for key, new_value in new_data.items():
            if key not in current_data:
                diff["additions"][key] = new_value
            elif current_data[key] != new_value:
                diff["changes"][key] = {
                    "old": current_data[key],
                    "new": new_value,
                }
        
        # Find removals (keys that exist in current but not in new)
        for key, current_value in current_data.items():
            if key not in new_data:
                diff["removals"][key] = current_value
        
        return diff

    async def cleanup_old_history(
        self,
        entity_type: str,
        entity_id: int,
        keep_count: int = 100,
    ) -> int:
        """Clean up old history entries, keeping only the most recent ones."""
        return await self.repository.delete_old_history(
            entity_type=entity_type,
            entity_id=entity_id,
            keep_count=keep_count,
        )

    async def get_user_activity(
        self,
        user_id: int,
        limit: int = 100,
        offset: int = 0,
        entity_type: Optional[str] = None,
    ) -> List[MetadataHistory]:
        """Get all metadata changes made by a user."""
        return await self.repository.get_user_history(
            user_id=user_id,
            limit=limit,
            offset=offset,
            entity_type=entity_type,
        )

    async def get_entity_statistics(
        self, entity_type: str, entity_id: int
    ) -> Dict[str, Any]:
        """Get statistics about an entity's change history."""
        history_entries = await self.repository.get_entity_history(
            entity_type=entity_type,
            entity_id=entity_id,
            limit=1000,  # Get more entries for statistics
        )
        
        total_changes = len(history_entries)
        if total_changes == 0:
            return {
                "total_changes": 0,
                "change_types": {},
                "most_active_users": [],
                "most_changed_fields": [],
            }

        # Count change types
        change_types = {}
        user_counts = {}
        field_counts = {}
        
        for entry in history_entries:
            # Count action types
            change_types[entry.action] = change_types.get(entry.action, 0) + 1
            
            # Count user activity
            if entry.user_id:
                user_counts[entry.user_id] = user_counts.get(entry.user_id, 0) + 1
            
            # Count field changes
            if entry.changed_fields:
                for field in entry.changed_fields:
                    field_counts[field] = field_counts.get(field, 0) + 1

        # Sort most active users and fields
        most_active_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        most_changed_fields = sorted(field_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total_changes": total_changes,
            "change_types": change_types,
            "most_active_users": most_active_users,
            "most_changed_fields": most_changed_fields,
        }