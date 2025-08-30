"""
Seed several memories and run a couple of recalls.

Run:
  python examples/seed_and_query.py
"""

from somafractalmemory.factory import create_memory_system, MemoryMode
from somafractalmemory.core import MemoryType


def main():
    mem = create_memory_system(
        MemoryMode.LOCAL_AGENT,
        "seed_ns",
        config={"redis": {"testing": True}, "qdrant": {"path": "./qdrant.db"}},
    )

    coords = [(0.0, 0.0, 0.1), (0.0, 0.0, 0.2), (0.0, 0.0, 0.3)]
    payloads = [
        {"task": "write docs", "importance": 2},
        {"task": "review PR", "importance": 1},
        {"fact": "docs published"},
    ]
    types = [MemoryType.EPISODIC, MemoryType.EPISODIC, MemoryType.SEMANTIC]

    for c, p, t in zip(coords, payloads, types):
        mem.store_memory(c, p, memory_type=t)

    print("Recall 'docs':")
    print(mem.recall("docs", top_k=3))


if __name__ == "__main__":
    main()

