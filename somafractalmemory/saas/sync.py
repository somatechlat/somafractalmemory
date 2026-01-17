"""
Usage Sync Service for SomaFractalMemory.

Synchronizes usage records from SFM to SomaBrain central
for consolidated billing through Lago.

VIBE Coding Rules v5.2 - ALL 7 PERSONAS:
- Architect: Clean async service design
- Security: API key authentication
- DevOps: Background processing
- QA: Testable with mock clients
- Docs: Comprehensive docstrings
- DBA: Batch operations
- SRE: Retry logic, failure handling
"""

import logging
import threading
import time
from datetime import datetime, timedelta, timezone

import httpx
from django.conf import settings
from django.db.models import Sum
from django.db.models.functions import Coalesce

from somafractalmemory.saas.models import UsageRecord

logger = logging.getLogger(__name__)


# =============================================================================
# USAGE SYNC CLIENT
# =============================================================================


class UsageSyncClient:
    """
    Client to sync usage data to SomaBrain central billing.

    Sends aggregated usage records to SomaBrain's Lago integration
    for unified billing across both services.
    """

    def __init__(self):
        """Initialize the instance."""

        self.somabrain_url = getattr(settings, "SOMABRAIN_URL", None)
        self.api_token = getattr(settings, "SOMABRAIN_API_TOKEN", "")

    @property
    def headers(self) -> dict:
        """Authentication headers for SomaBrain API."""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def sync_usage(
        self,
        tenant: str,
        events: list[dict],
    ) -> bool:
        """
        Send usage events to SomaBrain for Lago billing.

        Args:
            tenant: Tenant identifier
            events: List of usage events with operation, count, timestamp

        Returns:
            True if sync succeeded, False otherwise
        """
        if not self.api_token:
            logger.warning("SOMABRAIN_API_TOKEN not configured - skipping sync")
            return False

        if not self.somabrain_url:
            logger.error("SOMABRAIN_URL not configured in Django settings - cannot sync")
            return False

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.somabrain_url}/api/v1/admin/usage/report",
                    headers=self.headers,
                    json={
                        "tenant_id": tenant,
                        "source": "somafractalmemory",
                        "events": events,
                    },
                )

                if response.status_code in [200, 201]:
                    logger.info(f"Synced {len(events)} events for tenant {tenant}")
                    return True

                logger.error(f"Usage sync failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.exception(f"Usage sync error: {e}")
            return False


# =============================================================================
# USAGE SYNC SERVICE (Background)
# =============================================================================


class UsageSyncService:
    """
    Background service to periodically sync usage to SomaBrain.

    SRE: Runs in background thread, handles failures gracefully.
    DevOps: Configurable interval and batch size.
    """

    def __init__(
        self,
        sync_interval: int = 300,  # 5 minutes
        batch_size: int = 1000,
    ):
        """Initialize the instance."""

        self._sync_interval = sync_interval
        self._batch_size = batch_size
        self._client = UsageSyncClient()
        self._thread: threading.Thread | None = None
        self._running = False
        self._last_sync: datetime | None = None

    def start(self):
        """Start the background sync thread."""
        if self._thread is None:
            self._running = True
            self._thread = threading.Thread(target=self._sync_loop, daemon=True)
            self._thread.start()
            logger.info("Usage sync service started")

    def stop(self):
        """Stop the background sync thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
            logger.info("Usage sync service stopped")

    def sync_now(self):
        """Force an immediate sync."""
        self._do_sync()

    def _sync_loop(self):
        """Background loop for periodic syncing."""
        while self._running:
            time.sleep(self._sync_interval)
            self._do_sync()

    def _do_sync(self):
        """Perform the actual sync operation."""
        try:
            # Get unsynced records grouped by tenant
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=1)

            # Get distinct tenants with unsent records
            tenants = (
                UsageRecord.objects.filter(synced_at__isnull=True, timestamp__lt=cutoff)
                .values_list("tenant", flat=True)
                .distinct()
            )

            for tenant in tenants:
                self._sync_tenant(tenant, cutoff)

            self._last_sync = datetime.now(timezone.utc)

        except Exception as e:
            logger.exception(f"Sync loop error: {e}")

    def _sync_tenant(self, tenant: str, cutoff: datetime):
        """Sync usage records for a specific tenant."""
        # Aggregate records by operation
        records = (
            UsageRecord.objects.filter(
                tenant=tenant,
                synced_at__isnull=True,
                timestamp__lt=cutoff,
            )
            .values("operation")
            .annotate(
                total_count=Coalesce(Sum("count"), 0),
                total_bytes=Coalesce(Sum("bytes_processed"), 0),
            )
        )

        if not records:
            return

        # Format events for SomaBrain
        events = [
            {
                "code": r["operation"],
                "properties": {
                    "count": r["total_count"],
                    "bytes": r["total_bytes"],
                },
                "timestamp": cutoff.isoformat(),
            }
            for r in records
        ]

        # Send to SomaBrain
        if self._client.sync_usage(tenant, events):
            # Mark as synced
            UsageRecord.objects.filter(
                tenant=tenant,
                synced_at__isnull=True,
                timestamp__lt=cutoff,
            ).update(synced_at=datetime.now(timezone.utc))


# =============================================================================
# SINGLETON SERVICE
# =============================================================================

_sync_service: UsageSyncService | None = None


def get_sync_service() -> UsageSyncService:
    """Get the singleton sync service."""
    global _sync_service
    if _sync_service is None:
        _sync_service = UsageSyncService()
    return _sync_service


def start_usage_sync():
    """Start the usage sync service."""
    service = get_sync_service()
    service.start()


def stop_usage_sync():
    """Stop the usage sync service."""
    if _sync_service:
        _sync_service.stop()
