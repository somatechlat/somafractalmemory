import json

import pytest

from somafractalmemory.serialization import deserialize, serialize


def test_serialize_returns_utf8_json_bytes():
    obj = {"a": 1, "b": "text", "c": [1, 2, 3]}
    b = serialize(obj)
    assert isinstance(b, (bytes, bytearray))
    # Ensure it's valid UTF-8 JSON and matches a standard dump with the same separators
    assert b.decode("utf-8") == json.dumps(obj, separators=(",", ":"))


def test_deserialize_valid_json_roundtrip():
    obj = {"x": "y", "n": 5}
    b = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    assert deserialize(b) == obj


def test_deserialize_none_returns_none():
    assert deserialize(None) is None


def test_deserialize_invalid_bytes_raises_valueerror():
    # Non-UTF-8 / non-JSON bytes must raise ValueError (no pickle fallback)
    invalid = b"\x80\x04\x95\x00\x00"
    with pytest.raises(ValueError):
        deserialize(invalid)
