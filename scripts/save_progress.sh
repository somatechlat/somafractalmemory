#!/usr/bin/env bash
set -euo pipefail

OUT=docs/CANONICAL_PROGRESS.md
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

cat >> "$OUT" <<-EOF

### Snapshot: $TS

- pwd: $(pwd)
- git branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)
- git status summary:

	author: $(git config user.name 2>/dev/null || echo "<no user>")
	commit: $(git rev-parse --short HEAD 2>/dev/null || echo "<no commit>")

- Docker images (somafractalmemory):
$(docker images --format '  - {{.Repository}}:{{.Tag}} {{.Size}}' | grep somafractalmemory || true)

- Running containers (related to soma):
$(docker ps --filter "ancestor=somafractalmemory:minimal" --format '  - {{.ID}} {{.Image}} {{.Status}} {{.Names}}' || true)

- Top ignored/untracked large files (du):
$(git ls-files -z --others --exclude-standard --ignored | xargs -0 du -sh 2>/dev/null | sort -hr | head -n 20 || true)

- Todo list (summary):
$(python - <<PY
from pathlib import Path
import json
# read the todo list produced earlier from the manage_todo_list contents
# fallback: print a static hint
print('  - See TODO list in the project root for current tasks')
PY)

---
EOF

echo "Appended snapshot to $OUT"
