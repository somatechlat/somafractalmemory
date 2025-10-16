# Installation Guide

## Prerequisites

- Docker and Docker Compose
- 4GB+ RAM
- 10GB+ free disk space

## Installation Steps

### 1. Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/somatechlat/somafractalmemory.git
cd somafractalmemory

# Start the services
docker compose up -d
```

### 2. Verifying Installation

```bash
# Check if services are running
docker compose ps

# Test the health endpoint
curl http://localhost:9595/healthz
```

## Configuration

The system can be configured through environment variables or a config file. See [Configuration Reference](../technical-manual/configuration.md) for details.

## Next Steps

- [Complete the Quick Start Tutorial](quick-start-tutorial.md)
- [Explore Features](features/)
- [Read the FAQ](faq.md)
