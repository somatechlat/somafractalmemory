# __init__.py for somafractalmemory package

# NOTE: The http_api module has module-level code that creates a memory system,
# which requires real infrastructure (Redis, Postgres, Milvus) and SOMA_API_TOKEN.
# To avoid import failures during testing or when infrastructure is unavailable,
# we do NOT import http_api at package init time.
#
# If you need Prometheus metrics registration, import http_api explicitly:
#   from somafractalmemory import http_api
#
# The test_metrics_exposed test should import http_api directly if needed.

# No automatic http_api import - this prevents module-level initialization
# from running when the package is imported for testing or library use.
