"""Centralized Error Codes and Messages — I18N Ready.

VIBE RULE 11: All user-facing text MUST use get_message().
This module is the SINGLE SOURCE OF TRUTH for all SomaFractalMemory messages.
"""

from enum import Enum

from django.utils.translation import gettext_lazy as _


class ErrorCode(str, Enum):
    """Error codes for SomaFractalMemory modules."""

    # Generic
    INTERNAL_ERROR = "internal_error"
    INVALID_REQUEST = "invalid_request"
    ADMIN_REQUIRED = "admin_required"
    ACCESS_DENIED = "access_denied"
    API_KEY_NOT_FOUND = "api_key_not_found"

    # Authentication
    MISSING_AUTH_HEADER = "missing_auth_header"
    INVALID_API_TOKEN = "invalid_api_token"
    PERMISSION_DENIED = "permission_denied"

    # Validation
    INVALID_COORDINATE = "invalid_coordinate"
    EMPTY_COORDINATE = "empty_coordinate"
    UNSUPPORTED_MEMORY_TYPE = "unsupported_memory_type"
    INVALID_FILTERS = "invalid_filters"

    # Vector Operations
    VECTOR_STORE_FAILED = "vector_store_failed"
    VECTOR_STORE_ERROR = "vector_store_error"
    VECTOR_SEARCH_FAILED = "vector_search_failed"
    VECTOR_DELETE_FAILED = "vector_delete_failed"
    VECTOR_NOT_FOUND = "vector_not_found"

    # Collection Management
    COLLECTION_NOT_FOUND = "collection_not_found"
    COLLECTION_CREATE_FAILED = "collection_create_failed"
    COLLECTION_DELETE_FAILED = "collection_delete_failed"

    # Embedding
    EMBEDDING_FAILED = "embedding_failed"
    EMBEDDING_DIMENSION_MISMATCH = "embedding_dimension_mismatch"

    # External Services
    MILVUS_UNAVAILABLE = "milvus_unavailable"
    MILVUS_CONNECTION_FAILED = "milvus_connection_failed"
    BACKEND_UNHEALTHY = "backend_unhealthy"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    KV_STORE_ERROR = "kv_store_error"

    # Memory & Graph
    MEMORY_NOT_FOUND = "memory_not_found"
    DELETE_FAILED = "delete_failed"
    GRAPH_LINK_FAILED = "graph_link_failed"
    GRAPH_NEIGHBORS_FAILED = "graph_neighbors_failed"
    GRAPH_PATH_FAILED = "graph_path_failed"
    PATH_NOT_FOUND = "path_not_found"

    # Rate Limiting
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


class SuccessCode(str, Enum):
    """Success codes for confirmations."""

    # Generic
    API_RUNNING = "api_running"
    HEALTH_OK = "health_ok"

    # Vector/Memory
    VECTOR_STORED = "vector_stored"
    VECTOR_SEARCHED = "vector_searched"
    VECTOR_DELETED = "vector_deleted"
    MEMORY_STORED = "memory_stored"
    MEMORY_DELETED = "memory_deleted"

    # Collection
    COLLECTION_CREATED = "collection_created"
    COLLECTION_DELETED = "collection_deleted"

    # Graph
    GRAPH_LINK_CREATED = "graph_link_created"


# I18N-Ready Messages using Django gettext_lazy
MESSAGES: dict[str | ErrorCode | SuccessCode, str] = {
    # Generic
    ErrorCode.INTERNAL_ERROR: _("An unexpected error occurred in FractalMemory"),
    ErrorCode.INVALID_REQUEST: _("Invalid request to memory store"),
    ErrorCode.ADMIN_REQUIRED: _("Admin permission required"),
    ErrorCode.ACCESS_DENIED: _("Access denied to requested resource"),
    ErrorCode.API_KEY_NOT_FOUND: _("API key not found"),
    # Authentication
    ErrorCode.MISSING_AUTH_HEADER: _("Missing Authorization header"),
    ErrorCode.INVALID_API_TOKEN: _("Invalid API token"),
    ErrorCode.PERMISSION_DENIED: _("Permission denied"),
    # Validation
    ErrorCode.INVALID_COORDINATE: _("Invalid coordinate format: {coord}"),
    ErrorCode.EMPTY_COORDINATE: _("Coordinate cannot be empty"),
    ErrorCode.UNSUPPORTED_MEMORY_TYPE: _("Unsupported memory type: {memory_type}"),
    ErrorCode.INVALID_FILTERS: _("Invalid filter format"),
    # Vector Operations
    ErrorCode.VECTOR_STORE_FAILED: _("Failed to store vector"),
    ErrorCode.VECTOR_STORE_ERROR: _("Vector store error during {operation}"),
    ErrorCode.VECTOR_SEARCH_FAILED: _("Failed to search vectors"),
    ErrorCode.VECTOR_DELETE_FAILED: _("Failed to delete vector"),
    ErrorCode.VECTOR_NOT_FOUND: _("Vector with id '{id}' not found"),
    # Collection Management
    ErrorCode.COLLECTION_NOT_FOUND: _("Collection '{name}' not found"),
    ErrorCode.COLLECTION_CREATE_FAILED: _("Failed to create collection '{name}'"),
    ErrorCode.COLLECTION_DELETE_FAILED: _("Failed to delete collection '{name}'"),
    # Embedding
    ErrorCode.EMBEDDING_FAILED: _("Failed to generate embeddings"),
    ErrorCode.EMBEDDING_DIMENSION_MISMATCH: _(
        "Embedding dimension {got} does not match expected {expected}"
    ),
    # External Services
    ErrorCode.MILVUS_UNAVAILABLE: _("Vector store (Milvus) is temporarily unavailable"),
    ErrorCode.MILVUS_CONNECTION_FAILED: _("Failed to connect to Milvus"),
    ErrorCode.BACKEND_UNHEALTHY: _("System backend is unhealthy"),
    ErrorCode.BACKEND_UNAVAILABLE: _("Required service '{service}' is unavailable"),
    ErrorCode.KV_STORE_ERROR: _("Key-value store error during {operation}"),
    # Memory & Graph
    ErrorCode.MEMORY_NOT_FOUND: _("Memory not found"),
    ErrorCode.DELETE_FAILED: _("Delete operation failed"),
    ErrorCode.GRAPH_LINK_FAILED: _("Failed to create graph link"),
    ErrorCode.GRAPH_NEIGHBORS_FAILED: _("Failed to retrieve neighbors"),
    ErrorCode.GRAPH_PATH_FAILED: _("Graph path query failed"),
    ErrorCode.PATH_NOT_FOUND: _("No path found between {from_coord} and {to_coord}"),
    # Rate Limiting
    ErrorCode.RATE_LIMIT_EXCEEDED: _("Rate limit exceeded. Please try again later."),
    # Success
    SuccessCode.API_RUNNING: _("FractalMemory API is running"),
    SuccessCode.HEALTH_OK: _("All systems healthy"),
    SuccessCode.VECTOR_STORED: _("Vector stored successfully"),
    SuccessCode.VECTOR_SEARCHED: _("Vector search completed"),
    SuccessCode.VECTOR_DELETED: _("Vector deleted successfully"),
    SuccessCode.MEMORY_STORED: _("Memory stored successfully at coordinate {coord}"),
    SuccessCode.MEMORY_DELETED: _("Memory at coordinate {coord} deleted successfully"),
    SuccessCode.COLLECTION_CREATED: _("Collection '{name}' created successfully"),
    SuccessCode.COLLECTION_DELETED: _("Collection '{name}' deleted successfully"),
    SuccessCode.GRAPH_LINK_CREATED: _("Graph link created from {from_coord} to {to_coord}"),
}


def get_message(code: ErrorCode | SuccessCode | str, **kwargs: object) -> str:
    """Get formatted, translated message for code.

    Args:
        code: Error or success code from enum
        **kwargs: Format arguments for message template

    Returns:
        Formatted, translated message string
    """
    msg = MESSAGES.get(code, _("Unknown error"))
    try:
        if kwargs:
            return str(msg).format(**kwargs)
        return str(msg)
    except KeyError as e:
        return f"{msg} (missing parameter: {e})"


def get_error_detail(code: ErrorCode, **kwargs: object) -> dict[str, str]:
    """Get error detail dict for API responses.

    Args:
        code: Error code
        **kwargs: Format parameters

    Returns:
        Dict with 'detail' and 'code' keys for API error responses
    """
    return {
        "detail": get_message(code, **kwargs),
        "code": str(code.value if hasattr(code, "value") else code),
    }
