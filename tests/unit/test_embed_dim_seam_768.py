"""Seam invariant: SFM vector dim is 768 everywhere and fail-closed.

The invariant is behavioural, not a source regex of one call form:

* the schema default on the TUNABLES registry is 768,
* ``MEM_EMBED_DIM`` is honoured as the seam alias for the same value,
* services refuse to guess when the dim is absent,
* nothing reintroduces a 256-dim default.
"""

from __future__ import annotations

import re
from pathlib import Path

from somafractalmemory.settings.model import schema_default

PKG = Path(__file__).resolve().parents[2] / "somafractalmemory"


def _read(rel: str) -> str:
    return (PKG / rel).read_text(encoding="utf-8")


class TestSfmDimDefaults:
    def test_settings_default_768(self):
        """The one declared default for SOMA_VECTOR_DIM is 768."""
        assert schema_default("SOMA_VECTOR_DIM") == 768

    def test_mem_embed_dim_is_honoured(self):
        """SOMA_VECTOR_DIM overrides, MEM_EMBED_DIM is the seam alias."""
        src = _read("settings/infra.py")
        assert "MEM_EMBED_DIM" in src
        assert "_read_vector_dim" in src
        # The alias chain must consult the explicit key first, then the seam
        # name, then the schema default — no further fallback.
        fn_src = src.split("def _read_vector_dim", 1)[1].split("\ndef ", 1)[0]
        assert fn_src.index("SOMA_VECTOR_DIM") < fn_src.index("MEM_EMBED_DIM")
        assert "schema_default" in fn_src

    def test_no_256_dim_default_in_services(self):
        src = _read("admin/core/services.py")
        assert not re.search(r"dim\s*:\s*int\s*=\s*256\b", src)

    def test_services_fail_closed_on_missing_dim(self):
        src = _read("admin/core/services.py")
        assert "refusing to guess" in src or "Never invent a fallback" in src
