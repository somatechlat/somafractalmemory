# Contributing to SomaFractalMemory

> Last updated: 2026-05-18

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/somafractalmemory.git`
3. Install dependencies: `pip install -e ".[dev]"`
4. Copy `.env.example` to `.env` and configure
5. Run tests: `pytest tests/`

## Development Workflow

- Create a feature branch: `git checkout -b feature/your-feature`
- Make focused, minimal changes
- Add tests for new functionality
- Run the test suite before committing
- Submit a pull request with a clear description

## Code Standards

- **100% Django**: No SQLAlchemy, no FastAPI
- Use Django ORM for all database access
- Use Django Ninja for API endpoints
- Follow PEP 8 style guidelines (line length: 100)
- Type hints encouraged for public APIs

## Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=somafractalmemory

# Run specific test file
pytest tests/unit/test_memory.py
```

## Documentation

- Update relevant docs when changing behavior
- Keep `openapi.json` in sync with API changes
- Document new environment variables in `docs/deployment.md`

## Commit Messages

Follow conventional commits:

```
feat: add new memory search filter
docs: update API examples
fix: correct graph path response format
refactor: simplify health check logic
```

## Questions?

Open an issue on GitHub or reach out to the maintainers.
