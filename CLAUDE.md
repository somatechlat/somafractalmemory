# somafractalmemory — agent entry rules

| Field | Value |
|---|---|
| Primary standard | Shared triad rules: `../somaAgent01/docs/standards/SOMA-STD-TRIAD-001.md` (same stack, same rules) |
| T-1 | Only SomaBrain writes SFM. The agent never holds an SFM client. |

## Stack lock

Milvus vectors · Postgres · bearer auth · no Qdrant · no ghost settings (implement or delete) · degraded recall must flag, never silent `[]`.

## Local project agent (`.mimocode/agent/`)

| Agent | Use for |
|---|---|
| `sfm-memory-engineer` | LTM CRUD, graph, embeddings durability, k_hop/belief/importance honesty |

## Known defect classes (B17–B22, B29)

Re-verify against code before claiming fixed. Cite file:line.
