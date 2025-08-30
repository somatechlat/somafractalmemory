# Configuration Guide

This project uses Dynaconf and environment variables (prefix `SOMA_`) for configuration. You can:
- Provide a `config.yaml` alongside your app
- Use environment variables to override values
- Pass a `config` dict to `create_memory_system()` in code

## Keys and Env Vars

- `redis`: Redis client options
  - `host` (env: `SOMA_REDIS__HOST`)
  - `port` (env: `SOMA_REDIS__PORT`)
  - `db` (env: `SOMA_REDIS__DB`)
  - `testing`: Use FakeRedis when true for tests/dev

- `qdrant`: Qdrant client options
  - `path`: Local on-disk storage (env: `SOMA_QDRANT__PATH`)
  - `location`/`url`/`host`: Remote connection options (envs: `SOMA_QDRANT__URL`, etc.)

- `memory_enterprise`: Core memory tuning
  - `vector_dim` (env: `SOMA_VECTOR_DIM`): Embedding size used by vector store and fallback
  - `pruning_interval_seconds` (env: `SOMA_PRUNING_INTERVAL_SECONDS`): Periodic decay cadence
  - `decay_thresholds_seconds`: Time thresholds for field removal
  - `decayable_keys_by_level`: Keys to remove at each threshold
  - `encryption_key`: Optional key for sensitive fields (if cryptography installed). When set, `task` and `code` fields are encrypted on store and decrypted on retrieve.
  - `max_memory_size`: Upper bound on total memories; older, low-importance episodic items are pruned when exceeded

- Langfuse
  - `langfuse_public` (env: `SOMA_LANGFUSE_PUBLIC`)
  - `langfuse_secret` (env: `SOMA_LANGFUSE_SECRET`)
  - `langfuse_host` (env: `SOMA_LANGFUSE_HOST`)

- Model
  - `SOMA_MODEL_NAME`: HF model name (fallback embeddings used if transformers unavailable)

## Precedence

1) Explicit `config` passed to `create_memory_system`
2) Environment variables (`SOMA_*`)
3) `config.yaml` loaded by Dynaconf

## Example `config.yaml`

See `config.example.yaml` for a ready-to-copy template.
