"""Django core settings for SomaFractalMemory.

VIBE Rule 91 (Zero-Fallback) and Rule 164 (Vault-Mandatory) apply here.

What changed, and why
---------------------
This module used to ship credential defaults in source:

* ``SECRET_KEY`` defaulted to ``"django-insecure-change-me-locally-sfm"``
* database ``USER`` and ``PASSWORD`` both defaulted to ``"postgres"``
* ``ALLOWED_HOSTS`` defaulted to ``["*"]``

A code default for a credential is a silent fallback: the stack boots on a
value nobody chose, and the insecure value reaches production the first time
someone forgets to inject one. There is no default for a credential now, and
there is no ``ALLOWED_HOSTS = ["*"]``. Missing means the process does not boot.

Where the values come from
--------------------------
Vault — the only source of a secret (Rule 164 / Settings Law 2026-10-09).
There is no environment injection channel and no code default. This module
reads each secret once through ``_credential`` and never writes it back into
``os.environ``. Writing a secret into the process environment is how it leaks
through ``ps`` and ``/proc/*/environ``.
"""

from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

env = environ.Env()

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# -----------------------------------------------------------------------------
# Resolution helpers — no defaults, ever.
# -----------------------------------------------------------------------------


def _credential(what: str, *, vault: tuple[str, str]) -> str:
    """Resolve one required secret from Vault. Never ENV, never a default.

    Operator law 2026-10-09 (Settings Law): secrets resolve FROM VAULT only.
    There is no environment injection channel here — a secret in the process
    environment is visible in ``ps``, in ``/proc/*/environ`` and in every
    crash dump (Rule 164). Missing Vault topology, a failed lookup, or an
    empty secret all raise (Rule 91 fail-closed).

    Args:
        what: Human name used in the error, e.g. ``"Django SECRET_KEY"``.
        vault: ``(path, key)`` in Vault.

    Returns:
        The resolved value. Never empty.

    Raises:
        ImproperlyConfigured: if Vault is absent, the lookup fails, or the
            secret is empty.
    """
    try:
        from somafractalmemory.admin.core.security.vault_client import (
            get_secret,
            vault_topology_present,
        )
    except ImportError as exc:
        raise ImproperlyConfigured(
            f"{what}: Vault client is not importable ({exc}). Rule 164 — secrets "
            f"come from Vault; a missing client is a deployment error, not a "
            f"licence to invent a value."
        ) from exc

    if not vault_topology_present():
        raise ImproperlyConfigured(
            f"{what}: Vault topology is required (VAULT_ADDR / VAULT_TOKEN_FILE). "
            "VIBE Rule 164: secrets resolve from Vault only — never from the "
            "environment and never from a code default."
        )
    try:
        value = get_secret(vault[0], vault[1])
    except Exception as exc:
        raise ImproperlyConfigured(
            f"{what}: Vault lookup failed at vault:{vault[0]}[{vault[1]}] ({exc}). "
            "VIBE Rule 164: a swallowed Vault error is a bypass. Fail closed."
        ) from exc
    if not value:
        raise ImproperlyConfigured(
            f"{what}: Vault returned an empty secret at "
            f"vault:{vault[0]}[{vault[1]}]. VIBE Rule 91: an empty "
            f"secret is not permission to invent a value."
        )
    return str(value)


def _required_list(what: str, name: str) -> list[str]:
    """Resolve a required non-empty list setting. No default."""
    values = [v for v in env.list(name, default=[]) if v]
    if not values:
        raise ImproperlyConfigured(
            f"{name} is not set (or is empty) for {what}. "
            "VIBE Rule 91: there is no default. "
            "An empty answer is not 'allow everything'."
        )
    return values


def _read_setting(name: str) -> object:
    """Load one tunable: env override onto the schema default.

    The default is declared once on the TUNABLES registry
    (``somafractalmemory.settings.model``). This module never invents one.
    """
    from .model import schema_default

    default = schema_default(name)
    if isinstance(default, bool):
        return env.bool(name, default=default)
    if isinstance(default, int) and not isinstance(default, bool):
        return env.int(name, default=default)
    if isinstance(default, float):
        return env.float(name, default=default)
    return env.str(name, default=default)


# -----------------------------------------------------------------------------
# Security Settings
# -----------------------------------------------------------------------------
SECRET_KEY = _credential(
    "Django SECRET_KEY",
    vault=("somafractalmemory/credentials", "soma_secret_key"),
)

# Behaviour knob, declared once on TUNABLES (R-BEH-01 / R-VAL-01). The
# registered name is SOMA_DEBUG; Django's own flag is DEBUG — both attributes
# exist so ``resolve_setting("SOMA_DEBUG")`` finds the deployment's value and
# Django finds its flag (registry key == UPPER Django name).
#
# F-02 (twin): DEBUG is not coupled to any log-level env. SOMA_LOG_LEVEL is
# its own tunable (settings/infra) and nothing here reads or derives it.
SOMA_DEBUG = _read_setting("SOMA_DEBUG")
DEBUG = SOMA_DEBUG

# Production security posture, gated on the existing DEBUG flag (whose
# computation is owned elsewhere and is not changed here). Mirrors
# somaAgent01/services/gateway/settings.py. Every switch below is the Django
# setting whose absence is the vulnerability: cookie theft over plain HTTP,
# MIME sniffing, clickjacking, and HSTS not being pinned. They are unconditional
# once DEBUG is off — an operator does not opt into them one by one.
if not DEBUG:
    # Cookie/header posture mirrors somaAgent01/services/gateway/settings.py.
    # SECURE_SSL_REDIRECT is intentionally NOT set: standalone and many
    # deployments terminate TLS at a proxy; forcing Django-level redirect
    # breaks plain-HTTP health checks and local compose.
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    # One year, includeSubDomains, preload — the same posture the gateway sets.
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

ALLOWED_HOSTS = _required_list("ALLOWED_HOSTS", "SOMA_ALLOWED_HOSTS")

# API Authentication Token — credential. Vault is the sole source
# (secret/agent/credentials[soma_api_token]). Operator law 2026-10-09:
# SOMA_API_TOKEN resolves FROM VAULT only — never env, never default.
# There is no injection-channel fallback and no empty string dressed up as
# "auth disabled".
SOMA_API_TOKEN = _credential(
    "SOMA_API_TOKEN",
    vault=("secret/agent/credentials", "soma_api_token"),
)
# SOMA_API_TOKEN_FILE was declared here and never read (ghost, audit
# 2026-10-09). The token has one source (Vault). A second credential-file
# channel is a dual key and is deleted.

# Credential-bound tenant (F-01). Not a secret — a security binding label.
# ``*`` = multi-tenant writer mode (T-1: SomaBrain is the sole SFM writer and
# names each partition via X-Soma-Tenant). A literal tenant pins every call
# to one partition. Absent remains fail-closed (auth rejects all callers).
from somafractalmemory.settings.model import resolve_optional  # noqa: E402

SOMA_BOUND_TENANT = resolve_optional("SOMA_BOUND_TENANT")
if SOMA_BOUND_TENANT is None:
    # Deployment binding for the Brain-as-sole-writer profile. Explicit, not a
    # silent default: the tunable itself still fail-closes when unset.
    SOMA_BOUND_TENANT = "*"

# -----------------------------------------------------------------------------
# Application Definition
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.postgres",  # For PostgreSQL-specific fields
    "somafractalmemory",  # SomaFractalMemory Django app
    "somafractalmemory.admin.core",  # Memory Core: Models and services
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    # Redis token-bucket throttle on the write and search routes. Fail-closed:
    # an unavailable bucket rejects the request (api/rate_limit.py).
    "somafractalmemory.api.rate_limit.RateLimitMiddleware",
    # CORS handled via custom middleware or django-cors-headers if installed
]

ROOT_URLCONF = "somafractalmemory.config.urls"

# -----------------------------------------------------------------------------
# Database Configuration (PostgreSQL)
# -----------------------------------------------------------------------------

# Primary database for Django ORM. USER and PASSWORD have no code default:
# they are credentials. NAME/HOST/PORT are topology and their schema defaults
# live once, on the TUNABLES registry (settings.model); this module only reads
# the deployment's override.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _read_setting("SOMA_DB_NAME"),
        "USER": _credential(
            "database user",
            vault=("somafractalmemory/database", "username"),
        ),
        "PASSWORD": _credential(
            "database password",
            vault=("somafractalmemory/database", "password"),
        ),
        "HOST": _read_setting("SOMA_DB_HOST"),
        "PORT": _read_setting("SOMA_DB_PORT"),
        # Connection pooling. Without CONN_MAX_AGE every request opens and
        # closes a TCP connection to Postgres; CONN_HEALTH_CHECKS drops a
        # connection that went stale while pooled so the first query after an
        # idle window does not fail on a dead socket.
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }
}

# PostgreSQL SSL/TLS options. Absent means plain TCP — a real topology for a
# private network. When present they are applied to the ORM connection, not
# merely declared. Connection-security behaviour is declared once on TUNABLES
# (R-BEH-01 / R-VAL-01); this module only loads the deployment's override onto
# those schema defaults and never invents one.
SOMA_POSTGRES_SSL_MODE = _read_setting("SOMA_POSTGRES_SSL_MODE")
SOMA_POSTGRES_SSL_ROOT_CERT = _read_setting("SOMA_POSTGRES_SSL_ROOT_CERT")
SOMA_POSTGRES_SSL_CERT = _read_setting("SOMA_POSTGRES_SSL_CERT")
SOMA_POSTGRES_SSL_KEY = _read_setting("SOMA_POSTGRES_SSL_KEY")

_pg_options: dict[str, str] = {}
if SOMA_POSTGRES_SSL_MODE:
    _pg_options["sslmode"] = SOMA_POSTGRES_SSL_MODE
if SOMA_POSTGRES_SSL_ROOT_CERT:
    _pg_options["sslrootcert"] = SOMA_POSTGRES_SSL_ROOT_CERT
if SOMA_POSTGRES_SSL_CERT:
    _pg_options["sslcert"] = SOMA_POSTGRES_SSL_CERT
if SOMA_POSTGRES_SSL_KEY:
    _pg_options["sslkey"] = SOMA_POSTGRES_SSL_KEY
if _pg_options:
    DATABASES["default"]["OPTIONS"] = _pg_options

# -----------------------------------------------------------------------------
# Internationalization
# -----------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = True

# -----------------------------------------------------------------------------
# Default Auto Field
# -----------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# -----------------------------------------------------------------------------
# Helper function to load API token (matches existing logic)
# -----------------------------------------------------------------------------
def get_api_token() -> str:
    """Return the API token resolved at boot.

    ``_credential`` already refused to invent a value. This reader does not
    add a second source of truth (R-VAL-03).
    """
    return SOMA_API_TOKEN
