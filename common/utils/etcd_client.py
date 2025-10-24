"""Lightweight Etcd client helpers for feature flag evaluation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from prometheus_client import Counter
from tenacity import retry, stop_after_attempt, wait_exponential

ETCD_OPS = Counter("etcd_ops_total", "Total Etcd client operations", ["method"])
ETCD_ERRORS = Counter("etcd_errors_total", "Etcd client errors", ["method"])
ETCD_RETRIES = Counter("etcd_retries_total", "Etcd client retry attempts", ["method"])

try:
    import etcd3
except ImportError:  # pragma: no cover - optional dependency
    etcd3 = None  # type: ignore


class EtcdFeatureFlagClient:
    """Fetch and watch feature flags stored in Etcd."""

    def __init__(
        self,
        *,
        host: str = "etcd.soma.svc.cluster.local",
        port: int = 2379,
        namespace: str = "soma",
        timeout: int = 5,
    ) -> None:
        if etcd3 is None:
            raise RuntimeError("etcd3 package must be installed to use EtcdFeatureFlagClient")
        self._namespace = namespace.rstrip("/")
        self._client = etcd3.client(host=host, port=port, timeout=timeout)

    def _key(self, flag_name: str) -> str:
        return f"/{self._namespace}/{flag_name}".replace("//", "/")

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        reraise=True,
    )
    def get_flag(self, flag_name: str, default: Any = None) -> Any:
        ETCD_OPS.labels(method="get_flag").inc()
        try:
            key = self._key(flag_name)
            value, _ = self._client.get(key)
            if value is None:
                return default
            try:
                return value.decode("utf-8")
            except Exception:  # pragma: no cover - defensive fallback
                return value
        except Exception as e:
            ETCD_ERRORS.labels(method="get_flag").inc()
            print(f"[EtcdFeatureFlagClient] get_flag({flag_name}) failed: {e}")
            raise

    def watch(self, flag_name: str, callback: Callable[[Any], None]) -> None:
        key = self._key(flag_name)

        def _handler(event):  # type: ignore[no-untyped-def]
            if event.value is None:
                callback(None)
            else:
                try:
                    callback(event.value.decode("utf-8"))
                except Exception:  # pragma: no cover
                    callback(event.value)

        self._client.add_watch_callback(key, _handler)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        reraise=True,
    )
    def close(self) -> None:
        ETCD_OPS.labels(method="close").inc()
        try:
            self._client.close()
        except Exception as e:
            ETCD_ERRORS.labels(method="close").inc()
            print(f"[EtcdFeatureFlagClient] close() failed: {e}")
            raise


__all__ = ["EtcdFeatureFlagClient"]
