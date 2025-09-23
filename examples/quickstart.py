from somafractalmemory.core import MemoryType
from somafractalmemory.factory import MemoryMode, create_memory_system


def main():
    config = {
        "redis": {"testing": True},
        "qdrant": {"path": "./qdrant.db"},
        "memory_enterprise": {
            "vector_dim": 256,
            "pruning_interval_seconds": 10,
            "decay_thresholds_seconds": [60, 600],
            "decayable_keys_by_level": [["scratch"], ["low_importance"]],
        },
    }

    # Use v2 canonical DEVELOPMENT mode for local/demo usage
    mem = create_memory_system(MemoryMode.DEVELOPMENT, "demo_ns", config=config)

    # Store
    coord1 = (1.0, 2.0, 3.0)
    mem.store_memory(
        coord1, {"task": "write docs", "importance": 2}, memory_type=MemoryType.EPISODIC
    )

    coord2 = (4.0, 5.0, 6.0)
    mem.store_memory(coord2, {"fact": "docs published"}, memory_type=MemoryType.SEMANTIC)

    # Link and search
    mem.link_memories(coord1, coord2, link_type="related")
    matches = mem.recall("documentation", top_k=3)
    print("Top match:", matches[0] if matches else None)
    print("Path:", mem.find_shortest_path(coord1, coord2))

    # Delete
    mem.delete(coord1)
    print("Deleted coord1. Exists?", bool(mem.retrieve(coord1)))


if __name__ == "__main__":
    main()
