# Architecture

`somafractalmemory` is a distributed, secure, and observable memory system for AI agents.

- **Storage:** Redis (key-value), Qdrant (vector), FAISS (in-memory)
- **Embeddings:** Hugging Face transformers
- **Security:** Optional Fernet encryption
- **Observability:** Prometheus, structlog
- **Anomaly Detection:** IsolationForest
- **Hybrid Search:** Semantic + spatial with RRF
- **Maintenance:** Decay, pruning, background thread

See `core.py` for details.
