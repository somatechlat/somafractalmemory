# SomaFractalMemory API Usage Guide

This guide explains how to use every public endpoint of the SomaFractalMemory (SFM) API, including inputs/outputs, parameters, environment settings, and real examples. It reflects the live server at port 9595 and the FastAPI app in `examples/api.py`.

- Base URL: http://localhost:9595
- Auth: Optional Bearer token via `SOMA_API_TOKEN` (when set, required on all endpoints except health/ready/metrics).
- Rate limiting: Global soft limit via `SOMA_RATE_LIMIT_MAX` and `SOMA_RATE_LIMIT_WINDOW_SECONDS` with 429 responses once exceeded.
- Namespacing: `SOMA_MEMORY_NAMESPACE` names the collection in vector/graph stores (default `api_ns`).
- Mode: `MEMORY_MODE` controls the backend wiring: `development` (default), `test`, `evented_enterprise`, `cloud_managed`.
- Hybrid default: Core recall uses hybrid scoring by default; toggle with `SOMA_HYBRID_RECALL_DEFAULT`.

## Environment settings (server)

- MEMORY_MODE: development | test | evented_enterprise | cloud_managed
- SOMA_MEMORY_NAMESPACE: string, default api_ns
- SOMA_API_TOKEN: if set, API requires `Authorization: Bearer <token>`
- SOMA_RATE_LIMIT_MAX: int, default 60 (requests/window)
- SOMA_RATE_LIMIT_WINDOW_SECONDS: float, default 60
- SOMA_HYBRID_RECALL_DEFAULT: 1|0 (default behavior in core.recall)
- SOMA_FORCE_HASH_EMBEDDINGS: enable hash embeddings fallback; prefer this over SOMA_FAST_START
- Postgres: POSTGRES_URL (e.g., postgresql://postgres:postgres@localhost:5433/somamemory)
- Redis: REDIS_URL or REDIS_HOST/REDIS_PORT/REDIS_DB
- Qdrant: QDRANT_URL or QDRANT_HOST/QDRANT_PORT
- Kafka (evented_enterprise): KAFKA_BOOTSTRAP_SERVERS, EVENTING_ENABLED=true

## Conventions

- Coordinates are string triples: "x,y,z" parsed as floats.
- Memory types: `episodic` or `semantic`.
- Filters refer to payload key/value filters for hybrid find operations.

## Health and system

1) GET /health
   - Purpose: Simple overall health summary from core (kv/vector/graph/prediction).
   - Returns: { kv_store: bool, vector_store: bool, graph_store: bool, prediction_provider: bool }
   - Auth: Not required.

2) GET /healthz
   - Purpose: Liveness probe. Direct store checks.
   - Returns: HealthResponse (same shape as /health).
   - Auth: Not required.

3) GET /readyz
   - Purpose: Readiness probe.
   - Returns: HealthResponse.
   - Auth: Not required.

4) GET /stats
   - Purpose: Basic memory counts.
   - Returns: { total_memories, episodic, semantic }
   - Auth: Bearer required if SOMA_API_TOKEN set.

## Memory write and bulk

5) POST /store
   - Body: { coord: "x,y,z", payload: {..}, type: "episodic"|"semantic" (default episodic) }
   - Purpose: Store one memory.
   - Returns: { ok: true }
   - When to use: single inserts, task logs, events.

6) POST /store_bulk
   - Body: { items: [ { coord, payload, type }, ... ] }
   - Purpose: Efficient batch insert.
   - Returns: { stored: N }
   - When to use: backfills, large ingestion.

## Recall and search

7) POST /recall
   - Body: { query: string, top_k?: int=5, type?: "episodic"|"semantic", filters?: object, hybrid?: bool }
   - Behavior:
     - If filters present → mem.find_hybrid_by_type(query, filters)
     - Else if hybrid=true → mem.hybrid_recall(query)
     - Else → mem.recall(query) (uses hybrid in core by default if toggled)
   - Returns: { matches: [ { ...payload... }, ... ] }
   - Use cases: semantic retrieval; hybrid if you want keyword boosting.

8) POST /recall_batch
   - Body: { queries: [string], top_k?: int=5, type?:, filters?:, hybrid?: }
   - Purpose: Multi-query recall; falls back to invoking recall/find per query.
   - Returns: { batches: [ [payloads...], ... ] }
   - Use cases: querying multiple prompts at once.

9) POST /recall_with_scores
   - Query params: query (string), top_k=5, type? (episodic|semantic), hybrid? (bool), exact?=true, case_sensitive?=false
   - Behavior:
     - If hybrid=true → mem.hybrid_recall_with_scores(query, exact, case_sensitive)
     - Else → mem.recall_with_scores(query)
   - Returns: { results: [ { payload, score }, ... ] }
   - Use cases: need scores for ranking/thresholding.

10) POST /recall_with_context
    - Query params: query (string), top_k=5, type? (episodic|semantic)
    - Body: context: object
    - Purpose: Context-aware hybrid recall (mem.find_hybrid_with_context)
    - Returns: { results: [ payloads... ] }
    - Use cases: conversational memory with session/user context.

11) POST /keyword_search
    - Body: { term: string, exact=true, case_sensitive=false, top_k=50, type? }
    - Purpose: Pure keyword retrieval leveraging Postgres JSONB pg_trgm fast path when available, falling back to KV scan.
    - Returns: { results: [ payloads... ] }
    - Use cases: exact token lookups, identifiers, tags.

12) POST /hybrid_recall_with_scores
    - Body: { query: string, terms?: [string], boost=2.0, top_k=5, exact=true, case_sensitive=false, type? }
    - Purpose: Combine embedding similarity with keyword matches; autodetects keywords when `terms` omitted.
    - Returns: { results: [ { payload, score }, ... ] }
    - Use cases: robust recall mixing semantics and terms for precision and recall.

## Graph

13) GET /neighbors
    - Query: coord="x,y,z", link_type?=string, limit?=int
    - Purpose: Graph neighbors from `graph_store`.
    - Returns: { neighbors: [ [ [x,y,z], edge_data ], ... ] }
    - Use cases: related memories traversal, path exploration.

14) POST /link
    - Body: { from_coord: "x,y,z", to_coord: "x,y,z", type="related", weight=1.0 }
    - Purpose: Create a graph edge between memories.
    - Returns: { ok: true }
    - Use cases: explicit associative linking.

15) GET /shortest_path
    - Query: frm="x,y,z", to="x,y,z", link_type?=string
    - Purpose: Weighted shortest path using graph.
    - Returns: { path: [ [x,y,z], ... ] }
    - Use cases: reasoning over associations, recommendation chains.

## Range query

16) GET /range
    - Query: min="x,y,z", max="x,y,z", type?=episodic|semantic
    - Purpose: Axis-aligned coordinate range search.
    - Returns: { coords: [ [x,y,z], ... ] }
    - Use cases: spatial windows, time buckets mapped to axes.

## Metrics and root

17) GET /metrics
    - Purpose: Prometheus metrics for API operations and 404s.
    - Auth: Not in schema.

18) GET /
    - Purpose: Simple message plus link to /metrics.

## Examples

- Store episodic memory:
  curl -X POST http://localhost:9595/store -H 'Content-Type: application/json' -d '{"coord":"1,2,3","payload":{"msg":"hello"},"type":"episodic"}'

- Hybrid recall with default hybrid in core:
  curl -X POST http://localhost:9595/recall -H 'Content-Type: application/json' -d '{"query":"hello", "top_k": 5}'

- Keyword search (case-insensitive substring):
  curl -X POST http://localhost:9595/keyword_search -H 'Content-Type: application/json' -d '{"term":"hello","exact":false,"case_sensitive":false,"top_k":10}'

- Hybrid recall with explicit terms and scores:
  curl -X POST http://localhost:9595/hybrid_recall_with_scores -H 'Content-Type: application/json' -d '{"query":"greeting message","terms":["hello"],"boost":2.5,"top_k":5,"exact":true,"case_sensitive":false}'

- Context recall:
  curl -X POST 'http://localhost:9595/recall_with_context?query=hello&top_k=3' -H 'Content-Type: application/json' -d '{"user":"abc","topic":"onboarding"}'

- Link memories and get neighbors:
  curl -X POST http://localhost:9595/link -H 'Content-Type: application/json' -d '{"from_coord":"1,2,3","to_coord":"4,5,6","type":"related","weight":1.0}'
  curl "http://localhost:9595/neighbors?coord=1,2,3&limit=5"

## Choosing between endpoints

- Need speed and exact hits? Use /keyword_search.
- Need semantics only? /recall with hybrid=false (or set SOMA_HYBRID_RECALL_DEFAULT=0 in core).
- Need robust results? /recall (hybrid default) or /hybrid_recall_with_scores for scoring.
- Need batch: /recall_batch.
- Need context conditioning: /recall_with_context.
- Need graphs: /link, /neighbors, /shortest_path.
- Need coordinates window: /range.

## Error modes

- 401/403 when SOMA_API_TOKEN set and missing/invalid Authorization.
- 429 rate limit when exceeding configured window.
- 422 for validation errors (bad parameters or body).
- 5xx surfaced from backends; /healthz can help diagnose.

---

This guide mirrors the current live API’s OpenAPI (see `/openapi.json`) and the server code in `examples/api.py`.
