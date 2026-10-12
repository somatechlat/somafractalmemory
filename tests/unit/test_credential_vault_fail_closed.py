"""TASK C — secrets resolve from Vault only (Settings Law 2026-10-09).

A swallowed Vault error is a bypass. A missing Vault topology is a refusal,
never a licence to read a secret from the environment. There is no injection
channel and no code default (Rule 164 / Rule 91).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured

from somafractalmemory.admin.core.security import vault_client
from somafractalmemory.settings import django_core


class TestVaultFailureIsNotEnvFallback:
    """A Vault error raises; absence of Vault also raises. Never ENV."""

    def test_credential_raises_when_vault_fails(self, tmp_path, monkeypatch):
        # Vault topology present, but nothing is listening.
        monkeypatch.setattr(vault_client, "vault_topology_present", lambda: True)

        def _boom(path, key=None):
            raise vault_client.VaultAuthError("vault unreachable in test")

        monkeypatch.setattr(vault_client, "get_secret", _boom)
        monkeypatch.setenv("SOMA_SECRET_KEY", "env-value-must-not-win")

        with pytest.raises(ImproperlyConfigured):
            django_core._credential(
                "Django SECRET_KEY",
                vault=("somafractalmemory/credentials", "soma_secret_key"),
            )

    def test_credential_never_falls_back_to_env(self, monkeypatch):
        monkeypatch.setattr(vault_client, "vault_topology_present", lambda: False)
        monkeypatch.setenv("SOMA_SECRET_KEY", "env-value-must-not-win")

        with pytest.raises(ImproperlyConfigured):
            django_core._credential(
                "Django SECRET_KEY",
                vault=("somafractalmemory/credentials", "soma_secret_key"),
            )

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

    def test_credential_never_reads_environ(self):
        source = Path(django_core.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or node.name != "_credential":
                continue
            for child in ast.walk(node):
                if isinstance(child, ast.Attribute) and child.attr in (
                    "environ",
                    "getenv",
                ):
                    raise AssertionError("_credential consults os.environ — secrets are Vault only")
                if isinstance(child, ast.Name) and child.id == "env":
                    raise AssertionError(
                        "_credential consults environ.Env — secrets are Vault only"
                    )
