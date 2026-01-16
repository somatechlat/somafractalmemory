"""Centralized messages for SomaFractalMemory API.

All user-facing strings are defined here for i18n readiness.
Use get_message(code, **kwargs) to retrieve formatted messages.

VIBE Compliance:
- NO hardcoded strings in API responses
- All messages routable through this system
- i18n ready for future translation
"""

from enum import Enum
from typing import Any


class SuccessCode(str, Enum):
    """Success message codes."""

    MEMORY_STORED = "memory_stored"
    MEMORY_DELETED = "memory_deleted"
    GRAPH_LINK_CREATED = "graph_link_created"
    API_RUNNING = "api_running"
    HEALTH_OK = "health_ok"


class ErrorCode(str, Enum):
    """Error message codes."""

    # Authentication errors (401)
    MISSING_AUTH_HEADER = "missing_auth_header"
    INVALID_API_TOKEN = "invalid_api_token"

    # Validation errors (400)
    INVALID_COORDINATE = "invalid_coordinate"
    EMPTY_COORDINATE = "empty_coordinate"
    UNSUPPORTED_MEMORY_TYPE = "unsupported_memory_type"
    INVALID_FILTERS = "invalid_filters"

    # Not found errors (404)
    MEMORY_NOT_FOUND = "memory_not_found"
    PATH_NOT_FOUND = "path_not_found"

    # Rate limiting (429)
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

    # Server errors (500, 502, 503)
    INTERNAL_ERROR = "internal_error"
    VECTOR_STORE_ERROR = "vector_store_error"
    KV_STORE_ERROR = "kv_store_error"
    DELETE_FAILED = "delete_failed"
    GRAPH_LINK_FAILED = "graph_link_failed"
    GRAPH_NEIGHBORS_FAILED = "graph_neighbors_failed"
    GRAPH_PATH_FAILED = "graph_path_failed"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    BACKEND_UNHEALTHY = "backend_unhealthy"


# Message templates - i18n ready (can be replaced with gettext in future)
MESSAGES: dict[str, str] = {
    # Success messages
    SuccessCode.MEMORY_STORED.value: "Memory stored successfully at coordinate {coord}",
    SuccessCode.MEMORY_DELETED.value: "Memory at coordinate {coord} deleted successfully",
    SuccessCode.GRAPH_LINK_CREATED.value: "Graph link created from {from_coord} to {to_coord}",
    SuccessCode.API_RUNNING.value: "SomaFractalMemory API is running",
    SuccessCode.HEALTH_OK.value: "All systems healthy",
    # Authentication errors
    ErrorCode.MISSING_AUTH_HEADER.value: "Missing Authorization header",
    ErrorCode.INVALID_API_TOKEN.value: "Invalid API token",
    # Validation errors
    ErrorCode.INVALID_COORDINATE.value: "Invalid coordinate format: {coord}",
    ErrorCode.EMPTY_COORDINATE.value: "Coordinate cannot be empty",
    ErrorCode.UNSUPPORTED_MEMORY_TYPE.value: "Unsupported memory type: {memory_type}",
    ErrorCode.INVALID_FILTERS.value: "Invalid filter format",
    # Not found errors
    ErrorCode.MEMORY_NOT_FOUND.value: "Memory not found",
    ErrorCode.PATH_NOT_FOUND.value: "No path found between {from_coord} and {to_coord}",
    # Rate limiting
    ErrorCode.RATE_LIMIT_EXCEEDED.value: "Rate limit exceeded. Please try again later.",
    # Server errors
    ErrorCode.INTERNAL_ERROR.value: "Internal server error",
    ErrorCode.VECTOR_STORE_ERROR.value: "Vector store error during {operation}",
    ErrorCode.KV_STORE_ERROR.value: "Key-value store error during {operation}",
    ErrorCode.DELETE_FAILED.value: "Delete operation failed",
    ErrorCode.GRAPH_LINK_FAILED.value: "Graph link creation failed",
    ErrorCode.GRAPH_NEIGHBORS_FAILED.value: "Graph neighbors query failed",
    ErrorCode.GRAPH_PATH_FAILED.value: "Graph path query failed",
    ErrorCode.BACKEND_UNAVAILABLE.value: "Backend service unavailable: {service}",
    ErrorCode.BACKEND_UNHEALTHY.value: "One or more backend services unhealthy",
}


def get_message(code: str | SuccessCode | ErrorCode, **kwargs: Any) -> str:
    """Get a formatted message by code.

    Args:
        code: Message code (SuccessCode, ErrorCode, or string)
        **kwargs: Format parameters for the message template

    Returns:
        Formatted message string

    Example:
        >>> get_message(ErrorCode.INVALID_COORDINATE, coord="abc")
        'Invalid coordinate format: abc'
    """
    # Convert enum to string if needed
    if isinstance(code, SuccessCode | ErrorCode):
        code_str = code.value
    else:
        code_str = str(code)

    template = MESSAGES.get(code_str)
    if template is None:
        # Fallback for unknown codes
        return f"Unknown message code: {code_str}"

    try:
        return template.format(**kwargs)
    except KeyError as e:
        # Missing format parameter - return template with error note
        return f"{template} (missing parameter: {e})"


def get_error_detail(code: ErrorCode, **kwargs: Any) -> dict[str, str]:
    """Get error detail dict for API responses.

    Args:
        code: Error code
        **kwargs: Format parameters

    Returns:
        Dict with 'detail' and 'code' keys for API error responses
    """
    return {
        "detail": get_message(code, **kwargs),
        "code": code.value,
    }


__all__ = [
    "SuccessCode",
    "ErrorCode",
    "MESSAGES",
    "get_message",
    "get_error_detail",
]
