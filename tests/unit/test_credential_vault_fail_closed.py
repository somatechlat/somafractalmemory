"""TASK C — a Vault *failure* must raise from ``_credential``.

A swallowed Vault error is a bypass. Only a deployment with no Vault topology
at all may use the injection channel; once Vault is claimed, it must work.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured

from somafractalmemory.admin.core.security import vault_client
from somafractalmemory.settings import django_core


class TestVaultFailureIsNotEnvFallback:
    """A Vault error raises; only a *nonexistent* Vault falls through."""

    def test_credential_raises_when_vault_fails(self, tmp_path, monkeypatch):
        # Vault topology present, but nothing is listening.
        monkeypatch.setenv("SOMA_VAULT_ADDR", "http://127.0.0.1:1")
        monkeypatch.delenv("VAULT_ADDR", raising=False)
        token_file = tmp_path / "vault_token"
        token_file.write_text("not-a-live-token", encoding="utf-8")
        monkeypatch.setenv("VAULT_TOKEN_FILE", str(token_file))
        monkeypatch.setenv("SOMA_SECRET_KEY", "env-value-must-not-win")

        vault_client._get_vault_client.cache_clear()
        try:
            with pytest.raises(ImproperlyConfigured):
                django_core._credential(
                    "Django SECRET_KEY",
                    "SOMA_SECRET_KEY",
                    vault=("somafractalmemory/credentials", "soma_secret_key"),
                )
        finally:
            vault_client._get_vault_client.cache_clear()

    def test_credential_uses_injection_only_when_vault_is_absent(self, monkeypatch):
        monkeypatch.delenv("SOMA_VAULT_ADDR", raising=False)
        monkeypatch.delenv("VAULT_ADDR", raising=False)
        monkeypatch.delenv("VAULT_TOKEN_FILE", raising=False)
        monkeypatch.setenv("SOMA_SECRET_KEY", "injected-test-value")

        resolved = django_core._credential(
            "Django SECRET_KEY",
            "SOMA_SECRET_KEY",
            vault=("somafractalmemory/credentials", "soma_secret_key"),
        )
        assert resolved == "injected-test-value"

    def test_credential_source_has_no_except_pass(self):
        source = Path(django_core.__file__).read_text(encoding="utf-8")
        assert "except Exception:\n            # Vault unreachable" not in source
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or node.name != "_credential":
                continue
            for child in ast.walk(node):
                if not isinstance(child, ast.Try):
                    continue
                for handler in child.handlers:
                    assert not (len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass)), (
                        "_credential still has `except: pass` — "
                        "a swallowed Vault error is a bypass"
                    )
        else:
            assert True
