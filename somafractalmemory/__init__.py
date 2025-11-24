# __init__.py for somafractalmemory package

# Import the HTTP API module to ensure Prometheus metric objects are instantiated
# and registered with the global ``prometheus_client`` registry at import time.
# This satisfies the ``test_metrics_exposed`` test, which checks that the metric
# names appear in ``prometheus_client.REGISTRY`` without needing to start the
# FastAPI server. Importing the module has no side‑effects beyond metric
# registration because the app is only created when the module is executed, not
# when the symbols are imported.
try:
    # Importing for side‑effects only – the symbols are not re‑exported.
    from . import http_api  # noqa: F401
except Exception:
    # In environments where the HTTP API cannot be imported (e.g., missing
    # optional dependencies), we silently ignore the error because the core
    # library functionality does not depend on the API layer.
    pass

# No additional metric registration is required here because importing the
# ``http_api`` module (above) already registers the necessary Prometheus counters.
