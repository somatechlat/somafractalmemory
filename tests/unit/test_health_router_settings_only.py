"""TASK B — the health router must not read secrets from os.environ.

Routers resolve configuration from Django settings (which already apply the
Vault / injection rules). A credential is never defaulted to localhost.
"""

from __future__ import annotations

import ast
from pathlib import Path

_HEALTH = Path(__file__).resolve().parents[2] / "somafractalmemory/api/routers/health.py"


def _environ_names_in(path: Path) -> set[str]:
    """Env names read via ``os.environ`` in a file (AST, not substring)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr != "get":
                continue
            if not (
                isinstance(node.func.value, ast.Attribute) and node.func.value.attr == "environ"
            ):
                continue
            if (
                node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                found.add(node.args[0].value)
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute):
            if node.value.attr == "environ" and isinstance(node.slice, ast.Constant):
                if isinstance(node.slice.value, str):
                    found.add(node.slice.value)
    return found


class TestHealthRouterNoEnvSecrets:
    """Settings only; no credential default of localhost."""

    def test_health_router_has_no_os_environ(self):
        names = _environ_names_in(_HEALTH)
        assert not names, (
            f"health router reads os.environ: {sorted(names)}. "
            "Routers must resolve configuration from Django settings."
        )

    def test_health_router_source_mentions_settings_not_localhost_defaults(self):
        source = _HEALTH.read_text(encoding="utf-8")
        # The credential must not be defaulted to a local password via os.environ.
        assert 'os.environ.get("SOMA_REDIS_PASSWORD"' not in source
        assert 'os.environ.get("SOMA_MILVUS_HOST"' not in source
        assert 'os.environ.get("SOMA_REDIS_HOST"' not in source
        # Settings-based resolution is required.
        assert (
            'getattr(settings, "SOMA_REDIS_HOST"' in source or "settings.SOMA_REDIS_HOST" in source
        )
        assert (
            'getattr(settings, "SOMA_REDIS_PASSWORD"' in source
            or "settings.SOMA_REDIS_PASSWORD" in source
        )
        assert (
            'getattr(settings, "SOMA_MILVUS_HOST"' in source
            or "settings.SOMA_MILVUS_HOST" in source
        )
