"""
Usage Tracking Middleware for SomaFractalMemory.

Automatically meters API calls for billing integration.
Records to UsageRecord model for aggregation and reporting.

VIBE Coding Rules v5.2 - ALL 7 PERSONAS:
- Architect: Clean middleware design
- Security: Tenant isolation
- DevOps: Async batching for performance
- QA: Testable with mock requests
- Docs: Comprehensive docstrings
- DBA: Batch inserts for efficiency
- SRE: Non-blocking, failure-tolerant
"""

import logging
import threading
import time
from collections import defaultdict
from datetime import UTC, datetime

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

from somafractalmemory.admin.aaas.models import UsageRecord

logger = logging.getLogger(__name__)


# =============================================================================
# USAGE BUFFER (Batch inserts for performance)
# =============================================================================


class UsageBuffer:
    """
    Thread-safe buffer for usage records.

    Collects usage events and flushes them to the database
    in batches for better performance.

    SRE: Non-blocking, failure-tolerant
    DBA: Batch inserts reduce database load
    """

    def __init__(self, flush_interval: int = 30, max_size: int = 100):
        """Initialize the instance."""

        self._buffer: list[dict] = []
        self._lock = threading.Lock()
        self._flush_interval = flush_interval
        self._max_size = max_size
        self._last_flush = time.time()
        self._flush_thread = None
        self._running = False

    def start(self) -> None:
        """Start the background flush thread."""
        if self._flush_thread is None:
            self._running = True
            self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
            self._flush_thread.start()

    def stop(self) -> None:
        """Stop the background flush thread."""
        self._running = False
        if self._flush_thread:
            self._flush_thread.join(timeout=5)

    def add(
        self,
        tenant: str,
        operation: str,
        count: int = 1,
        bytes_processed: int = 0,
        api_key_id: str | None = None,
    ) -> None:
        """Add a usage event to the buffer."""
        with self._lock:
            self._buffer.append(
                {
                    "tenant": tenant,
                    "operation": operation,
                    "count": count,
                    "bytes_processed": bytes_processed,
                    "api_key_id": api_key_id,
                    "timestamp": datetime.now(UTC),
                }
            )

            # Flush if buffer is full
            if len(self._buffer) >= self._max_size:
                self._flush()

    def _flush_loop(self) -> None:
        """Background loop to periodically flush buffer."""
        while self._running:
            time.sleep(self._flush_interval)
            with self._lock:
                if self._buffer:
                    self._flush()

    def _flush(self) -> None:
        """Flush buffer to database."""
        if not self._buffer:
            return

        records = self._buffer.copy()
        self._buffer.clear()

        try:
            # Aggregate records by tenant+operation for efficiency
            aggregated: dict[tuple, dict] = defaultdict(lambda: {"count": 0, "bytes_processed": 0})

            for record in records:
                key = (record["tenant"], record["operation"])
                aggregated[key]["count"] += record["count"]
                aggregated[key]["bytes_processed"] += record["bytes_processed"]

            # Batch create
            usage_records = [
                UsageRecord(
                    tenant=tenant,
                    operation=operation,
                    count=data["count"],
                    bytes_processed=data["bytes_processed"],
                )
                for (tenant, operation), data in aggregated.items()
            ]

            UsageRecord.objects.bulk_create(usage_records)
            logger.debug(f"Flushed {len(usage_records)} usage records")

        except Exception as e:
            logger.error(f"Failed to flush usage records: {e}")
            # Re-add to buffer on failure (best effort)
            with self._lock:
                self._buffer.extend(records[:50])  # Limit to avoid memory issues


# Singleton buffer instance
_usage_buffer: UsageBuffer | None = None


def get_usage_buffer() -> UsageBuffer:
    """Get the singleton usage buffer."""
    global _usage_buffer
    if _usage_buffer is None:
        _usage_buffer = UsageBuffer()
        _usage_buffer.start()
    return _usage_buffer


# =============================================================================
# MIDDLEWARE
# =============================================================================


class UsageTrackingMiddleware(MiddlewareMixin):
    """
    Django middleware to track API usage for billing.

    Records:
    - Operation type (based on URL path)
    - Response size
    - Tenant from auth context

    Non-blocking: Uses buffer for async recording.
    """

    # Operation mapping based on URL patterns
    OPERATION_MAP = {
        "/memories": "memory_store",
        "/graph": "graph_link",
        "/search": "vector_search",
        "/admin": "admin_operation",
    }

    def process_response(
        self,
        request: HttpRequest,
        response: HttpResponse,
    ) -> HttpResponse:
        """Record usage after each request."""
        # Skip non-API requests
        if not request.path.startswith("/api/"):
            return response

        # Skip failures (don't bill for errors)
        if response.status_code >= 400:
            return response

        # Get tenant from auth
        auth = getattr(request, "auth", {})
        tenant = auth.get("tenant")

        if not tenant:
            return response

        # Determine operation type
        operation = self._get_operation(request)

        # Get response size
        content_length = len(response.content) if hasattr(response, "content") else 0

        # Record async
        try:
            buffer = get_usage_buffer()
            buffer.add(
                tenant=tenant,
                operation=operation,
                count=1,
                bytes_processed=content_length,
                api_key_id=auth.get("api_key_id") or "",
            )
        except Exception as e:
            logger.warning(f"Failed to record usage: {e}")

        return response

    def _get_operation(self, request: HttpRequest) -> str:
        """Determine operation type from request."""
        path = request.path.lower()

        for pattern, operation in self.OPERATION_MAP.items():
            if pattern in path:
                return operation

        return "api_call"


# =============================================================================
# MANUAL TRACKING HELPERS
# =============================================================================


def track_usage(
    tenant: str,
    operation: str,
    count: int = 1,
    bytes_processed: int = 0,
    api_key_id: str | None = None,
) -> None:
    """
    Manually track a usage event.

    Use this for operations that need explicit tracking,
    like background jobs or internal operations.
    """
    try:
        buffer = get_usage_buffer()
        buffer.add(
            tenant=tenant,
            operation=operation,
            count=count,
            bytes_processed=bytes_processed,
            api_key_id=api_key_id,
        )
    except Exception as e:
        logger.warning(f"Failed to track usage: {e}")


def flush_usage() -> None:
    """Force flush the usage buffer."""
    buffer = get_usage_buffer()
    buffer._flush()
