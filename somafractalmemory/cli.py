import argparse
import argparse as _argparse
import asyncio
import json
import os
from typing import Any

from common.utils.logger import configure_logging

from .core import MemoryType
from .factory import MemoryMode, create_memory_system


def parse_coord(text: str) -> tuple[float, ...]:
    """
    Parse a comma-separated string into a tuple of floats.

    Parameters
    ----------
    text : str
        Comma-separated coordinate string (e.g., '1,2,3').

    Returns
    -------
    Tuple[float, ...]
        Tuple of floats representing the coordinate.
    """
    parts = [p.strip() for p in text.split(",") if p.strip()]
    return tuple(float(p) for p in parts)


def load_config_json(path: str | None) -> dict[str, Any]:
    """
    Load a JSON configuration file from the given path.

    Parameters
    ----------
    path : Optional[str]
        Path to the JSON config file.

    Returns
    -------
    Dict[str, Any]
        Parsed configuration dictionary.
    """
    if not path:
        return {}
    with open(path) as f:
        return json.load(f)


def get_mode(mode_str: str) -> MemoryMode:
    """
    Convert a mode string to a MemoryMode enum value.

    Parameters
    ----------
    mode_str : str
        Mode string ('on_demand', 'local_agent', 'enterprise').

    Returns
    -------
    MemoryMode
        Corresponding MemoryMode enum value.
    """
    # Accept both legacy names and the new v2 canonical names. Map any
    # accepted string (case-insensitive) to the canonical MemoryMode enum.
    # v2 canonical names only. Legacy mode strings were removed in v2.
    key = (mode_str or "").strip().lower() or MemoryMode.EVENTED_ENTERPRISE.value
    if key != MemoryMode.EVENTED_ENTERPRISE.value:
        raise ValueError(
            f"Unsupported mode: {mode_str}. Only '{MemoryMode.EVENTED_ENTERPRISE.value}' is supported."
        )
    return MemoryMode.EVENTED_ENTERPRISE


async def _run_command_async(args: _argparse.Namespace) -> None:
    # Run the synchronous memory system functions in a thread to avoid blocking
    # the async loop while keeping compatibility with current store/recall APIs.
    # Ensure deterministic, quiet embeddings in CLI flows
    os.environ.setdefault("SOMA_FORCE_HASH_EMBEDDINGS", "1")
    config = load_config_json(args.config_json)
    # configure logging for CLI
    configure_logging("smf-cli")
    mem = await asyncio.to_thread(create_memory_system, get_mode(args.mode), args.namespace, config)

    if args.cmd == "store":
        coord = parse_coord(args.coord)
        payload = json.loads(args.payload)
        mtype = MemoryType.SEMANTIC if args.mem_type == "semantic" else MemoryType.EPISODIC
        await asyncio.to_thread(mem.store_memory, coord, payload, memory_type=mtype)
        print("OK")
    elif args.cmd == "search":
        filters = None
        if args.filters:
            parsed = json.loads(args.filters)
            if parsed is not None and not isinstance(parsed, dict):
                raise SystemExit("--filters must be a JSON object")
            filters = parsed
        memory_type = None
        if getattr(args, "mem_type", None):
            memory_type = (
                MemoryType.SEMANTIC if args.mem_type == "semantic" else MemoryType.EPISODIC
            )
        res = await asyncio.to_thread(
            mem.find_hybrid_by_type, args.query, args.top_k, memory_type, filters
        )
        print(json.dumps(res))
    elif args.cmd == "recall":
        memory_type = None
        if getattr(args, "mem_type", None):
            memory_type = (
                MemoryType.SEMANTIC if args.mem_type == "semantic" else MemoryType.EPISODIC
            )
        res = await asyncio.to_thread(
            mem.recall, args.query, top_k=args.top_k, memory_type=memory_type
        )
        print(json.dumps(res))
    elif args.cmd == "get":
        coord = parse_coord(args.coord)
        record = await asyncio.to_thread(mem.retrieve, coord)
        if record is None:
            raise SystemExit("Memory not found")
        print(json.dumps(record))
    elif args.cmd == "delete":
        coord = parse_coord(args.coord)
        deleted = await asyncio.to_thread(mem.delete, coord)
        print(json.dumps({"deleted": bool(deleted)}))
    elif args.cmd == "stats":
        print(json.dumps(await asyncio.to_thread(mem.memory_stats), indent=2))
    elif args.cmd == "export-memories":
        n = await asyncio.to_thread(mem.export_memories, args.path)
        print(json.dumps({"exported": n}))
    elif args.cmd == "import-memories":
        n = await asyncio.to_thread(mem.import_memories, args.path, replace=args.replace)
        print(json.dumps({"imported": n}))
    elif args.cmd == "delete-many":
        coords = [parse_coord(s) for s in args.coords.split(";") if s.strip()]
        n = await asyncio.to_thread(mem.delete_many, coords)
        print(json.dumps({"deleted": n}))


def main() -> None:
    """Entry point for the SomaFractalMemory CLI that dispatches to an async runner."""
    parser = argparse.ArgumentParser(prog="soma", description="SomaFractalMemory CLI")
    parser.add_argument(
        "--mode",
        default=MemoryMode.EVENTED_ENTERPRISE.value,
        choices=[MemoryMode.EVENTED_ENTERPRISE.value],
        help="Memory system mode (evented_enterprise only)",
    )
    parser.add_argument("--namespace", default="cli_ns")
    parser.add_argument(
        "--config-json", dest="config_json", default=None, help="Path to JSON config file"
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_store = sub.add_parser("store", help="Store a memory")
    p_store.add_argument("--coord", required=True, help="Comma-separated floats, e.g., 1,2,3")
    p_store.add_argument("--payload", required=True, help="JSON object string")
    p_store.add_argument(
        "--type", dest="mem_type", default="episodic", choices=["episodic", "semantic"]
    )

    p_search = sub.add_parser("search", help="Hybrid search across stored memories")
    p_search.add_argument("--query", required=True)
    p_search.add_argument("--top-k", dest="top_k", type=int, default=5)
    p_search.add_argument(
        "--filters",
        dest="filters",
        default=None,
        help="Optional JSON object to constrain search results",
    )
    p_search.add_argument("--type", dest="mem_type", default=None, choices=["episodic", "semantic"])

    p_recall = sub.add_parser("recall", help="Recall memories using the legacy recall signal")
    p_recall.add_argument("--query", required=True)
    p_recall.add_argument("--top-k", dest="top_k", type=int, default=5)
    p_recall.add_argument("--type", dest="mem_type", default=None, choices=["episodic", "semantic"])

    p_get = sub.add_parser("get", help="Fetch a memory by coordinate")
    p_get.add_argument("--coord", required=True, help="Comma-separated floats, e.g., 1,2,3")

    p_delete = sub.add_parser("delete", help="Delete a memory by coordinate")
    p_delete.add_argument("--coord", required=True, help="Comma-separated floats, e.g., 1,2,3")

    sub.add_parser("stats", help="Show memory stats")

    p_exp_mem = sub.add_parser("export-memories", help="Export memories to JSONL")
    p_exp_mem.add_argument("--path", required=True)

    p_imp_mem = sub.add_parser("import-memories", help="Import memories from JSONL")
    p_imp_mem.add_argument("--path", required=True)
    p_imp_mem.add_argument("--replace", action="store_true")

    p_del_many = sub.add_parser("delete-many", help="Delete multiple coordinates")
    p_del_many.add_argument(
        "--coords", required=True, help='Semicolon-separated coords, e.g., "1,2,3;4,5,6"'
    )

    args = parser.parse_args()
    # Run the async command runner
    asyncio.run(_run_command_async(args))


if __name__ == "__main__":
    main()
