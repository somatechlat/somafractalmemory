#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ne 1 ]; then
  echo "Usage: ci_smoke_test.sh <health-url>"
  exit 2
fi
URL="$1"

# Poll the health endpoint up to 30s
for i in {1..30}; do
  echo "Attempt $i: GET $URL"
  body=$(curl -sS "$URL" || true)
  if echo "$body" | grep -q 'kv_store' && echo "$body" | grep -q 'vector_store'; then
    echo "Smoke test: health ok"
    echo "$body"
    exit 0
  fi
  sleep 1
done

echo "Smoke test failed: unexpected body:\n$body"
exit 1
