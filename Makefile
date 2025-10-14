.PHONY: setup test lint api cli clean uv-install lock \
	db-upgrade db-current db-revision \
	help prereqs prereqs-docker \
    compose-build compose-up compose-down compose-down-v compose-logs compose-ps compose-restart compose-health

# Variables
API_PORT ?= 9595

help: ## Show this help
	@echo "Available targets:" && \
	awk 'BEGIN {FS = ":.*##"; printf "\n"} /^[a-zA-Z0-9_.-]+:.*?##/ { printf "  \033[36m%-28s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST) | sort

prereqs: prereqs-docker ## Check that required tools are installed

prereqs-docker: ## Check docker and docker compose
	@command -v docker >/dev/null 2>&1 || { echo "Error: docker not found in PATH"; exit 1; }
	@docker compose version >/dev/null 2>&1 || { echo "Error: docker compose not available"; exit 1; }
	@command -v curl >/dev/null 2>&1 || { echo "Error: curl not found in PATH"; exit 1; }

setup-dev: prereqs-docker ## Canonical local setup: build, up, and wait for health
	@echo "→ Starting evented enterprise stack"
	$(MAKE) -s compose-build
	$(MAKE) -s compose-up
	$(MAKE) -s compose-health

docs-build: ## Build MkDocs documentation
	@command -v mkdocs >/dev/null 2>&1 || { echo "mkdocs not found, skipping"; exit 0; }
	mkdocs build -q

docs-serve: ## Serve MkDocs site locally
	@command -v mkdocs >/dev/null 2>&1 || { echo "mkdocs not found, install via 'uv run pip install mkdocs mkdocs-material'"; exit 1; }
	mkdocs serve -a 127.0.0.1:8008

ci-verify: prereqs-docker ## CI-style verify with Compose: up, health check, and tear down
	$(MAKE) -s compose-up
	$(MAKE) -s compose-health
	$(MAKE) -s compose-down

uv-install:
	@which uv >/dev/null 2>&1 || (curl -LsSf https://astral.sh/uv/install.sh | sh -s -- -y)
	@~/.local/bin/uv --version

setup: uv-install
	~/.local/bin/uv sync --extra api --extra events --extra dev

lock: uv-install
	~/.local/bin/uv lock

test:
	~/.local/bin/uv run pytest -q

lint:
	~/.local/bin/uv run mypy somafractalmemory

api:
	~/.local/bin/uv run uvicorn somafractalmemory.http_api:app --reload

cli:
	~/.local/bin/uv run soma -h

db-upgrade: ## Run Alembic migrations
	~/.local/bin/uv run alembic upgrade head

db-current: ## Show current Alembic revision
	~/.local/bin/uv run alembic current

db-revision: ## Generate a new Alembic migration
	@MSG=$${MSG:-"describe change"}; \
	~/.local/bin/uv run alembic revision -m "$$MSG"

clean:
	rm -rf .pytest_cache __pycache__ somafractalmemory.egg-info qdrant.db *.index audit_log.jsonl .ipynb_checkpoints

# Docker Compose workflows

compose-build: prereqs-docker ## Build images for Docker Compose
	docker compose build --progress=plain

compose-up: prereqs-docker ## Start the full stack in the background
	docker compose --profile core --profile consumer up -d
	@echo "→ API will be available at: http://127.0.0.1:$(API_PORT)"

compose-logs: prereqs-docker ## Tail API logs
	docker compose logs -f --tail=200 api

compose-ps: prereqs-docker ## Show container status
	docker compose ps

compose-restart: prereqs-docker ## Restart the API service
	docker compose restart api

compose-health: prereqs-docker ## Wait for API /healthz to return 200
	@echo "Waiting for API health at http://127.0.0.1:$(API_PORT)/healthz ..."; \
	for i in $$(seq 1 60); do \
	  if curl -fsS http://127.0.0.1:$(API_PORT)/healthz >/dev/null; then echo "✓ API healthy"; exit 0; fi; \
	  sleep 2; \
	done; \
	echo "✗ API did not become healthy in time"; exit 1

compose-down: prereqs-docker ## Stop all services (keep volumes)
	docker compose down

compose-down-v: prereqs-docker ## Stop all services and remove volumes (DANGEROUS)
	docker compose down -v
