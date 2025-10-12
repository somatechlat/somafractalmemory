import argparse
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
    mapping = {
        "development": MemoryMode.DEVELOPMENT,
        "test": MemoryMode.TEST,
        "evented_enterprise": MemoryMode.EVENTED_ENTERPRISE,
        "cloud_managed": MemoryMode.CLOUD_MANAGED,
    }

    key = (mode_str or "").strip().lower()
    try:
        return mapping[key]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported mode: {mode_str}. Supported modes: {', '.join(sorted(mapping.keys()))}"
        ) from exc


async def _run_command_async(args) -> None:
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
    elif args.cmd == "recall":
        mtype = None
        if args.mem_type:
            mtype = MemoryType.SEMANTIC if args.mem_type == "semantic" else MemoryType.EPISODIC
        res = await asyncio.to_thread(mem.recall, args.query, top_k=args.top_k, memory_type=mtype)
        # Ensure pure JSON array with payloads only
        try:
            out = [r if isinstance(r, dict) else r for r in res]
        except Exception:
            out = []
        print(json.dumps(out))
    elif args.cmd == "link":
        fc = parse_coord(args.from_coord)
        tc = parse_coord(args.to_coord)
        await asyncio.to_thread(
            mem.link_memories, fc, tc, link_type=args.link_type, weight=args.weight
        )
        print("OK")
    elif args.cmd == "path":
        fc = parse_coord(args.from_coord)
        tc = parse_coord(args.to_coord)
        path = await asyncio.to_thread(mem.find_shortest_path, fc, tc, link_type=args.link_type)
        print(json.dumps([list(c) for c in path]))
    elif args.cmd == "neighbors":
        c = parse_coord(args.coord)
        pairs = await asyncio.to_thread(
            mem.graph_store.get_neighbors, c, link_type=args.link_type, limit=args.limit
        )
        coords = [list(co) for co, _ in pairs]
        print(json.dumps(coords))
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
    elif args.cmd == "store-bulk":
        with open(args.file, encoding="utf-8") as fh:
            raw = json.load(fh)

        # Expect list of {coord: "x,y,z", payload: {...}, type: "episodic|semantic"}
        def _to_tuple(item):
            c = parse_coord(item.get("coord", ""))
            p = item.get("payload", {})
            t = MemoryType.SEMANTIC if item.get("type") == "semantic" else MemoryType.EPISODIC
            return (c, p, t)

        tuples = [_to_tuple(it) for it in raw]
        await asyncio.to_thread(mem.store_memories_bulk, tuples)
        print(json.dumps({"stored": len(tuples)}))
    elif args.cmd == "range":
        minc = parse_coord(args.min_coord)
        maxc = parse_coord(args.max_coord)
        mtype = None
        if args.mem_type:
            mtype = MemoryType.SEMANTIC if args.mem_type == "semantic" else MemoryType.EPISODIC
        res = await asyncio.to_thread(mem.find_by_coordinate_range, minc, maxc, memory_type=mtype)
        coords = [m.get("coordinate") for m in res if isinstance(m, dict) and m.get("coordinate")]
        print(json.dumps(coords))


def main() -> None:
    """Entry point for the SomaFractalMemory CLI that dispatches to an async runner."""
    parser = argparse.ArgumentParser(prog="soma", description="SomaFractalMemory CLI")
    parser.add_argument(
        "--mode",
        default="development",
        choices=["development", "test", "evented_enterprise", "cloud_managed"],
        help="Memory system mode (v2 canonical names)",
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

    p_recall = sub.add_parser("recall", help="Recall memories")
    p_recall.add_argument("--query", required=True)
    p_recall.add_argument("--top-k", dest="top_k", type=int, default=5)
    p_recall.add_argument("--type", dest="mem_type", default=None, choices=["episodic", "semantic"])

    p_link = sub.add_parser("link", help="Link two memories")
    p_link.add_argument("--from", dest="from_coord", required=True)
    p_link.add_argument("--to", dest="to_coord", required=True)
    p_link.add_argument("--type", dest="link_type", default="related")
    p_link.add_argument("--weight", dest="weight", type=float, default=1.0)

    p_path = sub.add_parser("path", help="Find shortest path between coordinates")
    p_path.add_argument("--from", dest="from_coord", required=True)
    p_path.add_argument("--to", dest="to_coord", required=True)
    p_path.add_argument("--type", dest="link_type", default=None)

    p_neighbors = sub.add_parser("neighbors", help="List neighbors of a coordinate")
    p_neighbors.add_argument("--coord", required=True)
    p_neighbors.add_argument("--type", dest="link_type", default=None)
    p_neighbors.add_argument("--limit", dest="limit", type=int, default=None)

    sub.add_parser("stats", help="Show memory stats")

    p_export = sub.add_parser("export-graph", help="Export semantic graph to GraphML")
    p_export.add_argument("--path", required=True)

    p_import_graph = sub.add_parser("import-graph", help="Import semantic graph from GraphML")
    p_import_graph.add_argument("--path", required=True)

    p_exp_mem = sub.add_parser("export-memories", help="Export memories to JSONL")
    p_exp_mem.add_argument("--path", required=True)

    p_imp_mem = sub.add_parser("import-memories", help="Import memories from JSONL")
    p_imp_mem.add_argument("--path", required=True)
    p_imp_mem.add_argument("--replace", action="store_true")

    p_del_many = sub.add_parser("delete-many", help="Delete multiple coordinates")
    p_del_many.add_argument(
        "--coords", required=True, help='Semicolon-separated coords, e.g., "1,2,3;4,5,6"'
    )

    p_store_bulk = sub.add_parser("store-bulk", help="Store memories from JSON file")
    p_store_bulk.add_argument(
        "--file", required=True, help="Path to JSON array of items {coord, payload, type}"
    )

    p_range = sub.add_parser("range", help="Find memories within a coordinate bounding box")
    p_range.add_argument(
        "--min", dest="min_coord", required=True, help="Comma-separated min coord, e.g., 0,0,0"
    )
    p_range.add_argument(
        "--max", dest="max_coord", required=True, help="Comma-separated max coord, e.g., 2,2,2"
    )
    p_range.add_argument("--type", dest="mem_type", default=None, choices=["episodic", "semantic"])

    args = parser.parse_args()
    # Run the async command runner
    asyncio.run(_run_command_async(args))


if __name__ == "__main__":
    main()
