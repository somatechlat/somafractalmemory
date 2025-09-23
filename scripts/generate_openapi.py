import json

from examples.api import app


def main() -> None:
    """Generate the OpenAPI JSON spec from the FastAPI example.
    The spec is written to ``openapi.json`` at the repository root.
    """
    spec = app.openapi()
    with open("openapi.json", "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, sort_keys=True)
    print("✅ openapi.json generated")


if __name__ == "__main__":
    main()
