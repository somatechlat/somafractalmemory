# Frequently Asked Questions

## General Questions

### What is Soma Fractal Memory?
Soma Fractal Memory is a sophisticated memory management system that stores and retrieves information using fractal patterns for efficient organization.

### How does it work?
The system uses vector embeddings and importance scoring to organize memories in a hierarchical structure, allowing for efficient retrieval based on similarity and relevance.

## Technical Questions

### What databases does it use?
- PostgreSQL for key-value storage
- Redis for caching
- Qdrant for vector similarity search

### How do I monitor system health?
The system provides a `/healthz` endpoint and Prometheus metrics. See [Monitoring Guide](../technical-manual/monitoring.md).

### What are the system requirements?
- Docker and Docker Compose
- 4GB+ RAM
- 10GB+ disk space

## Troubleshooting

### Common Issues

#### Authentication Failed
Ensure you're using the correct bearer token (default: `devtoken`).

#### Service Won't Start
Check Docker logs and ensure all required services (PostgreSQL, Redis, Qdrant) are running.

#### Memory Not Found
Verify the memory was stored successfully and check the importance threshold in your search query.
