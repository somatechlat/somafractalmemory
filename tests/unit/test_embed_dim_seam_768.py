"""Seam invariant: SFM vector dim is 768 everywhere and fail-closed."""

from __future__ import annotations

import re
from pathlib import Path

PKG = Path(__file__).resolve().parents[2] / "somafractalmemory"


def _read(rel: str) -> str:
    return (PKG / rel).read_text(encoding="utf-8")


class TestSfmDimDefaults:
    def test_settings_default_768(self):
        src = _read("settings/infra.py")
        assert re.search(
            r"SOMA_VECTOR_DIM\s*=\s*env\.int\(\s*[\"']SOMA_VECTOR_DIM[\"']\s*,\s*default\s*=\s*env\.int\(\s*[\"']MEM_EMBED_DIM[\"']\s*,\s*default\s*=\s*768\s*\)\)",
            src,
        )

    def test_no_256_dim_default_in_services(self):
        src = _read("admin/core/services.py")
        assert not re.search(r"dim\s*:\s*int\s*=\s*256\b", src)

    def test_services_fail_closed_on_missing_dim(self):
        src = _read("admin/core/services.py")
        assert "refusing to guess" in src or "Never invent a fallback" in src
