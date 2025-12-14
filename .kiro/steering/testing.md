---
inclusion: always
---

# Testing Guidelines

## Test Infrastructure

**All tests require real infrastructure** - no fakeredis, no mocks.

Required services (via `docker compose --profile core up -d`):
- PostgreSQL (port 5433)
- Redis (port 6379 or 6381)
- Milvus (port 19530)

## Running Tests

```bash
# Start infrastructure
docker compose --profile core up -d

# Run all tests
pytest

# Run specific test file
pytest tests/test_factory.py

# Run with verbose output
pytest -v --tb=short
```

## Test Organization

```
tests/
├── conftest.py              # Shared fixtures, infra detection
├── test_factory.py          # Factory function tests
├── test_end_to_end_memory.py # Full memory lifecycle tests
├── test_live_integration.py # Real infra integration tests
├── test_fast_core_math.py   # Math/embedding tests
└── test_*.py                # Feature-specific tests
```

## Writing Tests

### Use Real Services

```python
# CORRECT - uses real Redis/Postgres/Milvus
def test_memory_store(memory_system):
    memory_system.store_memory(coord, payload, MemoryType.EPISODIC)
    result = memory_system.retrieve(coord)
    assert result is not None

# WRONG - never do this
def test_with_mock():
    mock_store = Mock()  # NO MOCKS!
```

### Skip When Infra Unavailable

```python
import os
import pytest

@pytest.mark.skipif(
    os.environ.get("SOMA_INFRA_AVAILABLE") != "1",
    reason="Requires live infrastructure"
)
def test_integration_feature():
    ...
```

### Test Fixtures

The `conftest.py` provides:
- Auto-detection of running services
- Environment variable setup for test runs
- Automatic compose service startup if needed

## Property-Based Testing

Use `hypothesis` for property tests:

```python
from hypothesis import given, strategies as st

@given(st.floats(allow_nan=False), st.floats(allow_nan=False))
def test_coordinate_roundtrip(x, y):
    coord = (x, y)
    # Test that store/retrieve preserves data
```

## Test Data

- Mark test data clearly
- Use deterministic seeds for reproducibility
- Clean up test data after runs (factory.py handles namespace cleanup)
