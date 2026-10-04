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
1. Vault — the system of record (Rule 164). When Vault topology is present,
   a Vault failure raises. It never falls through to ENV.
2. The deployment's secret injection (compose ``*_FILE`` / k8s
   ``secretKeyRef``), presented as environment variables at process start —
   only when this deployment has no Vault at all.

This module reads them **once**, holds them in memory and never writes them
back into ``os.environ``. Writing a secret into the process environment is how
it leaks through ``ps`` and ``/proc/*/environ``.

``env.str(name, default=None)`` is not a fallback here: ``default=None`` means
"absent", and ``_credential`` is the only place that decides what absent means.
It raises.
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


def _credential(what: str, *names: str, vault: tuple[str, str] | None = None) -> str:
    """Resolve one required secret. Vault first, then the deployment's injection.

    Args:
        what: Human name used in the error, e.g. ``"Django SECRET_KEY"``.
        *names: Environment variable names, in priority order.
        vault: Optional ``(path, key)`` in Vault. When Vault topology is present
            it is the source of record and any lookup failure raises. Only when
            the deployment has no Vault at all does the injection channel below
            apply (compose ``*_FILE`` / k8s ``secretKeyRef``).

    Returns:
        The resolved value. Never empty.

    Raises:
        ImproperlyConfigured: if every source is absent or empty, or if Vault
            was consulted and failed. That is the Rule 91 failure mode -- the
            process must not boot on a guess, and a swallowed Vault error is a
            bypass (Rule 164).
    """
    if vault is not None:
        try:
            from somafractalmemory.admin.core.security.vault_client import (
                get_secret,
                vault_topology_present,
            )

            if vault_topology_present():
                value = get_secret(vault[0], vault[1])
                if value:
                    return str(value)
                raise ImproperlyConfigured(
                    f"{what}: Vault returned an empty secret at "
                    f"vault:{vault[0]}[{vault[1]}]. VIBE Rule 91: an empty "
                    f"secret is not permission to invent a value."
                )
            # No Vault topology at all: fall through to the deployment's
            # injection channel -- not to a code default.
        except ImportError as exc:
            raise ImproperlyConfigured(
                f"{what}: Vault client is not importable ({exc}). Rule 164 -- secrets "
                f"come from Vault; a missing client is a deployment error, not a "
                f"licence to invent a value."
            ) from exc
        except ImproperlyConfigured:
            # VaultNotConfigured / VaultAuthError / SecretNotFound already say
            # what failed. Do not swallow them into an ENV fallback.
            raise
        except Exception as exc:
            raise ImproperlyConfigured(
                f"{what}: Vault lookup failed ({exc}). "
                "VIBE Rule 164: a swallowed Vault error is a bypass. Fail closed."
            ) from exc

    for name in names:
        value = env.str(name, default=None)
        if value:
            return value

    sources = list(names)
    if vault is not None:
        sources.insert(0, f"vault:{vault[0]}[{vault[1]}]")
    raise ImproperlyConfigured(
        f"{what} is not set. Tried: {', '.join(sources)}. "
        "VIBE Rule 91: there is no default for a credential. "
        "VIBE Rule 164: provide it from Vault, or via the deployment's secret injection."
    )


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
    """Load one topology tunable: env override onto the schema default.

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
    "SOMA_SECRET_KEY",
    "DJANGO_SECRET_KEY",
    vault=("somafractalmemory/credentials", "soma_secret_key"),
)

DEBUG = env.bool("SOMA_DEBUG", default=False)

ALLOWED_HOSTS = _required_list("ALLOWED_HOSTS", "SOMA_ALLOWED_HOSTS")

# API Authentication Token
# Standardized to support SOMA_API_TOKEN or SOMA_API_TOKEN_FILE via environ's support
# But we'll use explicit logic to be safe and match patterns
SOMA_API_TOKEN = env.str("SOMA_API_TOKEN", default=None)
SOMA_API_TOKEN_FILE = env.str("SOMA_API_TOKEN_FILE", default=None)

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
            "SOMA_DB_USER",
            vault=("somafractalmemory/database", "username"),
        ),
        "PASSWORD": _credential(
            "database password",
            "SOMA_DB_PASSWORD",
            vault=("somafractalmemory/database", "password"),
        ),
        "HOST": _read_setting("SOMA_DB_HOST"),
        "PORT": _read_setting("SOMA_DB_PORT"),
    }
}

# PostgreSQL SSL/TLS options. Absent means plain TCP — a real topology for a
# private network. When present they are applied to the ORM connection, not
# merely declared.
SOMA_POSTGRES_SSL_MODE = env.str("SOMA_POSTGRES_SSL_MODE", default=None)
SOMA_POSTGRES_SSL_ROOT_CERT = env.str("SOMA_POSTGRES_SSL_ROOT_CERT", default=None)
SOMA_POSTGRES_SSL_CERT = env.str("SOMA_POSTGRES_SSL_CERT", default=None)
SOMA_POSTGRES_SSL_KEY = env.str("SOMA_POSTGRES_SSL_KEY", default=None)

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
def get_api_token() -> str | None:
    """Load the API token from settings or file.

    Returns ``None`` when neither source is configured -- that is a real
    state (auth is not enabled for this deployment), not a swallowed error.
    A file that is configured but cannot be read is a deployment error and
    raises rather than quietly disabling authentication.
    """
    if SOMA_API_TOKEN:
        return SOMA_API_TOKEN

    if SOMA_API_TOKEN_FILE:
        p = Path(SOMA_API_TOKEN_FILE)
        if not p.exists():
            raise ImproperlyConfigured(
                f"SOMA_API_TOKEN_FILE points at {p}, which does not exist. "
                "VIBE Rule 91: an unreadable credential is not 'no credential'."
            )
        return p.read_text(encoding="utf-8").strip()

    return None
