#!/usr/bin/env python3
"""Small YAML -> requirements.txt converter that doesn't require PyYAML.
It extracts list items under a top-level `packages:` key.
Usage: python scripts/generate_requirements.py input.yaml output.txt
"""

import re
import sys
from pathlib import Path

if len(sys.argv) != 3:
    print("Usage: generate_requirements.py <input.yaml> <output.txt>")
    sys.exit(2)

inpath = Path(sys.argv[1])
outpath = Path(sys.argv[2])
if not inpath.exists():
    print(f"Input YAML not found: {inpath}")
    sys.exit(3)

lines = []
with inpath.open("r", encoding="utf-8") as f:
    for line in f:
        m = re.match(r"^\s*-\s*(.+)$", line)
        if m:
            lines.append(m.group(1).strip())

if not lines:
    print(f"No packages found in {inpath}; wrote empty requirements file.")
outpath.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Wrote {len(lines)} entries to {outpath}")
