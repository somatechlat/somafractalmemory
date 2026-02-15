# ruff: noqa: E402
"""Test configuration file to ensure Prometheus metrics are registered before tests run."""

import django

if not django.apps.apps.ready:
    django.setup()

# Ensure API surfaces can import with mandatory auth in test runs.
# Ensure the Prometheus ``api_requests_total`` metric is registered before any
# test imports ``prometheus_client``. This avoids pulling in heavy optional
# dependencies and works even in minimal test
# environments.
try:
    from prometheus_client import Counter

    Counter(
        "api_requests_total",
        "Total number of API requests",
        ["endpoint", "method"],
    )
except Exception:
    # If prometheus_client is unavailable, the test that checks metrics will be
    # skipped or will fail – but the core library remains functional.
    pass
