"""SomaFractalMemory CLI - 100% Django ORM.

Command-line interface for memory operations using Django ORM.
"""

import argparse
import json
import os
import sys


def setup_django() -> None:
    """Setup Django before any Django imports."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "somafractalmemory.settings")
    import django

    django.setup()


def parse_coord(text: str) -> tuple[float, ...]:
    """Parse a comma-separated string into a tuple of floats."""
    parts = [p.strip() for p in text.split(",") if p.strip()]
    return tuple(float(p) for p in parts)


def main() -> None:
    """Entry point for the SomaFractalMemory CLI."""
    setup_django()

    from somafractalmemory.services import get_memory_service

    parser = argparse.ArgumentParser(prog="soma", description="SomaFractalMemory CLI (Django ORM)")
    parser.add_argument("--namespace", default="cli_ns")
    parser.add_argument("--tenant", default="default")

    sub = parser.add_subparsers(dest="cmd", required=True)

    # Store command
    p_store = sub.add_parser("store", help="Store a memory")
    p_store.add_argument("--coord", required=True, help="Comma-separated floats, e.g., 1,2,3")
    p_store.add_argument("--payload", required=True, help="JSON object string")
    p_store.add_argument(
        "--type", dest="mem_type", default="episodic", choices=["episodic", "semantic"]
    )

    # Search command
    p_search = sub.add_parser("search", help="Search memories")
    p_search.add_argument("--query", required=True)
    p_search.add_argument("--top-k", dest="top_k", type=int, default=5)
    p_search.add_argument("--type", dest="mem_type", default=None, choices=["episodic", "semantic"])

    # Get command
    p_get = sub.add_parser("get", help="Fetch a memory by coordinate")
    p_get.add_argument("--coord", required=True, help="Comma-separated floats, e.g., 1,2,3")

    # Delete command
    p_delete = sub.add_parser("delete", help="Delete a memory by coordinate")
    p_delete.add_argument("--coord", required=True, help="Comma-separated floats, e.g., 1,2,3")

    # Stats command
    sub.add_parser("stats", help="Show memory stats")

    # Health command
    sub.add_parser("health", help="Check database health")

    args = parser.parse_args()

    # Create service
    service = get_memory_service(namespace=args.namespace)

    if args.cmd == "store":
        coord = parse_coord(args.coord)
        payload = json.loads(args.payload)
        service.store(
            coordinate=coord,
            payload=payload,
            memory_type=args.mem_type,
            tenant=args.tenant,
        )
        print("OK")

    elif args.cmd == "search":
        results = service.search(
            query=args.query,
            top_k=args.top_k,
            memory_type=args.mem_type,
            tenant=args.tenant,
        )
        print(json.dumps(results, indent=2))

    elif args.cmd == "get":
        coord = parse_coord(args.coord)
        record = service.retrieve(coord, tenant=args.tenant)
        if record is None:
            print("Memory not found", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(record, indent=2))

    elif args.cmd == "delete":
        coord = parse_coord(args.coord)
        deleted = service.delete(coord, tenant=args.tenant)
        print(json.dumps({"deleted": deleted}))

    elif args.cmd == "stats":
        stats = service.stats()
        print(json.dumps(stats, indent=2))

    elif args.cmd == "health":
        health = service.health_check()
        print(json.dumps(health, indent=2))
        if not all(health.values()):
            sys.exit(1)


if __name__ == "__main__":
    main()
