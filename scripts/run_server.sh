#!/usr/bin/env bash
# Convenience script to start the SomaFractalMemory FastAPI server with metrics endpoint.
# Metrics are available at http://localhost:9595/metrics

# Activate virtual environment if present
if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
fi

# Run uvicorn
exec uvicorn somafractalmemory.http_api:app --host 0.0.0.0 --port 9595 "$@"
