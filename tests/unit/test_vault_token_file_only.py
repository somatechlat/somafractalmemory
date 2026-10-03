"""Vault token comes from a file, never from the environment.

VIBE Rule 164 / zero-trust: the Vault token is a credential. It is delivered
as a file named by ``VAULT_TOKEN_FILE`` (a path is topology). Exporting the
token value into the process environment leaves it in ``ps``,
``/proc/*/environ`` and every crash dump.

Covers:
- Static: the vault client source never looks up ``SOMA_VAULT_TOKEN`` /
  ``VAULT_TOKEN`` values from ``os.environ``.
- Behavioural: a present token file authenticates (live Vault) or at least
  resolves the token; missing/empty/unset raises.
- Behavioural: env-provided token *values* are ignored.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

from somafractalmemory.admin.core.security import vault_client
from somafractalmemory.admin.core.security.vault_client import (
    VaultNotConfigured,
    _resolve_vault_token,
)

# Exact env *value* names that must never be read. ``VAULT_TOKEN_FILE`` is a
# path and is deliberately absent from this set.
_FORBIDDEN_TOKEN_ENV_NAMES = frozenset({"SOMA_VAULT_TOKEN", "VAULT_TOKEN"})


def _token_env_lookups_in_module() -> set[str]:
    """Return env names this module reads via ``os.environ``.

    Walks the AST so a later ``.replace`` cannot hide a lookup the way a
    substring search would.
    """
    source = Path(vault_client.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    found: set[str] = set()

    for node in ast.walk(tree):
        # os.environ.get("NAME") / os.environ.get("NAME", ...)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr != "get":
                continue
            if not (
                isinstance(node.func.value, ast.Attribute) and node.func.value.attr == "environ"
            ):
                continue
            if node.args and isinstance(node.args[0], ast.Constant):
                if isinstance(node.args[0].value, str):
                    found.add(node.args[0].value)
        # os.environ["NAME"]
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute):
            if node.value.attr != "environ":
                continue
            if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                found.add(node.slice.value)

    return found


class TestStaticNoTokenEnvLookup:
    """The source must not consult ENV for the token value."""

    def test_module_never_reads_token_values_from_environ(self):
        looked_up = _token_env_lookups_in_module()
        leaked = looked_up & _FORBIDDEN_TOKEN_ENV_NAMES
        assert not leaked, (
            f"vault_client reads token VALUES from the environment: {sorted(leaked)}. "
            "VIBE Rule 164: the token is a file (VAULT_TOKEN_FILE), never an ENV value."
        )

    def test_vault_token_file_path_lookup_is_allowed(self):
        """The *path* is topology and may live in the environment.

        The source may read it via the ``DEFAULT_TOKEN_FILE_ENV`` constant or
        the literal name; either is fine as long as the token *value* names
        never appear.
        """
        source = Path(vault_client.__file__).read_text(encoding="utf-8")
        assert "DEFAULT_TOKEN_FILE_ENV" in source
        assert "VAULT_TOKEN_FILE" in source

    def test_resolve_vault_token_reads_file_not_environ_value(self, tmp_path, monkeypatch):
        token_file = tmp_path / "vault_token"
        token_file.write_text("hvs.from-file\n", encoding="utf-8")
        monkeypatch.setenv("VAULT_TOKEN_FILE", str(token_file))
        monkeypatch.setenv("VAULT_TOKEN", "leaked-from-env")
        monkeypatch.setenv("SOMA_VAULT_TOKEN", "leaked-from-env")

        assert _resolve_vault_token() == "hvs.from-file"


class TestTokenFileAbsentRaises:
    """Missing or empty token file is fatal — never 'no secrets available'."""

    def test_unset_token_file_path_raises(self, monkeypatch):
        monkeypatch.delenv("VAULT_TOKEN_FILE", raising=False)
        with pytest.raises(VaultNotConfigured):
            _resolve_vault_token()

    def test_missing_token_file_raises(self, tmp_path, monkeypatch):
        monkeypatch.setenv("VAULT_TOKEN_FILE", str(tmp_path / "does-not-exist"))
        with pytest.raises(VaultNotConfigured):
            _resolve_vault_token()

    def test_empty_token_file_raises(self, tmp_path, monkeypatch):
        empty = tmp_path / "empty_token"
        empty.write_text("\n  \n", encoding="utf-8")
        monkeypatch.setenv("VAULT_TOKEN_FILE", str(empty))
        with pytest.raises(VaultNotConfigured):
            _resolve_vault_token()


class TestTokenFilePresent:
    """A present token file is the only credential source."""

    def test_present_token_file_resolves_stripped_token(self, tmp_path, monkeypatch):
        token_file = tmp_path / "vault_token"
        token_file.write_text("  hvs.file-token-value  \n", encoding="utf-8")
        monkeypatch.setenv("VAULT_TOKEN_FILE", str(token_file))
        assert _resolve_vault_token() == "hvs.file-token-value"

    def test_present_token_file_authenticates_against_live_vault(self, monkeypatch):
        """Real Vault + real token file → client authenticates. Skip otherwise."""
        addr = os.environ.get("SOMA_VAULT_ADDR") or os.environ.get("VAULT_ADDR")
        token_file = os.environ.get("VAULT_TOKEN_FILE")
        if not addr or not token_file:
            pytest.skip(
                "Vault not configured (need SOMA_VAULT_ADDR/VAULT_ADDR and "
                "VAULT_TOKEN_FILE); token-file resolution is covered offline"
            )
        vault_client._get_vault_client.cache_clear()
        try:
            client = vault_client._get_vault_client()
            assert client.is_authenticated() is True
        finally:
            vault_client._get_vault_client.cache_clear()

    def test_client_uses_token_file_for_authentication_material(self, tmp_path, monkeypatch):
        """With topology present, client construction consumes the token file.

        A live Vault is optional here: the security property is that the token
        bytes come from the file. Authentication against a real server is
        asserted in the live test above.
        """
        token_file = tmp_path / "vault_token"
        token_file.write_text("hvs.file-only-token", encoding="utf-8")
        monkeypatch.setenv("VAULT_TOKEN_FILE", str(token_file))
        monkeypatch.delenv("SOMA_VAULT_TOKEN", raising=False)
        monkeypatch.delenv("VAULT_TOKEN", raising=False)
        monkeypatch.delenv("SOMA_VAULT_ADDR", raising=False)
        monkeypatch.delenv("VAULT_ADDR", raising=False)

        assert _resolve_vault_token() == "hvs.file-only-token"

        # No address → not configured, and that must raise rather than guess.
        vault_client._get_vault_client.cache_clear()
        try:
            with pytest.raises(VaultNotConfigured):
                vault_client._get_vault_client()
        finally:
            vault_client._get_vault_client.cache_clear()
