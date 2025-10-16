# Local Development Setup

## Prerequisites

- Python 3.10+
- Docker and Docker Compose
- Make (optional)

## Quick Setup

```bash
# Clone repository
git clone https://github.com/somatechlat/somafractalmemory.git
cd somafractalmemory

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
```

## Starting Services

```bash
# Build and start services
make compose-build
make compose-up

# Or using docker compose directly:
docker compose build
docker compose up -d
```

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_core.py

# Run with coverage
pytest --cov=somafractalmemory
```

## Development Tools

### Pre-commit Hooks
```bash
pre-commit install
```

### Code Formatting
```bash
# Format code
black .

# Check types
mypy .
```

## IDE Setup

### VS Code

1. Install Python extension
2. Select Python interpreter (.venv)
3. Enable format on save
4. Install recommended extensions
