#!/usr/bin/env bash
set -e

# Start FastAPI server in background
uvicorn somafractalmemory.http_api:app --host 0.0.0.0 --port 9595 &
# Start the consumer script in background
python scripts/run_consumers.py &

# Wait for any process to exit (if one crashes, container stops)
wait -n
# Exit with the status of the process that exited first
exit $?
