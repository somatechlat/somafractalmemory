# Canonical Progress Log — SomaFractalMemory

This file is the single canonical progress snapshot for ongoing work on this repository. It is updated by `scripts/save_progress.sh` which appends a timestamped entry containing key diagnostics and the current todo/checklist state. Use this file to quickly get up-to-speed when resuming work.

Important policy notes
- Do not change any mathematical code or algorithms unless there is a fully-reviewed, tested, and documented rationale. Any change to math must include tests and a regression verification plan.
- No destructive operations (deletions, archive moves) are performed without explicit user approval. All large-file cleanups are proposed and only executed after confirmation.

How snapshots are written
- Run `scripts/save_progress.sh` to append a snapshot.
- You can install a cron job or similar scheduler to run the script hourly; instructions are provided below.

Initial snapshot (created automatically):

<!-- SNAPSHOTS -->


---

## How to use

- To append the current snapshot manually (recommended before making changes):

```bash
chmod +x scripts/save_progress.sh
./scripts/save_progress.sh
```

- To schedule hourly on macOS (example using launchd) or Linux (cron), add a scheduler that runs the script and writes to this file. See `docs/CI.md` for cron examples.

---


### Snapshot: 2025-09-19T17:38:42Z

- pwd: /Users/macbookpro201916i964gb1tb/Documents/GitHub/somafractalmemory
- git branch: master
- git status summary:

author: somaplanet
commit: 8361057

- Docker images (somafractalmemory):
- somafractalmemory:minimal 1.57GB
- somafractalmemory:prod 234MB

- Running containers (related to soma):
- b3e4ac2f6930 somafractalmemory:minimal Up 6 minutes (unhealthy) somafractalmemory_min_test

- Top ignored/untracked large files (du):
 35M	archive/.venv/lib/python3.10/site-packages/grpc/_cython/cygrpc.cpython-310-darwin.so
 35M	.venv/lib/python3.10/site-packages/grpc/_cython/cygrpc.cpython-310-darwin.so
 33M	archive/.venv/lib/python3.13/site-packages/7ae574991b77ef47acad__mypyc.cpython-313-darwin.so
 33M	.venv/lib/python3.13/site-packages/7ae574991b77ef47acad__mypyc.cpython-313-darwin.so
 32M	archive/.venv/bin/ruff
 32M	.venv/bin/ruff
 21M	archive/.venv/lib/python3.10/site-packages/cryptography/hazmat/bindings/_rust.abi3.so
 21M	.venv/lib/python3.10/site-packages/cryptography/hazmat/bindings/_rust.abi3.so
 13M	archive/.venv/lib/python3.10/site-packages/faiss/_swigfaiss_avx2.cpython-310-darwin.so
 13M	.venv/lib/python3.10/site-packages/faiss/_swigfaiss_avx2.cpython-310-darwin.so
 12M	archive/.venv/lib/python3.10/site-packages/faiss/_swigfaiss.cpython-310-darwin.so
 12M	.venv/lib/python3.10/site-packages/faiss/_swigfaiss.cpython-310-darwin.so
8.7M	archive/.venv/lib/python3.10/site-packages/tokenizers/tokenizers.abi3.so
8.7M	.venv/lib/python3.10/site-packages/tokenizers/tokenizers.abi3.so
6.2M	archive/.venv/lib/python3.10/site-packages/numpy/_core/_multiarray_umath.cpython-310-darwin.so
6.2M	.venv/lib/python3.10/site-packages/numpy/_core/_multiarray_umath.cpython-310-darwin.so
5.7M	archive/.venv/lib/python3.10/site-packages/hf_xet/hf_xet.abi3.so
5.7M	.venv/lib/python3.10/site-packages/hf_xet/hf_xet.abi3.so
5.3M	.mypy_cache/3.10/numpy/__init__.data.json
5.1M	archive/.venv/lib/python3.10/site-packages/scipy/optimize/_highspy/_core.cpython-310-darwin.so

- Todo list (summary):


---
