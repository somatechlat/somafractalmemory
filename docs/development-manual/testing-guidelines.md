# Testing Guidelines

## Test Structure

### Unit Tests

- Test individual components in isolation
- Mock external dependencies
- Fast execution

Example:
```python
def test_memory_importance_calculation():
    # Arrange
    memory_age = 3600  # 1 hour
    access_count = 10

    # Act
    importance = calculate_importance(memory_age, access_count)

    # Assert
    assert 0 <= importance <= 1
    assert importance == pytest.approx(0.05, rel=1e-2)
```

### Integration Tests

- Test component interactions
- Use test containers for databases
- Clean up test data

### End-to-End Tests

- Test complete workflows
- Run against real services
- Part of CI/CD pipeline

## Test Data

### Fixtures

```python
@pytest.fixture
def memory_store():
    store = PostgresKeyValueStore("postgresql://test:test@localhost/test")
    yield store
    store.clear()  # cleanup
```

### Test Cases

- Cover edge cases
- Include error conditions
- Use parameterized tests

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=somafractalmemory

# Generate coverage report
pytest --cov=somafractalmemory --cov-report=html
```

## CI Integration

- Tests run on every PR
- Coverage reports uploaded
- Required for merge
