"""JSON-only serialization helpers for SomaFractalMemory.

This module centralizes serialization and enforces JSON (UTF-8) as the
sole on-disk/network format. No legacy binary Python serialization or fallback is
used in v2 to avoid insecure deserialization vectors.
"""

from __future__ import annotations

import json
from typing import Any


def serialize(obj: Any) -> bytes:
    """Serialize an object to bytes using JSON (utf-8).

    This function intentionally uses JSON as the primary format. If an object
    is not JSON-serializable, callers should pre-convert complex types to JSON
    friendly structures before calling.
    """
    return json.dumps(obj, default=_json_default, separators=(",", ":")).encode("utf-8")


def deserialize(raw: bytes) -> Any:
    """Deserialize bytes to Python object.

    Parse bytes as UTF-8 JSON. Raises ValueError when data is not valid JSON.
    """
    if raw is None:
        return None
    try:
        text = raw.decode("utf-8")
    except Exception:
        text = None

    if text is not None:
        try:
            return json.loads(text)
        except Exception:
            pass

    # JSON failed — raise. No legacy binary Python serialization fallback permitted in v2.
    raise ValueError(
        "Data is not valid JSON; legacy binary Python serialization fallback removed in v2"
    )


def _json_default(o: Any):
    """Fallback serializer for JSON for a few common types."""
    # Keep this minimal; prefer to normalize objects upstream
    if hasattr(o, "isoformat"):
        try:
            return o.isoformat()
        except Exception:
            pass
    if isinstance(o, bytes):
        try:
            return o.decode("utf-8")
        except Exception:
            return list(o)
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")
