import argparse
import json
import logging
import os
from typing import Any

from .core import MemoryType
from .factory import MemoryMode, create_memory_system


def parse_coord(text: str) -> tuple[float, ...]:
    parts = [p.strip() for p in text.split(",") if p.strip()]
    return tuple(float(p) for p in parts)


def load_config_json(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    with open(path) as f:
        return json.load(f)


def get_mode(mode_str: str) -> MemoryMode:
    mapping = {
        "on_demand": MemoryMode.ON_DEMAND,
        "local_agent": MemoryMode.LOCAL_AGENT,
        "enterprise": MemoryMode.ENTERPRISE,
    }
    return mapping[mode_str]


def main() -> None:
    # Ensure logs don't pollute JSON outputs
    logging.basicConfig(level=logging.WARNING)
    os.environ.setdefault("SOMA_SUPPRESS_STDOUT_LOGS", "1")
    parser = argparse.ArgumentParser(prog="soma", description="SomaFractalMemory CLI")
    parser.add_argument(
        "--mode", default="local_agent", choices=["on_demand", "local_agent", "enterprise"]
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

    sub.add_parser("analyze", help="Run analysis on the memory system")

    args = parser.parse_args()
    config = load_config_json(args.config_json)
    mem = create_memory_system(get_mode(args.mode), args.namespace, config=config)

    if args.cmd == "store":
        coord = parse_coord(args.coord)
        payload = json.loads(args.payload)
        mtype = MemoryType.SEMANTIC if args.mem_type == "semantic" else MemoryType.EPISODIC
        mem.store_memory(coord, payload, memory_type=mtype)
        print("OK")
    elif args.cmd == "recall":
        mtype = None
        if args.mem_type:
            mtype = MemoryType.SEMANTIC if args.mem_type == "semantic" else MemoryType.EPISODIC
        res = mem.recall(args.query, top_k=args.top_k, memory_type=mtype)
        print(json.dumps(res, indent=2))
    elif args.cmd == "link":
        fc = parse_coord(args.from_coord)
        tc = parse_coord(args.to_coord)
        mem.link_memories(fc, tc, link_type=args.link_type, weight=args.weight)
        print("OK")
    elif args.cmd == "path":
        fc = parse_coord(args.from_coord)
        tc = parse_coord(args.to_coord)
        path = mem.find_shortest_path(fc, tc, link_type=args.link_type)
        print(json.dumps([list(c) for c in path]))
    elif args.cmd == "neighbors":
        c = parse_coord(args.coord)
        pairs = mem.graph_store.get_neighbors(c, link_type=args.link_type, limit=args.limit)
        coords_out = [list(co) for co, _ in pairs]
        print(json.dumps(coords_out))
    elif args.cmd == "stats":
        print(json.dumps(mem.memory_stats(), indent=2))
    elif args.cmd == "export-graph":
        mem.export_graph(args.path)
        print("OK")
    elif args.cmd == "import-graph":
        mem.import_graph(args.path)
        print("OK")
    elif args.cmd == "export-memories":
        n = mem.export_memories(args.path)
        print(json.dumps({"exported": n}))
    elif args.cmd == "import-memories":
        n = mem.import_memories(args.path, replace=args.replace)
        print(json.dumps({"imported": n}))
    elif args.cmd == "delete-many":
        coords: list[tuple[float, ...]] = []
        for part in args.coords.split(";"):
            part = part.strip()
            if not part:
                continue
            coords.append(parse_coord(part))
        n = mem.delete_many(coords)
        print(json.dumps({"deleted": n}))
    elif args.cmd == "store-bulk":
        import json as _json

        with open(args.file, encoding="utf-8") as f:
            items_raw = _json.load(f)
        items = []
        for it in items_raw:
            coord = parse_coord(it["coord"])
            payload = it["payload"]
            tstr = it.get("type", "episodic")
            mtype = MemoryType.SEMANTIC if tstr == "semantic" else MemoryType.EPISODIC
            items.append((coord, payload, mtype))
        mem.store_memories_bulk(items)
        print(_json.dumps({"stored": len(items)}))
    elif args.cmd == "range":
        mi = parse_coord(args.min_coord)
        ma = parse_coord(args.max_coord)
        mtype = None
        if args.mem_type:
            mtype = MemoryType.SEMANTIC if args.mem_type == "semantic" else MemoryType.EPISODIC
        res = mem.find_by_coordinate_range(mi, ma, memory_type=mtype)
        coords_out2 = [m.get("coordinate") for m in res if m.get("coordinate")]
        print(json.dumps(coords_out2))
    elif args.cmd == "analyze":
        dimension = mem.calculate_fractal_dimension()
        print(json.dumps({"fractal_dimension": dimension}, indent=2))


if __name__ == "__main__":
    main()
