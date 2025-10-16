# Development Environment Setup

## Prerequisites Installation

### 1. Python Setup
```bash
# Install Python 3.10+
# macOS
brew install python@3.10

# Linux
sudo apt-get update
sudo apt-get install python3.10
```

### 2. Docker Setup
```bash
# macOS
brew install --cask docker

# Linux
curl -fsSL https://get.docker.com | sh
```

## Project Setup

### 1. Clone Repository
```bash
git clone https://github.com/somatechlat/somafractalmemory.git
cd somafractalmemory
```

### 2. Virtual Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate (Unix/macOS)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Start Services
```bash
# Start core services
docker compose --profile core up -d
```

## Verification Steps

### 1. Check Services
```bash
# Check service status
docker compose ps

# Check API health
curl http://localhost:9595/healthz
```

### 2. Run Tests
```bash
pytest tests/test_core.py -v
```

## Troubleshooting

### Common Issues

1. **Port Conflicts**
   ```bash
   # Check ports
lsof -i :9595
   ```

2. **Database Connection**
   ```bash
   # Check PostgreSQL
docker compose logs postgres
   ```
