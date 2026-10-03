"""TASK E — dead ``infra/aaas/`` pointers and a silent logging backend swap."""

from __future__ import annotations

import ast
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_API_CORE = _REPO / "somafractalmemory/api/core.py"
_ROUTERS_INIT = _REPO / "somafractalmemory/api/routers/__init__.py"
_LOGGER = _REPO / "somafractalmemory/admin/common/utils/logger.py"


class TestLeftoversAndLoggingBackend:
    """Dead pointers gone; no silent logging backend swap."""

    def test_api_core_has_no_aaas_pointer(self):
        source = _API_CORE.read_text(encoding="utf-8")
        assert "infra/aaas" not in source

    def test_routers_init_has_no_aaas_pointer(self):
        source = _ROUTERS_INIT.read_text(encoding="utf-8")
        assert "infra/aaas" not in source

    def test_logger_has_no_silent_structlog_swap(self):
        source = _LOGGER.read_text(encoding="utf-8")
        assert "HAS_STRUCTLOG = False" not in source
        tree = ast.parse(source)
        # No top-level try/except that assigns a boolean fallback flag.
        for node in tree.body:
            if isinstance(node, ast.Try):
                for handler in node.handlers:
                    for stmt in handler.body:
                        if isinstance(stmt, ast.Assign):
                            for target in stmt.targets:
                                if isinstance(target, ast.Name) and target.id.startswith("HAS_"):
                                    raise AssertionError(
                                        "logger silently swaps the logging backend on ImportError"
                                    )

    def test_logger_requires_structlog(self):
        source = _LOGGER.read_text(encoding="utf-8")
        assert "import structlog" in source
        # Refusal, not a quiet stdlib fallback: the import is unguarded or raises.
        assert "HAS_STRUCTLOG" not in source
