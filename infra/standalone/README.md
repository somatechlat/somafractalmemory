# SomaFractalMemory Standalone Deployment

**ISOLATION LEVEL: HIGH**

This directory contains the **Standalone** deployment configuration for SomaFractalMemory.
It is **COMPLETELY ISOLATED** from the AAAS (Agent-As-A-Service) deployment.

## Architecture
- **Service Type**: Microservice (HTTP API)
- **Container Prefix**: `somafractalmemory-standalone-`
- **Network**: `somafractalmemory-standalone-net`

## Port Isolation (10xxx Range)
| Service | Internal Port | Host Port | Container Name |
|---------|---------------|-----------|----------------|
| API | 10101 | 10101 | `somafractalmemory-standalone-api` |
| PostgreSQL | 5432 | 10432 | `somafractalmemory-standalone-postgres` |
| Redis | 6379 | 10379 | `somafractalmemory-standalone-redis` |
| Milvus | 19530 | 10530 | `somafractalmemory-standalone-milvus` |

## Usage
Run from the root of the repository via Makefile:

```bash
# Start Standalone Cluster
make compose-up

# View Logs
make compose-logs

# Stop Cluster
make compose-down
```

## Difference from AAAS
- **Standalone**: Runs its own Django process, DB, Redis, and Milvus.
- **AAAS**: Runs inside `somaAgent01` unified process, sharing infrastructure with Agent and Brain.
