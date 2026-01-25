# SomaFractalMemory Standalone Deployment

**ISOLATION LEVEL: HIGH**

This directory contains the **Standalone** deployment configuration for SomaFractalMemory.
It is **COMPLETELY ISOLATED** from the AAAS (Agent-As-A-Service) deployment.

## Architecture
- **Service Type**: Microservice (HTTP API)
- **Container Prefix**: `somafractalmemory_standalone_`
- **Network**: `somafractalmemory_standalone_net`

## Port Isolation (10xxx Range)
| Service | Internal Port | Host Port | Container Name |
|---------|---------------|-----------|----------------|
| API | 10101 | 10101 | `somafractalmemory_standalone_api` |
| PostgreSQL | 5432 | 10432 | `somafractalmemory_standalone_postgres` |
| Redis | 6379 | 10379 | `somafractalmemory_standalone_redis` |
| Milvus | 19530 | 10530 | `somafractalmemory_standalone_milvus` |

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
