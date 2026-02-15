#!/usr/bin/env python3
"""Verify OpenAPI spec contains required graph endpoints.

Generates the OpenAPI spec from the Django Ninja API (no running server required)
and verifies that graph endpoints are present:
  - POST /graph/link
  - GET /graph/neighbors
  - GET /graph/path

Usage:
  SOMA_API_TOKEN=... python scripts/verify_openapi.py

Exit codes:
  0 - All graph endpoints present and valid
  1 - Missing or invalid endpoints
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Add repo root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def _load_openapi() -> dict:
    if not os.environ.get("DJANGO_SETTINGS_MODULE"):
        os.environ["DJANGO_SETTINGS_MODULE"] = "somafractalmemory.settings"
    if not os.environ.get("SOMA_API_TOKEN"):
        raise RuntimeError("SOMA_API_TOKEN must be set (API auth is mandatory).")

    import django

    django.setup()

    from somafractalmemory.api import api

    # Prefer Ninja's schema generator. If the installed Ninja version differs,
    # fall back to public helpers where available.
    if hasattr(api, "get_openapi_schema"):
        return api.get_openapi_schema()  # type: ignore[no-any-return]
    if hasattr(api, "openapi_schema"):
        return api.openapi_schema  # type: ignore[no-any-return]
    raise RuntimeError("Unable to generate OpenAPI schema from NinjaAPI instance.")


def verify_openapi_spec() -> bool:
    """Verify the OpenAPI spec contains required graph endpoints."""
    try:
        openapi_spec = _load_openapi()
    except Exception as e:
        print(f"ERROR: Failed to generate OpenAPI spec: {e}")
        return False

    required_endpoints = {
        "/graph/link": {
            "method": "post",
            "request_model": "GraphLinkRequest",
            "response_model": "GraphLinkResponse",
        },
        "/graph/neighbors": {
            "method": "get",
            "response_model": "GraphNeighborsResponse",
        },
        "/graph/path": {
            "method": "get",
            "response_model": "GraphPathResponse",
        },
    }

    paths = openapi_spec.get("paths", {})
    schemas = openapi_spec.get("components", {}).get("schemas", {})

    all_valid = True
    print("\n=== OpenAPI Verification Report ===\n")

    for endpoint, requirements in required_endpoints.items():
        method = requirements["method"]
        print(f"Checking {method.upper()} {endpoint}...")

        if endpoint not in paths:
            print("  MISSING: Endpoint not found in OpenAPI spec")
            all_valid = False
            continue

        endpoint_spec = paths[endpoint]
        if method not in endpoint_spec:
            print(f"  MISSING: Method {method.upper()} not defined")
            all_valid = False
            continue

        method_spec = endpoint_spec[method]

        # Check response model
        response_model = requirements.get("response_model")
        if response_model:
            responses = method_spec.get("responses", {})
            success_response = responses.get("200", {}) or responses.get("201", {})
            content = success_response.get("content", {})
            json_content = content.get("application/json", {})
            schema_ref = json_content.get("schema", {}).get("$ref", "")
            if response_model not in schema_ref:
                print(
                    f"  WARNING: response model mismatch (expected {response_model}, got {schema_ref})"
                )

        # Check request model for POST
        if method == "post":
            request_model = requirements.get("request_model")
            if request_model:
                request_body = method_spec.get("requestBody", {})
                content = request_body.get("content", {})
                json_content = content.get("application/json", {})
                schema_ref = json_content.get("schema", {}).get("$ref", "")
                if request_model not in schema_ref:
                    print(
                        f"  WARNING: request model mismatch (expected {request_model}, got {schema_ref})"
                    )

        print("  OK")

    print("\n--- Schema Verification ---")
    for schema_name in (
        "GraphLinkRequest",
        "GraphLinkResponse",
        "GraphNeighborsResponse",
        "GraphPathResponse",
    ):
        if schema_name in schemas:
            print(f"  OK: {schema_name}")
        else:
            print(f"  MISSING: {schema_name}")
            all_valid = False

    output_path = Path(__file__).parent.parent / "docs" / "openapi.json"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(json.dumps(openapi_spec, indent=2), encoding="utf-8")
    print(f"\nOpenAPI spec saved to: {output_path}")

    return all_valid


if __name__ == "__main__":
    success = verify_openapi_spec()
    raise SystemExit(0 if success else 1)
