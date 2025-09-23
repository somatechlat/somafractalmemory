# API Documentation# Public API Reference



## `SomaFractalMemoryEnterprise`This document is generated from the source code (`core.py` and `factory.py`). It lists the public classes, enums, and functions that constitute the **SomaFractalMemory** API.



```python---

class SomaFractalMemoryEnterprise:

    def __init__(## Enums

        self,

        namespace: str,### `MemoryType`

        kv_store: IKeyValueStore,```python

        vector_store: IVectorStore,class MemoryType(Enum):

        graph_store: IGraphStore,    EPISODIC = "episodic"

        prediction_provider: IPredictionProvider,    SEMANTIC = "semantic"

        model_name: str = "microsoft/codebert-base",```

        vector_dim: int = 768,*Used to indicate whether a stored memory is episodic or semantic.*

        encryption_key: Optional[bytes] = None,

        config_file: str = "config.yaml",### `MemoryMode`

        max_memory_size: int = 100000,```python

        pruning_interval_seconds: int = 600,class MemoryMode(Enum):

        decay_thresholds_seconds: Optional[List[int]] = None,    DEVELOPMENT = "development"

        decayable_keys_by_level: Optional[List[List[str]]] = None,    TEST = "test"

        decay_enabled: bool = True,    EVENTED_ENTERPRISE = "evented_enterprise"

        reconcile_enabled: bool = True,    CLOUD_MANAGED = "cloud_managed"

    ) -> None:```

        ...*Selects the backend configuration for the memory system.*

```

---

### Key Public Methods

## Exceptions

- `store_memory(coordinate, value, memory_type=MemoryType.EPISODIC)` – Store a memory, optionally enrich with prediction, enforce limits, and publish event.

- `retrieve(coordinate)` – Retrieve a memory with optional decryption and access‑count tracking.### `SomaFractalMemoryError`

- `delete(coordinate)` – Delete a memory from all backends.```python

- `recall(query, context=None, top_k=5, memory_type=None)` – Hybrid recall using vector similarity and optional context.class SomaFractalMemoryError(Exception):

- `reflect(n=5, memory_type=MemoryType.EPISODIC)` – Replay recent memories for reflection.    pass

- `consolidate_memories(window_seconds=3600)` – Summarise recent episodic memories into a semantic summary.```

- `health_check()` – Returns health status of all backends.*Base exception for all memory‑system‑related errors.*

- `audit_log(action, coordinate, user="system")` – Append an audit entry to `audit_log.jsonl`.

- `share_memory_with(other_agent, filter_fn=None)` – Share memories with another memory instance.---

- Various utility methods for importance, versioning, decay, bulk import/export, etc.

## Core Classes

## `create_memory_system`

### `SomaFractalMemoryEnterprise`

Factory function to build a configured `SomaFractalMemoryEnterprise` instance.The main class that implements the memory system.  Key public methods:



```python| Method | Signature | Description |

def create_memory_system(|--------|-----------|-------------|

    mode: MemoryMode,| `find_shortest_path` | `def find_shortest_path(self, from_coord: Tuple[float, ...], to_coord: Tuple[float, ...], link_type: Optional[str] = None) -> List[Any]` | Delegates to the graph store to compute the shortest path between two coordinates. |

    namespace: str,| `report_outcome` | `def report_outcome(self, coordinate: Tuple[float, ...], outcome: Any) -> Dict[str, Any]` | Stores the actual outcome of a memory, updates prediction feedback, and creates a corrective semantic memory if needed. |

    config: Optional[Dict[str, Any]] = None,| `delete` | `def delete(self, coordinate: Tuple[float, ...]) -> bool` | Removes a memory from KV store, vector store, and graph store. |

) -> SomaFractalMemoryEnterprise:| `store` | `def store(self, coordinate: Tuple[float, ...], value: dict)` | Low‑level store that writes the payload to KV, adds metadata, and upserts the embedding into the vector store (with WAL fallback). |

    ...| `acquire_lock` / `with_lock` | `def acquire_lock(self, name: str, timeout: int = 10) -> ContextManager`<br>`def with_lock(self, name: str, func, *args, **kwargs)` | Helper for distributed locking via the KV store. |

```| `iter_memories` | `def iter_memories(self, pattern: Optional[str] = None)` | Yields memory payloads, falling back to KV store if the vector store is unavailable. |

| `health_check` | `def health_check(self) -> Dict[str, bool]` | Returns health status of all backend components. |

### Supported Modes (`MemoryMode`)| `set_importance` | `def set_importance(self, coordinate: Tuple[float, ...], importance: int = 1)` | Updates the `importance` field of a memory and syncs it to the vector store. |

| `retrieve` | `def retrieve(self, coordinate: Tuple[float, ...]) -> Optional[Dict[str, Any]]` | Retrieves a memory, updates access metadata, increments `access_count`, and decrypts sensitive fields if encryption is enabled. |

- `MemoryMode.DEVELOPMENT` – Local development; optional Redis cache, PostgreSQL if configured, Qdrant or in‑memory vector store, Ollama prediction.| `store_memories_bulk` | `def store_memories_bulk(self, items: List[Tuple[Tuple[float, ...], Dict[str, Any], MemoryType]])` | Bulk‑store helper that iterates over `store_memory`. |

- `MemoryMode.TEST` – Fully in‑memory stores, no eventing.| `export_memories` | `def export_memories(self, path: str) -> int` | Dumps all memories to a newline‑delimited JSON file. |

- `MemoryMode.EVENTED_ENTERPRISE` / `MemoryMode.CLOUD_MANAGED` – Production configuration with Redis, Qdrant, optional external prediction provider, eventing enabled.| `store_memory` | `def store_memory(self, coordinate: Tuple[float, ...] | List[float], value: Dict[str, Any], memory_type: MemoryType = MemoryType.EPISODIC)` | High‑level API used by callers – adds metadata, runs prediction enrichment, writes to KV, vector, and graph stores, and enforces memory limits. |

| `retrieve_memories` | `def retrieve_memories(self, memory_type: Optional[MemoryType] = None) -> List[Dict[str, Any]]` | Returns all memories, optionally filtered by type. |

The factory returns an instance with an `eventing_enabled` attribute controlling Kafka event publishing.| `find_hybrid_by_type` | `def find_hybrid_by_type(self, query: str, top_k: int = 5, memory_type: Optional[MemoryType] = None, filters: Optional[Dict[str, Any]] = None, **kwargs) -> List[Dict[str, Any]]` | Vector‑search wrapper that returns payloads matching a query. |

| `find_by_coordinate_range` | `def find_by_coordinate_range(self, min_coord: Tuple[float, ...], max_coord: Tuple[float, ...], memory_type: Optional[MemoryType] = None) -> List[Dict[str, Any]]` | Returns memories whose coordinates lie inside the supplied bounding box. |

---| `delete_many` | `def delete_many(self, coordinates: List[Tuple[float, ...]]) -> int` | Batch delete helper. |

| `import_memories` | `def import_memories(self, path: str, replace: bool = False) -> int` | Reads newline‑delimited JSON and stores each memory. |

For full class and method signatures, refer to the source files in `somafractalmemory/core.py` and `somafractalmemory/factory.py`.| `run_decay_once` / `_decay_memories` / `_apply_decay_to_all` | Various decay helpers that prune fields based on age thresholds. |

| `save_version` / `get_versions` | Version‑snapshot helpers for a given coordinate. |
| `audit_log` | Writes a JSONL audit entry for actions. |
| `summarize_memories`, `get_recent`, `get_important`, `memory_stats` | Convenience helpers for UI/CLI. |
| Hook system (`set_hook`, `_call_hook`) | Allows registration of callbacks for events like `before_store`, `after_store`, etc. |
| Graph helpers (`link_memories`, `get_linked_memories`) | Manipulate semantic links between memories. |

---

## Helper Classes (implementation details)

### `PostgresRedisHybridStore`
Implements `IKeyValueStore` by combining a canonical PostgreSQL store with an optional Redis cache.  Public methods:
- `set`, `get`, `delete`
- `scan_iter`, `hgetall`, `hset`
- `lock`, `health_check`

### `MemoryMode` (see Enums)

---

## Factory Function

### `create_memory_system`
```python
def create_memory_system(
    mode: MemoryMode,
    namespace: str,
    config: Optional[Dict[str, Any]] = None,
) -> SomaFractalMemoryEnterprise:
    ...
```
Creates a fully‑configured `SomaFractalMemoryEnterprise` instance based on the selected `MemoryMode`:
- **DEVELOPMENT** – PostgreSQL KV (canonical) with optional Redis cache, Qdrant or in‑memory vector store, and an `OllamaPredictionProvider` (if transformer model loads).
- **TEST** – In‑memory KV (FakeRedis) and in‑memory vector store, no prediction enrichment.
- **EVENTED_ENTERPRISE / CLOUD_MANAGED** – Production mode: PostgreSQL KV, Qdrant vector store, optional Redis cache, and a placeholder for future event‑driven pipelines.

All configuration values are taken from the supplied `config` dict (or Dynaconf `config.yaml`) and environment variables prefixed with `SOMA_`.

---

## Usage Example (from README)
```python
from somafractalmemory.factory import create_memory_system, MemoryMode
from somafractalmemory.core import MemoryType

mem = create_memory_system(MemoryMode.DEVELOPMENT, "demo", config={})
coord = (1.0, 2.0, 3.0)
mem.store_memory(coord, {"task": "write docs", "importance": 2}, MemoryType.EPISODIC)
```

---

*This API reference is the single source of truth for developers. All documentation elsewhere should point to these signatures.*
