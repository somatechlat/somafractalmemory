"""Generate gRPC Python stubs for proto files into the package.

Usage: python scripts/generate_protos.py

This script requires `grpc_tools` to be installed in the active environment.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTO_DIR = ROOT / "proto"
OUT_DIR = ROOT / "somafractalmemory"


def main() -> int:
    protos = list(PROTO_DIR.glob("*.proto"))
    if not protos:
        print("No proto files found in proto/")
        return 1
    for p in protos:
        cmd = [
            sys.executable,
            "-m",
            "grpc_tools.protoc",
            f"-I{PROTO_DIR}",
            f"--python_out={OUT_DIR}",
            f"--grpc_python_out={OUT_DIR}",
            str(p),
        ]
        print("Running:", " ".join(cmd))
        subprocess.check_call(cmd)
    print("Done generating protos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
