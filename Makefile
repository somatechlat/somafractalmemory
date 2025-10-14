.PHONY: setup test lint api cli clean uv-install lock \
	db-upgrade db-current db-revision \
	help prereqs prereqs-docker \
        compose-build compose-up compose-down compose-down-v compose-logs compose-ps compose-restart compose-health compose-print-ports

# Variables and dynamic detection

# Default host ports (Compose) – used when services are not running
API_PORT ?= 9595
POSTGRES_HOST_PORT ?= 5433
REDIS_HOST_PORT ?= 6381
QDRANT_HOST_PORT ?= 6333

# Resolve ports dynamically if possible
API_PORT_RUNTIME := $(or $(call dc_port,api,9595),$(API_PORT))
POSTGRES_HOST_PORT_RUNTIME := $(or $(call dc_port,postgres,5432),$(POSTGRES_HOST_PORT))
REDIS_HOST_PORT_RUNTIME := $(or $(call dc_port,redis,6379),$(REDIS_HOST_PORT))
QDRANT_HOST_PORT_RUNTIME := $(or $(call dc_port,qdrant,6333),$(QDRANT_HOST_PORT))

# Shared infra defaults
MODE ?= dev

# Help and prerequisites

help: ## Show this help
	@echo "Available targets:" && \
	awk 'BEGIN {FS = ":.*##"; printf "\n"} /^[a-zA-Z0-9_.-]+:.*?##/ { printf "  \033[36m%-28s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST) | sort

prereqs: prereqs-docker ## Check that required tools are installed

prereqs-docker: ## Check docker and docker compose
	@command -v docker >/dev/null 2>&1 || { echo "Error: docker not found in PATH"; exit 1; }
	@docker compose version >/dev/null 2>&1 || { echo "Error: docker compose not available (Docker Desktop 2.20+ required)"; exit 1; }
	@command -v curl >/dev/null 2>&1 || { echo "Error: curl not found in PATH"; exit 1; }
	@command -v jq >/dev/null 2>&1 || { echo "Warning: jq not found; JSON output will not be prettified"; }

settings: ## Print detected settings (ports, images, helm values)
	@echo "Compose runtime ports (detected if running):" && \
	echo "  API:              http://127.0.0.1:$(API_PORT_RUNTIME)" && \
	echo "  Postgres:         127.0.0.1:$(POSTGRES_HOST_PORT_RUNTIME)" && \
	echo "  Redis:            127.0.0.1:$(REDIS_HOST_PORT_RUNTIME)" && \
	echo "  Qdrant:           127.0.0.1:$(QDRANT_HOST_PORT_RUNTIME)"

# Aggregated canonical setups
setup-dev: prereqs-docker ## Canonical local setup: auto-assign ports, build, up, wait for health
	@echo "→ Auto-assigning ports and starting evented enterprise stack"; \
	./scripts/assign_ports_and_start.sh; \
	$(MAKE) -s compose-health; \
	$(MAKE) -s settings

quickstart: setup-dev ## Alias for setup-dev

docs-build: ## Build MkDocs documentation (if mkdocs is installed)
	@command -v mkdocs >/dev/null 2>&1 || { echo "mkdocs not found, skipping"; exit 0; }
	mkdocs build -q

docs-serve: ## Serve MkDocs site locally (if mkdocs is installed)
	@command -v mkdocs >/dev/null 2>&1 || { echo "mkdocs not found, install via 'uv run pip install mkdocs mkdocs-material'"; exit 1; }
	mkdocs serve -a 127.0.0.1:8008

ci-verify: prereqs-docker ## CI-style verify with Compose: up, wait for health, basic curls, tear down
	$(MAKE) -s compose-up
	$(MAKE) -s compose-health
	@echo "→ Curl endpoints"; \
	curl -fsS http://127.0.0.1:$(API_PORT)/healthz >/dev/null && echo "✓ /healthz"; \
	curl -fsS http://127.0.0.1:$(API_PORT)/readyz >/dev/null && echo "✓ /readyz"; \
	curl -fsS http://127.0.0.1:$(API_PORT)/metrics >/dev/null && echo "✓ /metrics"; \
	echo "→ Stats (may rely on backends):"; \
	curl -fsS http://127.0.0.1:$(API_PORT)/stats || true; \
	$(MAKE) -s compose-down

uv-install:
	@which uv >/dev/null 2>&1 || (curl -LsSf https://astral.sh/uv/install.sh | sh -s -- -y)
	@~/.local/bin/uv --version

setup: uv-install
	~/.local/bin/uv sync --extra api

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

db-upgrade: ## Run Alembic migrations against POSTGRES_URL (defaults from alembic.ini)
	~/.local/bin/uv run alembic upgrade head

db-current: ## Show current Alembic revision for the configured database
	~/.local/bin/uv run alembic current

db-revision: ## Generate a new Alembic migration skeleton with message MSG="..."
	@MSG=$${MSG:-"describe change"}; \
	~/.local/bin/uv run alembic revision -m "$$MSG"

.PHONY: clean
clean:
	rm -rf .pytest_cache __pycache__ somafractalmemory.egg-info qdrant.db *_qdrant *.index audit_log.jsonl .ipynb_checkpoints

# Docker Compose workflows

compose-build: prereqs-docker ## Build images for Docker Compose
	docker compose build --progress=plain

compose-up: prereqs-docker ## Start the full stack in the background
	docker compose up -d
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

compose-print-ports: prereqs-docker ## Print actual published ports for running services
	@echo "API:       http://127.0.0.1:$$(docker compose port api 9595 | awk -F: 'END{print $$NF}')" || true
	@echo "Postgres:  127.0.0.1:$$(docker compose port postgres 5432 | awk -F: 'END{print $$NF}')" || true
	@echo "Redis:     127.0.0.1:$$(docker compose port redis 6379 | awk -F: 'END{print $$NF}')" || true
	@echo "Qdrant:    127.0.0.1:$$(docker compose port qdrant 6333 | awk -F: 'END{print $$NF}')" || true

compose-down: prereqs-docker ## Stop all services (keep volumes)
	docker compose down

compose-down-v: prereqs-docker ## Stop all services and remove volumes (DANGEROUS)
	docker compose down -v

# Kubernetes: Kind + Helm dev slice (NodePort 30797)

runtime-build: prereqs-docker ## Build slim runtime image for Helm deployment
	docker build -f Dockerfile.runtime -t somafractalmemory-runtime:local .

kind-up: prereqs-k8s ## Create Kind cluster (named 'sfm') with host port mappings
	@if ! kind get clusters 2>/dev/null | grep -q '^sfm$$'; then \
	  echo "Creating Kind cluster 'sfm' using helm/kind-config.yaml"; \
	  kind create cluster --name sfm --config helm/kind-config.yaml; \
	else \
	  echo "Kind cluster 'sfm' already exists"; \
	fi

kind-load: prereqs-k8s ## Load local runtime image into Kind node
	kind load docker-image somafractalmemory-runtime:local --name sfm

kind-down: prereqs-k8s ## Delete Kind cluster 'sfm'
	kind delete cluster --name sfm || true

helm-dev-install: prereqs-k8s ## Install/upgrade dev release (sfm-9797) with NodePort values
	helm upgrade --install sfm-9797 ./helm -n sfm-9797 --create-namespace \
	  --values helm/values-dev-port9797.yaml --wait
	@echo "→ API (NodePort) should be reachable at: http://127.0.0.1:$(DEV_NODEPORT)"

helm-dev-health: prereqs-k8s ## Check health of the dev release via NodePort
	@echo "Checking http://127.0.0.1:$(DEV_NODEPORT)/healthz ..."; \
	curl -fsS http://127.0.0.1:$(DEV_NODEPORT)/healthz | jq . || curl -fsS http://127.0.0.1:$(DEV_NODEPORT)/healthz || true

helm-dev-uninstall: prereqs-k8s ## Uninstall dev release (sfm-9797)
	helm uninstall sfm-9797 -n sfm-9797 || true

# SomaStack shared infra (Kind + Helm)

sharedinfra-kind-bootstrap: prereqs-k8s ## Recreate Kind cluster 'soma' and preload shared infra images
	./scripts/create-kind-soma.sh
	./scripts/preload-sharedinfra-images.sh

sharedinfra-kind-deploy: prereqs-k8s ## Deploy shared infra Helm chart into the Kind cluster
	./scripts/deploy-kind-sharedinfra.sh MODE=$(MODE)

sharedinfra-kind: sharedinfra-kind-bootstrap sharedinfra-kind-deploy ## Full shared infra reset + deploy
	@echo "Deploying shared infra..."

```
	@echo "Rendering helm values for mode '${MODE:=dev}'"

	@echo "Deploying full infra to kind (cluster: ${CLUSTER_NAME:=soma-kind})"

	@echo "Backing up postgres from container: ${CONTAINER:=somafractalmemory_postgres_1}"

```
