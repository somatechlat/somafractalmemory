"""Lightweight Etcd client helpers for feature flag evaluation."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

try:
    import etcd3
except ImportError:  # pragma: no cover - optional dependency
    etcd3 = None  # type: ignore

LOGGER = logging.getLogger(__name__)


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

    def get_flag(self, flag_name: str, default: Any = None) -> Any:
        key = self._key(flag_name)
        value, _ = self._client.get(key)
        if value is None:
            return default
        try:
            return value.decode("utf-8")
        except Exception:  # pragma: no cover - defensive fallback
            return value

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

    def close(self) -> None:
        self._client.close()


__all__ = ["EtcdFeatureFlagClient"]
