"""WebSocket connection manager for real-time notifications.

This module provides WebSocket infrastructure for real-time notifications.
Currently experimental and disabled by default until authentication is implemented.
"""

import json
import logging
from typing import Dict, List, Optional, Set
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class WebSocketMessage(BaseModel):
    """Schema for WebSocket messages."""

    type: str = Field(..., description="Message type")
    data: dict = Field(default_factory=dict, description="Message payload")
    timestamp: Optional[str] = Field(None, description="Message timestamp")
    user_id: Optional[UUID] = Field(None, description="User ID (future implementation)")


class NotificationMessage(WebSocketMessage):
    """Schema for notification WebSocket messages."""

    type: str = Field(default="notification", description="Message type")
    notification_id: UUID = Field(..., description="Notification ID")
    notification_type: str = Field(..., description="Notification type")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    series_id: Optional[UUID] = Field(None, description="Related series ID")
    chapter_id: Optional[UUID] = Field(None, description="Related chapter ID")


class WatchingUpdateMessage(WebSocketMessage):
    """Schema for watching update WebSocket messages."""

    type: str = Field(default="watching_update", description="Message type")
    series_id: UUID = Field(..., description="Series ID")
    series_title: str = Field(..., description="Series title")
    update_type: str = Field(..., description="Update type (new_chapter, status_change)")
    chapter_count: Optional[int] = Field(None, description="New chapter count")


class ConnectionManager:
    """Manages WebSocket connections for real-time notifications.

    TODO: This is currently experimental and should be enabled only after
    user authentication is implemented for proper connection scoping.
    """

    def __init__(self):
        # Active WebSocket connections
        self.active_connections: List[WebSocket] = []

        # TODO: User-specific connections for multi-user support
        self.user_connections: Dict[UUID, Set[WebSocket]] = {}

        # Connection metadata
        self.connection_metadata: Dict[WebSocket, dict] = {}

        # Feature flag - disabled by default until authentication is ready
        self.enabled = False

        logger.info("WebSocket ConnectionManager initialized (disabled by default)")

    def enable(self, enabled: bool = True):
        """Enable or disable WebSocket functionality."""
        self.enabled = enabled
        logger.info(f"WebSocket functionality {'enabled' if enabled else 'disabled'}")

    async def connect(self, websocket: WebSocket, user_id: Optional[UUID] = None):
        """Accept a WebSocket connection.

        Args:
            websocket: WebSocket connection
            user_id: User ID (future implementation)
        """
        if not self.enabled:
            logger.warning("WebSocket connection rejected - functionality disabled")
            await websocket.close(code=1000, reason="WebSocket functionality disabled")
            return

        await websocket.accept()
        self.active_connections.append(websocket)

        # Store connection metadata
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "connected_at": None,  # Could add timestamp
            "subscriptions": set(),  # Types of notifications subscribed to
        }

        # TODO: Associate with user when authentication is implemented
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(websocket)

        logger.info(
            f"WebSocket connection established. Active connections: {len(self.active_connections)}"
        )

        # Send welcome message
        await self.send_to_connection(
            websocket,
            {
                "type": "connection_established",
                "message": "WebSocket connection established",
                "features_available": ["notifications", "watching_updates"],
            },
        )

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection.

        Args:
            websocket: WebSocket connection to remove
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        # Remove from user connections
        metadata = self.connection_metadata.get(websocket, {})
        user_id = metadata.get("user_id")
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        # Clean up metadata
        self.connection_metadata.pop(websocket, None)

        logger.info(
            f"WebSocket connection disconnected. Active connections: {len(self.active_connections)}"
        )

    async def send_to_connection(self, websocket: WebSocket, message: dict):
        """Send message to a specific WebSocket connection.

        Args:
            websocket: Target WebSocket connection
            message: Message dictionary to send
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
            # Connection might be dead, clean it up
            self.disconnect(websocket)

    async def broadcast_to_all(self, message: dict):
        """Broadcast message to all connected WebSocket clients.

        Args:
            message: Message dictionary to broadcast
        """
        if not self.enabled:
            return

        if not self.active_connections:
            return

        logger.debug(f"Broadcasting message to {len(self.active_connections)} connections")

        # Send to all connections, clean up dead ones
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket connection: {e}")
                dead_connections.append(connection)

        # Clean up dead connections
        for dead_connection in dead_connections:
            self.disconnect(dead_connection)

    async def broadcast_to_user(self, user_id: UUID, message: dict):
        """Broadcast message to all connections for a specific user.

        Args:
            user_id: Target user ID
            message: Message dictionary to send

        TODO: This will be useful when user authentication is implemented.
        """
        if not self.enabled:
            return

        user_connections = self.user_connections.get(user_id, set())
        if not user_connections:
            return

        logger.debug(
            f"Broadcasting message to user {user_id} ({len(user_connections)} connections)"
        )

        # Send to user's connections, clean up dead ones
        dead_connections = []
        for connection in list(user_connections):  # Create copy to iterate over
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to user WebSocket connection: {e}")
                dead_connections.append(connection)

        # Clean up dead connections
        for dead_connection in dead_connections:
            self.disconnect(dead_connection)

    async def send_notification(self, notification_data: NotificationMessage):
        """Send notification to all relevant WebSocket connections.

        Args:
            notification_data: Notification message data
        """
        message = notification_data.model_dump()

        # TODO: When user authentication is implemented, send only to relevant users
        # For now, broadcast to all connections
        await self.broadcast_to_all(message)

    async def send_watching_update(self, update_data: WatchingUpdateMessage):
        """Send watching update to all relevant WebSocket connections.

        Args:
            update_data: Watching update message data
        """
        message = update_data.model_dump()

        # TODO: When user authentication is implemented, send only to users watching this series
        # For now, broadcast to all connections
        await self.broadcast_to_all(message)

    def get_stats(self) -> dict:
        """Get WebSocket connection statistics.

        Returns:
            Dictionary with connection statistics
        """
        return {
            "enabled": self.enabled,
            "total_connections": len(self.active_connections),
            "user_connections": len(self.user_connections),
            "users_with_connections": list(self.user_connections.keys()),
        }


# Global connection manager instance
connection_manager = ConnectionManager()
