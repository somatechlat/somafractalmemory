#!/bin/sh
set -eu

# Map environment variables to soma CLI arguments.
# This enables configuration via Docker Desktop UI (Environment tab) or docker run -e ...

# Safe defaults (avoid external services by default)
MODE="${SFM_MODE:-on_demand}"
NAMESPACE="${SFM_NAMESPACE:-cli_ns}"
CMD_NAME="${SFM_CMD:-}"

# Optional config: either a JSON string or a path mounted into the container
CONFIG_ARG=""
if [ "${SFM_CONFIG_JSON:-}" != "" ]; then
  case "${SFM_CONFIG_JSON}" in
    \{*)
      # Looks like inline JSON, write to temp file
      echo "${SFM_CONFIG_JSON}" > /tmp/config.json
      CONFIG_ARG="--config-json /tmp/config.json"
      ;;
    *)
      # Treat as file path (must exist inside the container)
      if [ -f "${SFM_CONFIG_JSON}" ]; then
        CONFIG_ARG="--config-json ${SFM_CONFIG_JSON}"
      fi
      ;;
  esac
fi

BASE_ARGS="--mode ${MODE} --namespace ${NAMESPACE} ${CONFIG_ARG}"

# If no command is provided, either run API server (FastAPI) or health server
if [ -z "${CMD_NAME}" ]; then
  PORT="${SFM_API_PORT:-9595}"
  HOST="${SFM_API_HOST:-0.0.0.0}"
  if [ "${SFM_SERVER:-}" = "1" ] || [ -z "${CMD_NAME}" ]; then
    echo "Starting FastAPI server at http://${HOST}:${PORT} (API mode, /docs available)" >&2
    exec uvicorn somafractalmemory.api_server:app --host "$HOST" --port "$PORT"
  else
    # CLI or health server fallback
    echo "Starting health server at ${HOST}:${PORT} (set SFM_SERVER=1 for API, or SFM_CMD for CLI)" >&2
    exec python /app/src/somafractalmemory/health_server.py
  fi
fi

case "${CMD_NAME}" in
  store)
    : "${SFM_STORE_COORD:?SFM_STORE_COORD is required for store}"
    : "${SFM_STORE_PAYLOAD:?SFM_STORE_PAYLOAD is required for store}"
    TYPE_ARG=""
    if [ "${SFM_STORE_TYPE:-}" != "" ]; then TYPE_ARG="--type ${SFM_STORE_TYPE}"; fi
    exec soma ${BASE_ARGS} store --coord "${SFM_STORE_COORD}" --payload "${SFM_STORE_PAYLOAD}" ${TYPE_ARG}
    ;;
  recall)
    : "${SFM_RECALL_QUERY:?SFM_RECALL_QUERY is required for recall}"
    TOPK_ARG=""; TYPE_ARG=""
    if [ "${SFM_RECALL_TOPK:-}" != "" ]; then TOPK_ARG="--top-k ${SFM_RECALL_TOPK}"; fi
    if [ "${SFM_RECALL_TYPE:-}" != "" ]; then TYPE_ARG="--type ${SFM_RECALL_TYPE}"; fi
    exec soma ${BASE_ARGS} recall --query "${SFM_RECALL_QUERY}" ${TOPK_ARG} ${TYPE_ARG}
    ;;
  link)
    : "${SFM_LINK_FROM:?SFM_LINK_FROM is required for link}"
    : "${SFM_LINK_TO:?SFM_LINK_TO is required for link}"
    TYPE_ARG=""; WEIGHT_ARG=""
    if [ "${SFM_LINK_TYPE:-}" != "" ]; then TYPE_ARG="--type ${SFM_LINK_TYPE}"; fi
    if [ "${SFM_LINK_WEIGHT:-}" != "" ]; then WEIGHT_ARG="--weight ${SFM_LINK_WEIGHT}"; fi
    exec soma ${BASE_ARGS} link --from "${SFM_LINK_FROM}" --to "${SFM_LINK_TO}" ${TYPE_ARG} ${WEIGHT_ARG}
    ;;
  path)
    : "${SFM_PATH_FROM:?SFM_PATH_FROM is required for path}"
    : "${SFM_PATH_TO:?SFM_PATH_TO is required for path}"
    TYPE_ARG=""; if [ "${SFM_PATH_TYPE:-}" != "" ]; then TYPE_ARG="--type ${SFM_PATH_TYPE}"; fi
    exec soma ${BASE_ARGS} path --from "${SFM_PATH_FROM}" --to "${SFM_PATH_TO}" ${TYPE_ARG}
    ;;
  neighbors)
    : "${SFM_NEIGHBORS_COORD:?SFM_NEIGHBORS_COORD is required for neighbors}"
    TYPE_ARG=""; LIMIT_ARG=""
    if [ "${SFM_NEIGHBORS_TYPE:-}" != "" ]; then TYPE_ARG="--type ${SFM_NEIGHBORS_TYPE}"; fi
    if [ "${SFM_NEIGHBORS_LIMIT:-}" != "" ]; then LIMIT_ARG="--limit ${SFM_NEIGHBORS_LIMIT}"; fi
    exec soma ${BASE_ARGS} neighbors --coord "${SFM_NEIGHBORS_COORD}" ${TYPE_ARG} ${LIMIT_ARG}
    ;;
  stats)
    exec soma ${BASE_ARGS} stats
    ;;
  export-graph)
    : "${SFM_EXPORT_GRAPH_PATH:?SFM_EXPORT_GRAPH_PATH is required for export-graph}"
    exec soma ${BASE_ARGS} export-graph --path "${SFM_EXPORT_GRAPH_PATH}"
    ;;
  import-graph)
    : "${SFM_IMPORT_GRAPH_PATH:?SFM_IMPORT_GRAPH_PATH is required for import-graph}"
    exec soma ${BASE_ARGS} import-graph --path "${SFM_IMPORT_GRAPH_PATH}"
    ;;
  export-memories)
    : "${SFM_EXPORT_MEMORIES_PATH:?SFM_EXPORT_MEMORIES_PATH is required for export-memories}"
    exec soma ${BASE_ARGS} export-memories --path "${SFM_EXPORT_MEMORIES_PATH}"
    ;;
  import-memories)
    : "${SFM_IMPORT_MEMORIES_PATH:?SFM_IMPORT_MEMORIES_PATH is required for import-memories}"
    REPLACE_ARG=""; if [ "${SFM_IMPORT_MEMORIES_REPLACE:-}" = "1" ] || [ "${SFM_IMPORT_MEMORIES_REPLACE:-}" = "true" ]; then REPLACE_ARG="--replace"; fi
    exec soma ${BASE_ARGS} import-memories --path "${SFM_IMPORT_MEMORIES_PATH}" ${REPLACE_ARG}
    ;;
  delete-many)
    : "${SFM_DELETE_MANY_COORDS:?SFM_DELETE_MANY_COORDS is required for delete-many}"
    exec soma ${BASE_ARGS} delete-many --coords "${SFM_DELETE_MANY_COORDS}"
    ;;
  store-bulk)
    : "${SFM_STORE_BULK_FILE:?SFM_STORE_BULK_FILE is required for store-bulk}"
    exec soma ${BASE_ARGS} store-bulk --file "${SFM_STORE_BULK_FILE}"
    ;;
  range)
    : "${SFM_RANGE_MIN:?SFM_RANGE_MIN is required for range}"
    : "${SFM_RANGE_MAX:?SFM_RANGE_MAX is required for range}"
    TYPE_ARG=""; if [ "${SFM_RANGE_TYPE:-}" != "" ]; then TYPE_ARG="--type ${SFM_RANGE_TYPE}"; fi
    exec soma ${BASE_ARGS} range --min "${SFM_RANGE_MIN}" --max "${SFM_RANGE_MAX}" ${TYPE_ARG}
    ;;
  analyze)
    exec soma ${BASE_ARGS} analyze
    ;;
  *)
    echo "Unknown SFM_CMD='${CMD_NAME}'. Showing help..." >&2
    exec soma --help
    ;;
esac
