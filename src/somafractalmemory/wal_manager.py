# wal_manager.py - Handles Write-Ahead Logging

import logging
import pickle
import time
import uuid
from typing import Any, Dict

logger = logging.getLogger(__name__)

class WALManager:
    def __init__(self, namespace: str, kv_store: Any) -> None:
        self.namespace = namespace
        self.kv_store = kv_store

    def _wal_key(self, wid: str) -> str:
        return f"{self.namespace}:wal:{wid}"

    def write(self, entry: Dict[str, Any]) -> str:
        wid = str(uuid.uuid4())
        payload = dict(entry)
        payload.update({"id": wid, "status": "pending", "ts": time.time()})
        self.kv_store.set(self._wal_key(wid), pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL))
        return wid

    def commit(self, wid: str) -> None:
        try:
            raw = self.kv_store.get(self._wal_key(wid))
            if not raw:
                return
            entry = pickle.loads(raw)
            entry["status"] = "committed"
            self.kv_store.set(self._wal_key(wid), pickle.dumps(entry, protocol=pickle.HIGHEST_PROTOCOL))
        except Exception:
            pass

    def fail(self, wid: str, error: str = "") -> None:
        try:
            raw = self.kv_store.get(self._wal_key(wid))
            if not raw:
                return
            entry = pickle.loads(raw)
            entry["status"] = "failed"
            if error:
                entry["error"] = error
            self.kv_store.set(self._wal_key(wid), pickle.dumps(entry, protocol=pickle.HIGHEST_PROTOCOL))
        except Exception:
            pass

    def reconcile_once(self) -> None:
        for wal_key in self.kv_store.scan_iter(f"{self.namespace}:wal:*"):
            try:
                raw = self.kv_store.get(wal_key)
                if not raw:
                    continue
                entry = pickle.loads(raw)
                if entry.get("status") in {"pending", "failed"}:
                    # Assume apply logic here or delegate
                    logger.info(f"Reconciling WAL entry {entry.get('id')}")
                    # For now, mark as committed
                    entry["status"] = "committed"
                    self.kv_store.set(wal_key, pickle.dumps(entry, protocol=pickle.HIGHEST_PROTOCOL))
            except Exception as e:
                logger.warning(f"Error during WAL reconcile for {wal_key}: {e}")
