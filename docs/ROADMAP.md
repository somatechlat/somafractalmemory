Roadmap & CI/Minimal runtime plan

This file documents the decisions, CI design, and minimal runtime recipe created by the engineering assistant.

Goals
- Provide a fast, minimal Docker image suitable for production-testing against external Redis and Qdrant instances.
- Keep YAML files as the canonical dependency manifests.
- Provide a GitHub Actions CI pipeline that uses the YAML manifests and runs lint, tests, security scan, and a Docker smoke job.

Artifacts added locally (not committed unless approved)
- requirements-min.yaml, api-requirements-min.yaml
- scripts/generate_requirements.py
- scripts/ci_smoke_test.sh
- Dockerfile.min (updated locally to consume YAML)
- docker-run-min.sh (helper already present)
- .github/workflows/ci.yml

How the minimal runtime works
1. YAML -> requirements: the `scripts/generate_requirements.py` script reads `requirements-min.yaml` and writes `requirements-min.txt`.
2. Docker build: `Dockerfile.min` (local) runs `generate_requirements.py` during image build and installs the generated requirements into a venv.
3. Runtime: container runs `uvicorn examples.api:app` on port 9595. For local testing we map host 9596->container 9595 to avoid conflict with existing server.

CI design summary
- Jobs: lint, test, security (bandit), docker-smoke
- The docker-smoke job starts Redis and Qdrant service containers in the runner so the smoke test is self-contained.
- The YAML manifests are the single source of truth for dependencies.

Next steps
- Review the CI YAML and scripts; if approved, I will commit the CI workflow and scripts to the repository and run a PR to validate.
- Optionally: expand the YAML manifests to include a `dev` or `test` YAML for test-specific deps (pytest, fakeredis).
