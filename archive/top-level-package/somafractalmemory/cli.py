import argparse
import json
from typing import Any, Dict, Optional, Tuple

from .factory import MemoryMode, create_memory_system


def parse_coord(text: str) -> Tuple[float, ...]:
    parts = [p.strip() for p in text.split(",") if p.strip()]
    return tuple(float(p) for p in parts)


def load_config_json(path: Optional[str]) -> Dict[str, Any]:
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
    parser = argparse.ArgumentParser(prog="soma", description="SomaFractalMemory CLI")
    parser.add_argument(
        "--mode", default="local_agent", choices=["on_demand", "local_agent", "enterprise"]
    )
    parser.add_argument("--namespace", default="cli_ns")
    parser.add_argument(
        "--config-json", dest="config_json", default=None, help="Path to JSON config file"
    )

    _sub = parser.add_subparsers(dest="cmd", required=True)
    # ...existing commands...

    args = parser.parse_args()
    config = load_config_json(args.config_json)
    _mem = create_memory_system(get_mode(args.mode), args.namespace, config=config)

    # The rest of CLI behavior is preserved in the archive copy.
