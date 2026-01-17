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

    # Vector Operations
    VECTOR_STORE_FAILED = "vector_store_failed"
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


class SuccessCode(str, Enum):
    """Success codes for confirmations."""

    VECTOR_STORED = "vector_stored"
    VECTOR_SEARCHED = "vector_searched"
    VECTOR_DELETED = "vector_deleted"
    COLLECTION_CREATED = "collection_created"
    COLLECTION_DELETED = "collection_deleted"


# I18N-Ready Messages using Django gettext_lazy
MESSAGES: dict[str | ErrorCode | SuccessCode, str] = {
    # Generic
    ErrorCode.INTERNAL_ERROR: _("An unexpected error occurred in FractalMemory"),
    ErrorCode.INVALID_REQUEST: _("Invalid request to memory store"),
    # Vector Operations
    ErrorCode.VECTOR_STORE_FAILED: _("Failed to store vector"),
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
    # Success
    SuccessCode.VECTOR_STORED: _("Vector stored successfully"),
    SuccessCode.VECTOR_SEARCHED: _("Vector search completed"),
    SuccessCode.VECTOR_DELETED: _("Vector deleted successfully"),
    SuccessCode.COLLECTION_CREATED: _("Collection '{name}' created successfully"),
    SuccessCode.COLLECTION_DELETED: _("Collection '{name}' deleted successfully"),
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
    if kwargs:
        return str(msg).format(**kwargs)
    return str(msg)
