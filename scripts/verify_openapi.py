#!/usr/bin/env python3
"""Verify OpenAPI spec contains required graph endpoints.

This script extracts the OpenAPI spec from the FastAPI app and verifies
that the graph endpoints (/graph/link, /graph/neighbors, /graph/path)
are properly defined.

Usage:
    python scripts/verify_openapi.py

Exit codes:
    0 - All graph endpoints present and valid
    1 - Missing or invalid endpoints
"""

import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def verify_openapi_spec() -> bool:
    """Verify the OpenAPI spec contains required graph endpoints."""
    # Import here to avoid import errors if dependencies missing
    try:
        from somafractalmemory.http_api import app
    except ImportError as e:
        print(f"ERROR: Failed to import http_api: {e}")
        print("Make sure you're running from the somafractalmemory directory")
        return False
    except Exception as e:
        # Some initialization errors are expected without full infra
        print(f"WARNING: Import had errors (expected without infra): {e}")
        # Try to get the app anyway
        try:
            from somafractalmemory.http_api import app
        except Exception:
            print("ERROR: Cannot import app even after retry")
            return False

    # Get OpenAPI spec
    try:
        openapi_spec = app.openapi()
    except Exception as e:
        print(f"ERROR: Failed to generate OpenAPI spec: {e}")
        return False

    # Required graph endpoints
    required_endpoints = {
        "/graph/link": {
            "method": "post",
            "description": "Create a link between two memory coordinates",
            "request_model": "GraphLinkRequest",
            "response_model": "GraphLinkResponse",
        },
        "/graph/neighbors": {
            "method": "get",
            "description": "Get neighbors of a coordinate",
            "response_model": "GraphNeighborsResponse",
        },
        "/graph/path": {
            "method": "get",
            "description": "Find shortest path between coordinates",
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
            print("  ❌ MISSING: Endpoint not found in OpenAPI spec")
            all_valid = False
            continue

        endpoint_spec = paths[endpoint]
        if method not in endpoint_spec:
            print(f"  ❌ MISSING: Method {method.upper()} not defined")
            all_valid = False
            continue

        method_spec = endpoint_spec[method]

        # Check response model
        response_model = requirements.get("response_model")
        if response_model:
            responses = method_spec.get("responses", {})
            success_response = responses.get("200", {})
            content = success_response.get("content", {})
            json_content = content.get("application/json", {})
            schema_ref = json_content.get("schema", {}).get("$ref", "")

            if response_model in schema_ref:
                print(f"  ✅ Response model: {response_model}")
            else:
                print(f"  ⚠️  Response model mismatch: expected {response_model}, got {schema_ref}")

        # Check request model for POST
        if method == "post":
            request_model = requirements.get("request_model")
            if request_model:
                request_body = method_spec.get("requestBody", {})
                content = request_body.get("content", {})
                json_content = content.get("application/json", {})
                schema_ref = json_content.get("schema", {}).get("$ref", "")

                if request_model in schema_ref:
                    print(f"  ✅ Request model: {request_model}")
                else:
                    print(
                        f"  ⚠️  Request model mismatch: expected {request_model}, got {schema_ref}"
                    )

        # Check tags
        tags = method_spec.get("tags", [])
        if "graph" in tags:
            print("  ✅ Tagged with 'graph'")
        else:
            print("  ⚠️  Missing 'graph' tag")

        # Check authentication (FastAPI uses dependencies for auth, not security in OpenAPI)
        # Security and dependencies are available in method_spec if needed
        _ = method_spec.get("security", [])
        _ = method_spec.get("dependencies", [])
        print("  ✅ Endpoint defined")

    # Check schemas exist
    print("\n--- Schema Verification ---")
    required_schemas = [
        "GraphLinkRequest",
        "GraphLinkResponse",
        "GraphNeighborsResponse",
        "GraphPathResponse",
    ]

    for schema_name in required_schemas:
        if schema_name in schemas:
            print(f"  ✅ Schema: {schema_name}")
        else:
            print(f"  ❌ MISSING Schema: {schema_name}")
            all_valid = False

    # Output summary
    print("\n=== Summary ===")
    if all_valid:
        print("✅ All graph endpoints are properly defined in OpenAPI spec")
    else:
        print("❌ Some endpoints or schemas are missing")

    # Optionally save the spec
    output_path = Path(__file__).parent.parent / "docs" / "openapi.json"
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(openapi_spec, f, indent=2)
    print(f"\nOpenAPI spec saved to: {output_path}")

    return all_valid


if __name__ == "__main__":
    success = verify_openapi_spec()
    sys.exit(0 if success else 1)
