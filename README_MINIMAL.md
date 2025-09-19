Minimal runtime and local test guide

This README explains how to build and run the minimal test image locally (does NOT replace your running 9595 server).

Files
- `requirements-min.yaml` - YAML manifest for minimal runtime deps
- `api-requirements-min.yaml` - API-specific deps
- `Dockerfile.min` - Minimal Dockerfile that generates requirements from YAML and installs them
- `docker-run-min.sh` - helper to build and run the image on port 9596
- `scripts/generate_requirements.py` - YAML -> requirements.txt converter

Build & run (local)

1. Build and run the minimal image (maps host 9596 -> container 9595):

```bash
chmod +x docker-run-min.sh
./docker-run-min.sh
```

2. Smoke test: open http://127.0.0.1:9596/health

Notes
- This is intentionally minimal: heavy ML packages are excluded so the image is fast to build.
- To promote the YAML manifests as canonical source of truth, CI will use `scripts/generate_requirements.py` to convert YAML into pip-style requirements during workflow and Docker builds.
