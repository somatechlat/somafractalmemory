.PHONY: setup test lint api metrics cli bench clean uv-install lock

uv-install:
	@which uv >/dev/null 2>&1 || (curl -LsSf https://astral.sh/uv/install.sh | sh -s -- -y)
	@~/.local/bin/uv --version

setup: uv-install
	~/.local/bin/uv sync --extra api --extra events

lock: uv-install
	~/.local/bin/uv lock

test:
	~/.local/bin/uv run pytest -q

lint:
	~/.local/bin/uv run mypy somafractalmemory

api:
	~/.local/bin/uv run uvicorn examples.api:app --reload

metrics:
	~/.local/bin/uv run python examples/metrics_server.py

cli:
	~/.local/bin/uv run soma -h

bench:
	~/.local/bin/uv run python examples/benchmark.py --n 2000 --dim 256

.PHONY: clean
clean:
	rm -rf .pytest_cache __pycache__ somafractalmemory.egg-info qdrant.db *_qdrant *.index audit_log.jsonl .ipynb_checkpoints
