.PHONY: setup test lint cli bench clean

setup:
	python3 -m venv .venv && . .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt && pip install -e .

test:
	. .venv/bin/activate && pytest -q

lint:
	. .venv/bin/activate && mypy src/somafractalmemory

cli:
	. .venv/bin/activate && soma -h

bench:
	. .venv/bin/activate && python run_performance_benchmark.py --scale medium

clean:
	rm -rf .pytest_cache __pycache__ somafractalmemory.egg-info qdrant.db *_qdrant *.index .ipynb_checkpoints
	# (leaves recovery/ intact)
