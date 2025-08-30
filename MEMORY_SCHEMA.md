# Memory Payload Schema (Guidance)

A memory is stored as a Python dict and persisted in KV, vector payloads, and graph node attributes. Common fields:

- coordinate: list[number]
  - The spatial coordinate; always included in stored payloads.
- memory_type: string
  - "episodic" or "semantic".
- timestamp: number
  - Unix epoch seconds for episodic memories; added if missing.
- importance: number (optional)
  - Higher means more important; used in pruning and sorting.
- links: array (optional)
  - Items: { to: tuple|list, type: string, timestamp: number }
- Arbitrary user fields
  - e.g., task, fact, meta, etc.

Notes:
- Coordinates passed in APIs can be tuples; stored payloads contain `coordinate` as a list for JSON compatibility.
- Sensitive fields such as `task` or `code` may be encrypted if an encryption key is configured and cryptography is available.
- Vector payload mirrors the stored payload; updates like `importance` are synced to vector store.
