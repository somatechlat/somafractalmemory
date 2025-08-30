.PHONY: setup test lint api metrics cli

setup:
	python3 -m venv .venv && . .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt && pip install -e .

test:
	. .venv/bin/activate && pytest -q

lint:
	. .venv/bin/activate && mypy somafractalmemory

api:
	. .venv/bin/activate && uvicorn examples.api:app --reload

metrics:
	. .venv/bin/activate && python examples/metrics_server.py

cli:
	. .venv/bin/activate && soma -h

bench:
	. .venv/bin/activate && python examples/benchmark.py --n 2000 --dim 256
