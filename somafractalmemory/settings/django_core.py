from pathlib import Path

import environ

env = environ.Env()

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# -----------------------------------------------------------------------------
# Security Settings
# -----------------------------------------------------------------------------
SECRET_KEY = env.str(
    "SOMA_SECRET_KEY",
    default=env.str("DJANGO_SECRET_KEY", default="django-insecure-change-me-locally-sfm"),
)

DEBUG = env.bool("SOMA_DEBUG", default=False)

ALLOWED_HOSTS = env.list("SOMA_ALLOWED_HOSTS", default=["*"])

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
    "somafractalmemory.admin.aaas",  # AAAS: API keys, usage tracking
    "somafractalmemory.admin.core",  # Memory Core: Models and services
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    # CORS handled via custom middleware or django-cors-headers if installed
    # AAAS Usage Tracking (billing)
    "somafractalmemory.admin.aaas.middleware.UsageTrackingMiddleware",
]

ROOT_URLCONF = "somafractalmemory.config.urls"

# -----------------------------------------------------------------------------
# Database Configuration (PostgreSQL)
# -----------------------------------------------------------------------------

# Primary database for Django ORM
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env.str("SOMA_DB_NAME", default="somafractalmemory"),
        "USER": env.str("SOMA_DB_USER", default="postgres"),
        "PASSWORD": env.str("SOMA_DB_PASSWORD", default="postgres"),
        "HOST": env.str("SOMA_DB_HOST", default="localhost"),
        "PORT": env.str("SOMA_DB_PORT", default="5432"),
    }
}

# Legacy DSN format (for backwards compatibility with existing stores)
SOMA_POSTGRES_URL = env.str(
    "SOMA_POSTGRES_URL",
    default=env.str(
        "POSTGRES_URL",
        default=f"postgresql://{DATABASES['default']['USER']}:{DATABASES['default']['PASSWORD']}@"
        f"{DATABASES['default']['HOST']}:{DATABASES['default']['PORT']}/{DATABASES['default']['NAME']}",
    ),
)

# PostgreSQL SSL/TLS options
SOMA_POSTGRES_SSL_MODE = env.str("SOMA_POSTGRES_SSL_MODE", default=None)
SOMA_POSTGRES_SSL_ROOT_CERT = env.str("SOMA_POSTGRES_SSL_ROOT_CERT", default=None)
SOMA_POSTGRES_SSL_CERT = env.str("SOMA_POSTGRES_SSL_CERT", default=None)
SOMA_POSTGRES_SSL_KEY = env.str("SOMA_POSTGRES_SSL_KEY", default=None)

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
    """Load the API token from settings or file."""
    if SOMA_API_TOKEN:
        return SOMA_API_TOKEN

    if SOMA_API_TOKEN_FILE:
        try:
            p = Path(SOMA_API_TOKEN_FILE)
            if p.exists():
                return p.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    return None
