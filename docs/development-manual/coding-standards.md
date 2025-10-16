# Coding Standards

## Code Style

### Python

- Follow PEP 8
- Use black for formatting
- Maximum line length: 100 characters
- Use type hints for all functions

```python
# Good
def calculate_importance(memory_age: float, access_count: int) -> float:
    """Calculate memory importance based on age and access count.

    Args:
        memory_age: Time since memory creation in seconds
        access_count: Number of times memory was accessed

    Returns:
        Normalized importance score between 0 and 1
    """
    raw_score = access_count / (1 + memory_age / 3600)
    return min(1.0, raw_score / 100)

# Bad
def calc_imp(age, count):
    return min(1.0, (count / (1 + age / 3600)) / 100)
```

## Documentation

### Docstrings

- Required for all public functions/methods
- Use Google style
- Include type hints
- Document exceptions

### Comments

- Explain why, not what
- Keep current and relevant
- Remove commented-out code

## Testing

- Use pytest
- Test coverage > 80%
- Mock external dependencies
- Use descriptive test names

## Version Control

### Commit Messages

```
type(scope): description

Body text here

Refs: #123
```

Types:
- feat: new feature
- fix: bug fix
- docs: documentation
- style: formatting
- refactor: code restructuring
- test: adding tests
- chore: maintenance
