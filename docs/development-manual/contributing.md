---
title: "Contribution Guidelines"
purpose: "Guide developers on contributing to SomaFractalMemory"
audience: "Developers and contributors"
last_updated: "2025-10-16"
review_frequency: "quarterly"
---

# Contributing to SomaFractalMemory

## Overview
This guide explains how to contribute to SomaFractalMemory effectively. We welcome contributions of all kinds, from bug fixes to feature enhancements.

## Quick Start

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Development Setup

### Prerequisites
- Python 3.10+
- Docker and Docker Compose
- PostgreSQL 14+
- Redis 6+
- Qdrant latest

### Local Environment
```bash
# Clone repository
git clone https://github.com/yourusername/somafractalmemory.git
cd somafractalmemory

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r api-requirements.txt

# Start development services
docker compose up -d
```

## Coding Standards

### Python Style Guide
- Follow PEP 8
- Use type hints
- Document functions
- Write tests

### Example
```python
from typing import Optional, List

def find_memories(
    query: str,
    limit: Optional[int] = 10
) -> List[Memory]:
    """Find memories matching the query.

    Args:
        query: Search query string
        limit: Maximum number of results

    Returns:
        List of matching Memory objects

    Raises:
        ValueError: If query is empty
    """
    if not query:
        raise ValueError("Query cannot be empty")

    return Memory.search(query, limit=limit)
```

### Code Organization
```
somafractalmemory/
├── core/              # Core functionality
├── interfaces/        # API interfaces
├── implementations/   # Feature implementations
└── utils/            # Shared utilities
```

## Git Workflow

### Branch Naming
- Feature: `feature/description`
- Fix: `fix/issue-description`
- Release: `release/version`

### Commit Messages
```
type(scope): description

[optional body]

[optional footer]
```

Types:
- feat: New feature
- fix: Bug fix
- docs: Documentation
- style: Formatting
- refactor: Code restructuring
- test: Adding tests
- chore: Maintenance

### Example
```
feat(vector): add cosine similarity search

- Implement cosine similarity in vector store
- Add configuration options
- Update documentation

Closes #123
```

## Testing

### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_vector_store.py

# Run with coverage
pytest --cov=somafractalmemory
```

### Writing Tests
```python
from somafractalmemory import Memory

def test_memory_creation():
    """Test basic memory creation."""
    memory = Memory(content="Test content")
    assert memory.content == "Test content"
    assert memory.id is not None

def test_memory_vector_search():
    """Test vector similarity search."""
    memories = Memory.search_vector(
        vector=[0.1, 0.2, 0.3],
        limit=5
    )
    assert len(memories) <= 5
    assert all(isinstance(m, Memory) for m in memories)
```

## Documentation

### Code Documentation
- Docstrings for all public APIs
- Type hints for parameters
- Usage examples
- Exception documentation

### Example
```python
class Memory:
    """Represents a stored memory.

    Attributes:
        id: Unique identifier
        content: Memory content
        vector: Optional embedding vector
        metadata: Additional metadata

    Example:
        ```python
        memory = Memory(content="Example")
        memory.store()
        ```
    """
```

### Project Documentation
- Update relevant .md files
- Add migration guides
- Document breaking changes
- Update examples

## Pull Request Process

1. **Create Issue**
   - Describe the change
   - Get feedback
   - Link related issues

2. **Prepare Changes**
   - Create branch
   - Make changes
   - Add tests
   - Update docs

3. **Submit PR**
   - Fill template
   - Link issues
   - Request review

4. **Review Process**
   - Address feedback
   - Update changes
   - Maintain clean history

### PR Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Added tests
- [ ] Updated tests
- [ ] All tests pass

## Documentation
- [ ] Updated docs
- [ ] Added examples
- [ ] No docs needed

## Related Issues
Fixes #123
```

## Release Process

### Version Numbers
- Follow semantic versioning
- Format: MAJOR.MINOR.PATCH
- Document breaking changes

### Release Steps
1. Update version
2. Update changelog
3. Create release branch
4. Run tests
5. Create tag
6. Deploy release

### Example Changelog
```markdown
## [1.2.0] - 2025-10-16

### Added
- Vector similarity search
- Cache optimization
- New API endpoints

### Changed
- Improved performance
- Updated dependencies
- Enhanced documentation

### Fixed
- Memory leak in vector store
- Connection handling
- Cache invalidation
```

## Community

### Getting Help
- GitHub Issues
- Discussion Forum
- Stack Overflow
- Community Chat

### Communication
- Be respectful
- Be clear
- Be helpful
- Follow CoC

## Best Practices

1. **Code Quality**
   - Write clean code
   - Add comments
   - Follow style guide
   - Write tests

2. **Documentation**
   - Keep it updated
   - Add examples
   - Explain changes
   - Link resources

3. **Testing**
   - Unit tests
   - Integration tests
   - Performance tests
   - Documentation tests

## Further Reading
- [Development Manual](../development-manual/index.md)
- [Architecture Guide](../technical-manual/architecture.md)
- [API Reference](api-reference.md)
- [Testing Guide](testing-guidelines.md)
