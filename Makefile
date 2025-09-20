.PHONY: setup test lint api metrics cli

setup:
	python3 -m venv .venv && . .venv/bin/activate && \
	pip install --upgrade pip && \
	# Generate requirements.txt from YAML (simple format) then install
	grep -E '^- ' requirements.yaml | sed 's/^- //' > requirements.txt || true && \
	grep -E '^- ' api-requirements.yaml | sed 's/^- //' > api-requirements.txt || true && \
	pip install -r requirements.txt && pip install -e .

test:
	. .venv/bin/activate && pytest -q

lint:
	. .venv/bin/activate && mypy somafractalmemory

api:
	. .venv/bin/activate && ./scripts/free_port.sh 9595 || true && uvicorn examples.api:app --host 0.0.0.0 --port 9595 --workers 1 --log-level info

metrics:
	. .venv/bin/activate && python examples/metrics_server.py

cli:
	. .venv/bin/activate && soma -h

bench:
	. .venv/bin/activate && python examples/benchmark.py --n 2000 --dim 256

.PHONY: clean
clean:
	rm -rf .pytest_cache __pycache__ somafractalmemory.egg-info qdrant.db *_qdrant *.index audit_log.jsonl .ipynb_checkpoints
