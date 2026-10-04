"""SFM settings model — every tunable declared once, read through one resolver.

Resolution order (highest wins) — no hardcoded product behavior:

    1. Django settings   (deployment authority: django_core / infra / standalone)
    2. Schema default    (declared once, on the TUNABLES registry)

Env feeds Django settings (topology and tunables) in ``infra``. Vault owns
secrets (``django_core._credential``). Call sites never name a bare literal
default and never name a deployment URL — they call :func:`resolve_setting`,
:func:`service_url` or :func:`milvus_uri`.

This is the SomaFractalMemory equivalent of the somaAgent01 pattern in
``admin/core/helpers/settings_model.py`` + ``capsule_settings.py``. SFM has no
capsule and no AgentSetting layer, so the chain is two steps. The registry is
the registration: a key that is not in ``TUNABLES`` cannot be resolved
(fail-closed, Rule 91), and a tunable with no reader is a lie — either wire it
or delete it from this table and from ``infra``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured

# -----------------------------------------------------------------------------
# ISO-style categories (normative — keep in sync with docs/iso/SOMA-SFM-ARCH-001).
# -----------------------------------------------------------------------------
CATEGORY_INFRA = "INFRA"
CATEGORY_SECURITY = "SECURITY"
CATEGORY_MEMORY = "MEMORY"
CATEGORY_API = "API"
CATEGORY_OBSERVABILITY = "OBSERVABILITY"
CATEGORY_BACKUP = "BACKUP"

CATEGORIES: tuple[str, ...] = (
    CATEGORY_INFRA,
    CATEGORY_SECURITY,
    CATEGORY_MEMORY,
    CATEGORY_API,
    CATEGORY_OBSERVABILITY,
    CATEGORY_BACKUP,
)


class _Required:
    """Sentinel: a tunable with no schema default. Absent means fail closed."""

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "REQUIRED"


REQUIRED = _Required()


@dataclass(frozen=True)
class Tunable:
    """One administrable value: type, schema default, category, purpose."""

    kind: str  # "str" | "int" | "float" | "bool" | "list" | "path"
    default: Any  # schema default, or REQUIRED
    category: str
    description: str


# -----------------------------------------------------------------------------
# The registry. Values are declared HERE and nowhere else.
#
# Every key below has a reader in this codebase. A tunable with no reader is a
# lie and is deleted (see the list in ``settings/infra``). The survivors are
# the knobs whose behaviour already exists and is now wired to this table.
# -----------------------------------------------------------------------------
TUNABLES: dict[str, Tunable] = {
    # --- INFRA topology (readers: django_core.DATABASES, health, services,
    #     milvus_vector, vault_client) -----------------------------------------
    "SOMA_DB_NAME": Tunable("str", "somafractalmemory", CATEGORY_INFRA, "Postgres database name."),
    "SOMA_DB_HOST": Tunable("str", "localhost", CATEGORY_INFRA, "Postgres host."),
    "SOMA_DB_PORT": Tunable("str", "5432", CATEGORY_INFRA, "Postgres TCP port."),
    "SOMA_REDIS_HOST": Tunable(
        "str", None, CATEGORY_INFRA, "Redis host. Absent means no Redis is deployed."
    ),
    "SOMA_REDIS_PORT": Tunable("int", 6379, CATEGORY_INFRA, "Redis TCP port."),
    "SOMA_REDIS_DB": Tunable("int", 0, CATEGORY_INFRA, "Redis logical database index."),
    "SOMA_REDIS_PASSWORD": Tunable(
        "str",
        None,
        CATEGORY_SECURITY,
        "Redis AUTH password. Absent means Redis runs without AUTH (a real topology).",
    ),
    "SOMA_MILVUS_HOST": Tunable(
        "str", None, CATEGORY_INFRA, "Milvus host. Absent means no Milvus is deployed."
    ),
    "SOMA_MILVUS_PORT": Tunable("str", "19530", CATEGORY_INFRA, "Milvus TCP port."),
    "SOMA_MILVUS_TIMEOUT_S": Tunable(
        "float", 10.0, CATEGORY_INFRA, "MilvusClient connect/IO timeout in seconds."
    ),
    "SOMA_VAULT_URL": Tunable(
        "str",
        None,
        CATEGORY_INFRA,
        "Vault address. Absent means no Vault topology. Bootstrap reads "
        "SOMA_VAULT_ADDR/VAULT_ADDR from env; once Django settings are up, "
        "this key is the deployment authority.",
    ),
    # --- MEMORY (readers: api.core, services, milvus_vector, health) ----------
    "SOMA_MEMORY_NAMESPACE": Tunable(
        "str", "api_ns", CATEGORY_MEMORY, "Namespace the API service operates in."
    ),
    "SOMA_TEST_MEMORY_NAMESPACE": Tunable(
        "str", "test_ns", CATEGORY_MEMORY, "Namespace reserved for test-stats."
    ),
    # 768 is not arbitrary: it is the hidden size of the embedding model the
    # agent seam uses (microsoft/codebert-base) and the dim the Milvus collection
    # was created at. SOMA_VECTOR_DIM overrides when set explicitly; otherwise
    # MEM_EMBED_DIM is honoured so both sides share one vector space (see
    # ``settings.infra._read_vector_dim``). The agent seam computes embeddings
    # once and sends them precomputed at this dim.
    "SOMA_VECTOR_DIM": Tunable(
        "int",
        768,
        CATEGORY_MEMORY,
        "Vector dimension for stored embeddings (fixed per collection).",
    ),
    "SOMA_SIMILARITY_METRIC": Tunable(
        "str", "cosine", CATEGORY_MEMORY, "Milvus distance metric (cosine|ip|l2)."
    ),
    "SOMA_MILVUS_NLIST": Tunable(
        "int", 128, CATEGORY_MEMORY, "IVF_FLAT cluster count at collection creation."
    ),
    "SOMA_MILVUS_NPROBE": Tunable(
        "int", 16, CATEGORY_MEMORY, "IVF_FLAT clusters probed per search."
    ),
    "SOMA_SEARCH_CANDIDATE_MULTIPLIER": Tunable(
        "int",
        3,
        CATEGORY_MEMORY,
        "Over-fetch factor for vector candidates before ranking and paging.",
    ),
    "SOMA_HASH_EMBEDDING_PENALTY": Tunable(
        "float",
        0.25,
        CATEGORY_MEMORY,
        "Score multiplier for hash-fallback hits. Precomputed hits keep the "
        "raw score; hash-sourced hits are demoted because their vector space "
        "is not comparable.",
    ),
    # --- API / OBSERVABILITY (readers: logger, health, api.core) --------------
    "SOMA_LOG_LEVEL": Tunable("str", "INFO", CATEGORY_OBSERVABILITY, "Root log level."),
    "SOMA_LOG_JSON": Tunable(
        "bool", False, CATEGORY_OBSERVABILITY, "Render logs as JSON (otherwise console)."
    ),
    "SOMA_PROBE_TIMEOUT_S": Tunable(
        "float", 2.0, CATEGORY_API, "Timeout for health-probe backend checks."
    ),
    # --- BACKUP (reader: scripts/backup_restore.py) ---------------------------
    "SOMA_BACKUP_DIR": Tunable("path", "./backups", CATEGORY_BACKUP, "Local backup destination."),
    "SOMA_MEMORY_DATA_DIR": Tunable(
        "path", "./data", CATEGORY_BACKUP, "Local data directory the backup script copies."
    ),
    "SOMA_S3_BUCKET": Tunable(
        "str", "", CATEGORY_BACKUP, "S3 bucket for off-site backup. Empty means local only."
    ),
}

# Key -> category, for the ISO configuration tables.
KEY_CATEGORY: dict[str, str] = {key: t.category for key, t in TUNABLES.items()}


class _Unset:
    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "UNSET"


_UNSET = _Unset()


def _from_django(key: str) -> Any:
    """Read one key from Django settings. ``None``/empty means absent."""
    from django.conf import settings

    if not settings.configured:
        return None
    value = getattr(settings, key, None)
    if value is None:
        return None
    if isinstance(value, str) and value == "":
        return None
    if isinstance(value, list | tuple) and len(value) == 0:
        return None
    return value


def _coerce(key: str, kind: str, value: Any) -> Any:
    """Coerce a resolved value to the tunable's kind. Fail-closed on garbage."""
    try:
        if kind == "int":
            return int(value)
        if kind == "float":
            return float(value)
        if kind == "bool":
            if isinstance(value, bool):
                return value
            return str(value).strip().lower() in ("1", "true", "yes", "on")
        if kind == "list":
            if isinstance(value, str):
                return [v.strip() for v in value.split(",") if v.strip()]
            return list(value)
        if kind == "path":
            from pathlib import Path

            return Path(value)
        return str(value)
    except (TypeError, ValueError) as exc:
        raise ImproperlyConfigured(
            f"{key}: value {value!r} does not parse as {kind}. "
            "VIBE Rule 91: an unparseable setting is not permission to invent a value."
        ) from exc


def category_of(key: str) -> str:
    """ISO category for a settings key (raises on unknown — fail-closed)."""
    if key not in TUNABLES:
        raise ImproperlyConfigured(
            f"{key} is not a registered SomaFractalMemory tunable. "
            "VIBE Rule 91: an unregistered key is a programming error, not a new default."
        )
    return TUNABLES[key].category


def schema_default(key: str) -> Any:
    """The schema default declared for ``key``. Raises when the key is required."""
    if key not in TUNABLES:
        raise ImproperlyConfigured(
            f"{key} is not a registered SomaFractalMemory tunable. "
            "VIBE Rule 91: an unregistered key is a programming error, not a new default."
        )
    default = TUNABLES[key].default
    if isinstance(default, _Required):
        raise ImproperlyConfigured(
            f"{key} has no schema default and is not set. "
            "VIBE Rule 91: there is no default for this value — the deployment must name it."
        )
    return default


def resolve_setting(key: str, *, default: Any = _UNSET) -> Any:
    """Resolve one tunable: Django settings → schema default (or caller default).

    Args:
        key: Registered tunable name (must be in ``TUNABLES``).
        default: Optional caller-supplied fallback used only when the tunable
            itself declares ``REQUIRED`` and Django settings is absent. Passing
            this is legal only for values the caller genuinely treats as
            optional (e.g. a URL for a gate that is not deployed).

    Returns:
        The resolved value, coerced to the tunable's kind.

    Raises:
        ImproperlyConfigured: unknown key, unparseable value, or a required
            tunable that is absent with no caller default (Rule 91 fail-closed).
    """
    if key not in TUNABLES:
        raise ImproperlyConfigured(
            f"{key} is not a registered SomaFractalMemory tunable. "
            "VIBE Rule 91: an unregistered key is a programming error, not a new default."
        )
    tunable = TUNABLES[key]

    value = _from_django(key)
    if value is not None:
        return _coerce(key, tunable.kind, value)

    if not isinstance(tunable.default, _Required):
        return tunable.default

    if not isinstance(default, _Unset):
        return default

    raise ImproperlyConfigured(
        f"{key} is not set ({tunable.description}). "
        "VIBE Rule 91: there is no default for this value — the deployment must name it."
    )


def resolve_optional(key: str) -> Any:
    """Resolve a tunable that may legitimately be absent. Returns None when absent."""
    if key not in TUNABLES:
        raise ImproperlyConfigured(
            f"{key} is not a registered SomaFractalMemory tunable. "
            "VIBE Rule 91: an unregistered key is a programming error, not a new default."
        )
    tunable = TUNABLES[key]
    value = _from_django(key)
    if value is not None:
        return _coerce(key, tunable.kind, value)
    if isinstance(tunable.default, _Required):
        return None
    return tunable.default


def service_url(key: str) -> str:
    """Resolve a deployment URL. No URL may be named in logic.

    The URL is taken from Django settings (deployment authority). There is no
    code default: a URL a caller invents is a URL an operator cannot change and
    a reviewer cannot see.

    Raises:
        ImproperlyConfigured: the key is unregistered, absent, or not an
            absolute ``http``/``https`` URL.
    """
    raw = resolve_setting(key, default=None)
    if not raw:
        raise ImproperlyConfigured(
            f"{key} is not configured. "
            "VIBE Rule 91: no deployment URL has a code default. Name it in the deployment."
        )
    parsed = urlparse(str(raw))
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ImproperlyConfigured(
            f"{key} must be an absolute http(s) URL, got {raw!r}. "
            "A host without a scheme is not a service URL."
        )
    return str(raw)


def milvus_uri() -> str:
    """Build the Milvus URI from registered topology. The only place that knows how.

    Host and port are administrable (``SOMA_MILVUS_HOST`` / ``SOMA_MILVUS_PORT``).
    The URI scheme is assembled here once so no call site names a URL.

    Raises:
        ImproperlyConfigured: Milvus topology is not configured.
    """
    host = resolve_optional("SOMA_MILVUS_HOST")
    port = resolve_optional("SOMA_MILVUS_PORT")
    if not host or not port:
        raise ImproperlyConfigured(
            "SOMA_MILVUS_HOST/SOMA_MILVUS_PORT is not configured. "
            "VIBE Rule 91: the vector store URI is built from named topology, never guessed."
        )
    return f"http://{host}:{port}"


class SfmSettings:
    """Typed view over the resolved tunables (the settings model).

    Attribute names are the registered keys without the ``SOMA_`` prefix,
    lowercased. Construction resolves every key through :func:`resolve_setting`
    so the model can never hold a value the registry does not know.
    """

    def __init__(self) -> None:
        for key, tunable in TUNABLES.items():
            attr = key.removeprefix("SOMA_").lower()
            if isinstance(tunable.default, _Required):
                object.__setattr__(self, attr, resolve_optional(key))
            else:
                object.__setattr__(self, attr, resolve_setting(key))

    def __getattr__(self, name: str) -> Any:
        raise AttributeError(
            f"unknown SfmSettings attribute {name!r}; registered keys are "
            f"{sorted(k.removeprefix('SOMA_').lower() for k in TUNABLES)}"
        )

    def as_dict(self) -> dict[str, Any]:
        """Flat ``SOMA_*`` -> resolved value map (for admin surfaces and tests)."""
        return {key: getattr(self, key.removeprefix("SOMA_").lower()) for key in TUNABLES}


def sfm_settings() -> SfmSettings:
    """Build a fresh typed view of the current resolved settings."""
    return SfmSettings()


__all__ = [
    "CATEGORIES",
    "CATEGORY_API",
    "CATEGORY_BACKUP",
    "CATEGORY_INFRA",
    "CATEGORY_MEMORY",
    "CATEGORY_OBSERVABILITY",
    "CATEGORY_SECURITY",
    "KEY_CATEGORY",
    "REQUIRED",
    "SfmSettings",
    "TUNABLES",
    "Tunable",
    "category_of",
    "milvus_uri",
    "resolve_optional",
    "resolve_setting",
    "schema_default",
    "service_url",
    "sfm_settings",
]
