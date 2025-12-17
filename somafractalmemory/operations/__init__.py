# somafractalmemory/operations/__init__.py
"""Operations module for SomaFractalMemory.

This module contains extracted operations from the core SomaFractalMemoryEnterprise class,
organized by functional domain for maintainability and VIBE compliance (<500 lines per file).
"""

from .delete import (
    delete_many_op,
    delete_op,
    forget_op,
    remove_vector_entries_op,
)
from .graph_ops import (
    find_shortest_path_op,
    get_linked_memories_op,
    link_memories_op,
    sync_graph_from_memories_op,
)
from .lifecycle import (
    adaptive_importance_norm_op,
    apply_decay_to_all_op,
    consolidate_memories_op,
    decay_memories_op,
    enforce_memory_limit_op,
    reflect_op,
    replay_memories_op,
    run_decay_once_op,
)
from .retrieve import (
    get_all_memories_op,
    get_versions_op,
    retrieve_memories_op,
    retrieve_op,
    save_version_op,
)
from .search import (
    find_by_coordinate_range_op,
    find_hybrid_by_type_op,
    find_hybrid_with_context_op,
    hybrid_recall_op,
    hybrid_recall_with_scores_op,
    keyword_search_op,
    recall_op,
)
from .stats import (
    audit_log_op,
    get_important_op,
    get_recent_op,
    health_check_op,
    memory_stats_op,
    summarize_memories_op,
)
from .store import (
    export_memories_op,
    import_memories_op,
    store_memories_bulk_op,
    store_memory_op,
    store_op,
    store_vector_only_op,
)

__all__ = [
    "store_memory_op",
    "store_op",
    "store_memories_bulk_op",
    "store_vector_only_op",
    "import_memories_op",
    "export_memories_op",
    "retrieve_op",
    "retrieve_memories_op",
    "get_all_memories_op",
    "get_versions_op",
    "save_version_op",
    "recall_op",
    "hybrid_recall_op",
    "hybrid_recall_with_scores_op",
    "keyword_search_op",
    "find_hybrid_with_context_op",
    "find_hybrid_by_type_op",
    "find_by_coordinate_range_op",
    "delete_op",
    "forget_op",
    "delete_many_op",
    "remove_vector_entries_op",
    "link_memories_op",
    "get_linked_memories_op",
    "find_shortest_path_op",
    "sync_graph_from_memories_op",
    "memory_stats_op",
    "summarize_memories_op",
    "get_recent_op",
    "get_important_op",
    "health_check_op",
    "audit_log_op",
    "decay_memories_op",
    "apply_decay_to_all_op",
    "run_decay_once_op",
    "consolidate_memories_op",
    "replay_memories_op",
    "reflect_op",
    "enforce_memory_limit_op",
    "adaptive_importance_norm_op",
]
