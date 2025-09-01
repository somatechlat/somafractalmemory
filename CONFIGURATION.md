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

- `vector`: Vector backend selection and tuning
  - `backend`: one of `inmemory`, `fractal`, `faiss_aperture`, `qdrant`
  - `fractal_enabled` (bool): when `backend: inmemory`, enable fractal path (env: `SFM_FRACTAL_BACKEND=1`)
  - `fractal`: options for the fractal backend
    - `centroids` (int, optional): number of coarse clusters (auto ≈ sqrt(N) if omitted)
    - `beam_width` (int): number of top centroids to explore (default 4)
    - `max_candidates` (int): cap before exact rerank (default 1024)
    - `rebuild_enabled` (bool): periodic/background rebuilds (default true)
    - `rebuild_size_delta` (float): rebuild when size grows by this fraction (default 0.1)
    - `rebuild_interval_seconds` (int): periodic rebuild cadence (default 600)

- `memory_enterprise`: Core memory tuning
  - `vector_dim` (env: `SOMA_VECTOR_DIM`): Embedding size used by vector store and fallback
  - `pruning_interval_seconds` (env: `SOMA_PRUNING_INTERVAL_SECONDS`): Periodic decay cadence
  - `decay_thresholds_seconds`: Time thresholds for field removal
  - `decayable_keys_by_level`: Keys to remove at each threshold
  - `encryption_key`: Optional key for sensitive fields (if cryptography installed). When set, `task` and `code` fields are encrypted on store and decrypted on retrieve.
  - `max_memory_size`: Upper bound on total memories; older, low-importance episodic items are pruned when exceeded
  - `salience`: Novelty gate and salience tuning
    - `novelty_gate` (bool): enable novelty-based write gate (default false)
    - `novelty_threshold` (float 0..1): gating threshold (default 0.0)
    - `weights` (dict optional): internal weighting, e.g. `{novelty: 1.0, error: 0.0}`

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

Minimal example you can copy into config.yaml:

```yaml
redis:
  testing: true  # use in-memory FakeRedis for local/dev

qdrant:
  path: ./qdrant.db  # or set url/host for remote

memory_enterprise:
  vector_dim: 768
  pruning_interval_seconds: 600
  max_memory_size: 100000
  salience:
    novelty_gate: true
    novelty_threshold: 0.4

vector:
  backend: fractal
  fractal:
    centroids: 64
    beam_width: 4
```
