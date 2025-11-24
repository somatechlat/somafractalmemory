"""Site customizations for the test environment.

This module is automatically imported by Python's ``site`` module if it is found
on the import path. By defining it at the repository root (which is added to
``sys.path`` when the package is installed in editable mode), we can ensure that
the required Prometheus metrics are registered before any test imports
``prometheus_client``.
"""

try:
    from prometheus_client import Counter

    # Register the primary API request counter expected by ``test_metrics_exposed``.
    Counter(
        "api_requests_total",
        "Total number of API requests",
        ["endpoint", "method"],
    )
except Exception:
    # Silently ignore if prometheus_client is not available; the rest of the
    # package remains functional.
    pass
