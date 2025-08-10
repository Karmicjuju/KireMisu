"""Secure error handling utilities for the KireMisu API."""

import logging
import re
from typing import Dict, Any
from uuid import uuid4

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

logger = logging.getLogger(__name__)


class SecureErrorHandler:
    """Handles errors securely by sanitizing sensitive information."""

    # Patterns to identify sensitive information in error messages
    SENSITIVE_PATTERNS = [
        r"/[a-zA-Z0-9/\-_\.]+",  # File paths
        r"[A-Za-z]:\\[a-zA-Z0-9\\\/\-_\.]+",  # Windows paths
        r"database://[^\s]+",  # Database URLs
        r"postgresql://[^\s]+",  # PostgreSQL URLs
        r"mongodb://[^\s]+",  # MongoDB URLs
        r"redis://[^\s]+",  # Redis URLs
        r"password[=:][\w]+",  # Password fields
        r"secret[=:][\w]+",  # Secret fields
        r"token[=:][\w]+",  # Token fields
        r"key[=:][\w]+",  # API key fields
        r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",  # IP addresses
        r"localhost:\d+",  # Local ports
        r"127\.0\.0\.1:\d+",  # Localhost with port
    ]

    @staticmethod
    def sanitize_error_message(message: str, request_id: str = None) -> str:
        """
        Sanitize error message by removing sensitive information.

        Args:
            message: Original error message
            request_id: Optional request ID for logging

        Returns:
            Sanitized error message safe for client consumption
        """
        if not message:
            return "An error occurred"

        # Log the original error for debugging (server-side only)
        if request_id:
            logger.error(f"Original error [{request_id}]: {message}")
        else:
            logger.error(f"Original error: {message}")

        sanitized = message

        # Replace sensitive patterns with generic placeholders
        for pattern in SecureErrorHandler.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)

        # Additional sanitization for common error scenarios
        sanitizations = {
            r"Path does not exist: [REDACTED]": "Invalid path specified",
            r"Path is not a directory: [REDACTED]": "Invalid directory path",
            r"Path is not readable: [REDACTED]": "Directory access denied",
            r"Path already exists: [REDACTED]": "Path already configured",
            r"Library path not found: [a-f0-9\-]{36}": "Library path not found",
            r"Chapter not found: [a-f0-9\-]{36}": "Chapter not found",
            r"Series not found: [a-f0-9\-]{36}": "Series not found",
            r"File not found: [REDACTED]": "Requested file not available",
            r"Permission denied: [REDACTED]": "Access denied",
            r"\[REDACTED\]": "system path",  # Generic replacement for redacted paths
        }

        for pattern, replacement in sanitizations.items():
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

        # Limit message length to prevent verbose error disclosure
        max_length = 200
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "..."

        return sanitized

    @staticmethod
    def create_secure_error_response(
        status_code: int, error_message: str, request_id: str = None, include_details: bool = False
    ) -> Dict[str, Any]:
        """
        Create a secure error response with sanitized information.

        Args:
            status_code: HTTP status code
            error_message: Original error message
            request_id: Optional request ID for tracing
            include_details: Whether to include additional error details (for dev mode)

        Returns:
            Sanitized error response dictionary
        """
        sanitized_message = SecureErrorHandler.sanitize_error_message(error_message, request_id)

        response = {
            "error": True,
            "message": sanitized_message,
            "status_code": status_code,
        }

        if request_id:
            response["request_id"] = request_id

        # Only include detailed errors in development mode
        if include_details and logger.isEnabledFor(logging.DEBUG):
            response["details"] = {
                "original_message": error_message[:500],  # Truncated for safety
                "timestamp": None,  # Will be set by FastAPI
            }

        return response


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unhandled errors.

    Args:
        request: The FastAPI request object
        exc: The unhandled exception

    Returns:
        Sanitized JSON error response
    """
    request_id = str(uuid4())

    # Log the full error for server-side debugging
    logger.error(
        f"Unhandled exception [{request_id}] {type(exc).__name__}: {str(exc)}", exc_info=True
    )

    # Create secure error response
    error_response = SecureErrorHandler.create_secure_error_response(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        error_message=str(exc),
        request_id=request_id,
        include_details=False,  # Never expose details for unhandled exceptions
    )

    return JSONResponse(status_code=HTTP_500_INTERNAL_SERVER_ERROR, content=error_response)


def create_secure_http_exception(
    status_code: int, error_message: str, request_id: str = None
) -> HTTPException:
    """
    Create an HTTPException with sanitized error message.

    Args:
        status_code: HTTP status code
        error_message: Original error message
        request_id: Optional request ID

    Returns:
        HTTPException with sanitized detail
    """
    sanitized_message = SecureErrorHandler.sanitize_error_message(error_message, request_id)

    return HTTPException(status_code=status_code, detail=sanitized_message)


def create_standardized_error_response(
    status_code: int,
    message: str,
    error_code: str = None,
    request_id: str = None,
    details: list = None,
) -> dict:
    """
    Create a standardized error response using the new error schemas.

    Args:
        status_code: HTTP status code
        message: Error message
        error_code: Application-specific error code
        request_id: Request tracking ID
        details: List of error details

    Returns:
        Standardized error response dictionary
    """
    from kiremisu.database.schemas import ErrorResponse

    error_response = ErrorResponse.create(
        message=SecureErrorHandler.sanitize_error_message(message, request_id),
        status_code=status_code,
        error_code=error_code,
        request_id=request_id,
        details=details,
    )

    return error_response.model_dump()


def create_not_found_error(
    resource_type: str, resource_id: str = None, request_id: str = None
) -> dict:
    """Create a standardized 404 error response."""
    from kiremisu.database.schemas import NotFoundErrorResponse

    error_response = NotFoundErrorResponse.create_for_resource(
        resource_type=resource_type, resource_id=resource_id, request_id=request_id
    )

    return error_response.model_dump()


def create_validation_error(validation_exception, request_id: str = None) -> dict:
    """Create a standardized validation error response."""
    from kiremisu.database.schemas import ValidationErrorResponse

    error_response = ValidationErrorResponse.from_pydantic_error(
        validation_exception, request_id=request_id
    )

    return error_response.model_dump()
