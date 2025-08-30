# Performance Tips

- Vector dimension (`memory_enterprise.vector_dim`):
  - Smaller dims (e.g., 256) are faster and use less memory; higher dims (768+) improve recall quality.
- Batch operations:
  - If adding many memories at once, consider batching vector upserts to reduce overhead.
- Qdrant local vs. server:
  - Local on-disk is convenient for development but locks per process and is slower at scale.
  - For concurrent access/high volume, use Qdrant server (Docker/Cloud).
- Embeddings:
  - The default robust fallback is hash-based; for higher quality, configure a transformer model via `SOMA_MODEL_NAME`.
- Decay interval:
  - Tune `pruning_interval_seconds` to balance overhead with responsiveness of field decay.
- Logging and metrics:
  - Disable debug logs in hot paths; scrape Prometheus at reasonable intervals.
