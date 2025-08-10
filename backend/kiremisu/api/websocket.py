"""WebSocket API endpoints for real-time notifications.

This module provides WebSocket endpoints for real-time notifications.
Currently experimental and disabled by default.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.responses import JSONResponse

from kiremisu.websocket.connection_manager import connection_manager
from kiremisu.database.schemas import ErrorResponse
from kiremisu.core.error_handler import create_standardized_error_response

router = APIRouter(prefix="/api/ws", tags=["websocket"])
logger = logging.getLogger(__name__)


@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    # TODO: Add user authentication when implemented
    # user_id: Optional[UUID] = Query(None, description="User ID (future implementation)")
):
    """WebSocket endpoint for real-time notifications.

    This endpoint provides real-time notifications via WebSocket connection.

    **EXPERIMENTAL**: Currently disabled by default until user authentication
    is implemented for proper connection scoping.

    Message Types:
    - notification: New notification received
    - watching_update: Series watching status changed
    - connection_established: Initial connection confirmation

    TODO: Enable after implementing user authentication and authorization.
    """
    user_id = None  # TODO: Extract from authentication token

    try:
        await connection_manager.connect(websocket, user_id=user_id)

        # Keep connection alive and handle incoming messages
        while True:
            # Wait for messages from client (subscription management, etc.)
            try:
                data = await websocket.receive_json()
                await handle_websocket_message(websocket, data, user_id)
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                break

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        connection_manager.disconnect(websocket)


async def handle_websocket_message(websocket: WebSocket, data: dict, user_id: Optional[UUID]):
    """Handle incoming WebSocket messages from clients.

    Args:
        websocket: WebSocket connection
        data: Message data from client
        user_id: User ID (future implementation)
    """
    message_type = data.get("type", "unknown")

    logger.debug(f"Received WebSocket message: {message_type}")

    if message_type == "ping":
        # Respond to ping with pong
        await connection_manager.send_to_connection(
            websocket,
            {
                "type": "pong",
                "timestamp": None,  # Could add current timestamp
            },
        )

    elif message_type == "subscribe":
        # Handle subscription management (future implementation)
        subscription_types = data.get("subscription_types", [])
        logger.debug(f"Client subscription request: {subscription_types}")

        # TODO: Update connection metadata with subscriptions
        await connection_manager.send_to_connection(
            websocket,
            {
                "type": "subscription_confirmed",
                "subscriptions": subscription_types,
                "message": "Subscription preferences updated",
            },
        )

    elif message_type == "unsubscribe":
        # Handle unsubscription (future implementation)
        subscription_types = data.get("subscription_types", [])
        logger.debug(f"Client unsubscription request: {subscription_types}")

        await connection_manager.send_to_connection(
            websocket,
            {
                "type": "unsubscription_confirmed",
                "unsubscribed": subscription_types,
                "message": "Unsubscribed from notification types",
            },
        )

    else:
        # Unknown message type
        await connection_manager.send_to_connection(
            websocket,
            {
                "type": "error",
                "error_code": "UNKNOWN_MESSAGE_TYPE",
                "message": f"Unknown message type: {message_type}",
            },
        )


@router.get(
    "/stats",
    response_model=dict,
    responses={
        200: {"description": "WebSocket connection statistics"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_websocket_stats() -> dict:
    """Get WebSocket connection statistics.

    Returns information about active WebSocket connections and system status.
    Useful for monitoring and debugging WebSocket functionality.
    """
    try:
        stats = connection_manager.get_stats()
        return {
            "websocket_stats": stats,
            "status": "operational" if connection_manager.enabled else "disabled",
            "message": "WebSocket system disabled until authentication implemented"
            if not connection_manager.enabled
            else "WebSocket system operational",
        }
    except Exception as e:
        logger.error(f"Error getting WebSocket stats: {e}")
        error_response = create_standardized_error_response(
            status_code=500,
            message="Failed to get WebSocket statistics",
            error_code="WEBSOCKET_STATS_ERROR",
        )
        return JSONResponse(status_code=500, content=error_response)


@router.post(
    "/enable",
    response_model=dict,
    responses={
        200: {"description": "WebSocket functionality enabled/disabled"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def toggle_websocket_functionality(enabled: bool = True) -> dict:
    """Enable or disable WebSocket functionality.

    This endpoint allows administrators to enable/disable WebSocket functionality.

    **Warning**: Only enable after implementing proper user authentication
    and authorization to prevent unauthorized access to real-time notifications.

    Args:
        enabled: Whether to enable WebSocket functionality

    Returns:
        Status of WebSocket functionality
    """
    try:
        connection_manager.enable(enabled)

        return {
            "websocket_enabled": enabled,
            "active_connections": len(connection_manager.active_connections),
            "message": f"WebSocket functionality {'enabled' if enabled else 'disabled'}",
            "warning": "Ensure proper authentication is implemented before enabling in production"
            if enabled
            else None,
        }
    except Exception as e:
        logger.error(f"Error toggling WebSocket functionality: {e}")
        error_response = create_standardized_error_response(
            status_code=500,
            message="Failed to toggle WebSocket functionality",
            error_code="WEBSOCKET_TOGGLE_ERROR",
        )
        return JSONResponse(status_code=500, content=error_response)


@router.post(
    "/test-broadcast",
    response_model=dict,
    responses={
        200: {"description": "Test message broadcast"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def test_websocket_broadcast(
    message: str = "Test notification", message_type: str = "test"
) -> dict:
    """Send a test message to all connected WebSocket clients.

    This endpoint is useful for testing WebSocket connectivity and message delivery.

    **Development Only**: This endpoint should be removed or secured in production.

    Args:
        message: Test message to send
        message_type: Type of test message

    Returns:
        Broadcast result information
    """
    try:
        if not connection_manager.enabled:
            return {
                "status": "skipped",
                "message": "WebSocket functionality is disabled",
                "connections_attempted": 0,
            }

        test_message = {
            "type": message_type,
            "message": message,
            "timestamp": None,  # Could add current timestamp
            "test": True,
        }

        await connection_manager.broadcast_to_all(test_message)

        return {
            "status": "sent",
            "message": "Test message broadcast to all connections",
            "connections_attempted": len(connection_manager.active_connections),
            "broadcast_data": test_message,
        }
    except Exception as e:
        logger.error(f"Error broadcasting test message: {e}")
        error_response = create_standardized_error_response(
            status_code=500,
            message="Failed to broadcast test message",
            error_code="WEBSOCKET_BROADCAST_ERROR",
        )
        return JSONResponse(status_code=500, content=error_response)
