# A2A CLAIMS — file path locks

Format: `| path/prefix | agent | task | started_at | status |`
Status: ACTIVE | RELEASED | DONE
Before large edits, claim. Release when done.

| path/prefix | agent | task | started_at | status |
|---|---|---|---|---|
| infra/standalone/docker-compose.yml infra/standalone/seed_vault.py infra/standalone/.env | MiMoCode | F-06+F-15 curl-in-argv seeder + idempotent Vault seed + .env secret strip | 2026-10-10T18:30:00Z | DONE |
| infra/standalone/docker-compose.yml | soma-infra-health | TRIAD liveness: fix t0_ram tmpfs handoff lifetime (keeper + boot order) so postgres/minio/API can start | 2026-10-11T00:50:00Z | ACTIVE |
| somafractalmemory/api/schemas.py somafractalmemory/admin/core/models.py somafractalmemory/admin/core/services.py somafractalmemory/api/routers/memory.py somafractalmemory/api/routers/search.py somafractalmemory/api/routers/graph.py somafractalmemory/migrations/ | MiMoCode-sfm-integration | WAVE-SFM-INT: importance+belief+working_memory schema, store honesty, k_hop BFS, degraded flags, fail-closed Milvus (D1-D5/B17-B21) | 2026-10-11T17:07:58Z | ACTIVE |
| somafractalmemory/tests/unit/test_write_contract.py somafractalmemory/tests/unit/test_k_hop_honesty.py somafractalmemory/tests/unit/test_degraded_search.py | MiMoCode-sfm-integration | WAVE-SFM-INT: contract + k_hop + degraded tests | 2026-10-11T17:07:58Z | ACTIVE |
