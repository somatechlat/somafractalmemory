import os
from pathlib import Path

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# -----------------------------------------------------------------------------
# Security Settings
# -----------------------------------------------------------------------------
SECRET_KEY = os.environ.get("SOMA_SECRET_KEY") or os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    # Default for dev/build to prevent crashes, but warn in prod
    SECRET_KEY = "django-insecure-change-me-locally-sfm"

DEBUG = os.environ.get("SOMA_DEBUG", "false").lower() in ("true", "1", "yes")

ALLOWED_HOSTS_STR = os.environ.get("SOMA_ALLOWED_HOSTS")
if not ALLOWED_HOSTS_STR:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS_STR.split(",") if h.strip()]

# API Authentication Token
SOMA_API_TOKEN = os.environ.get("SOMA_API_TOKEN")
SOMA_API_TOKEN_FILE = os.environ.get("SOMA_API_TOKEN_FILE")

# -----------------------------------------------------------------------------
# Application Definition
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.postgres",  # For PostgreSQL-specific fields
    "somafractalmemory",  # SomaFractalMemory Django app
    "somafractalmemory.apps.aaas",  # AAAS: API keys, usage tracking - UPDATED PATH
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    # CORS handled via custom middleware or django-cors-headers if installed
    # AAAS Usage Tracking (billing)
    "somafractalmemory.apps.aaas.middleware.UsageTrackingMiddleware",
]

ROOT_URLCONF = "somafractalmemory.config.urls"

# -----------------------------------------------------------------------------
# Database Configuration (PostgreSQL)
# -----------------------------------------------------------------------------

# Primary database for Django ORM
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("SOMA_DB_NAME", "somafractalmemory"),
        "USER": os.environ.get("SOMA_DB_USER", "postgres"),
        "PASSWORD": os.environ.get("SOMA_DB_PASSWORD", "postgres"),
        "HOST": os.environ.get("SOMA_DB_HOST", "localhost"),
        "PORT": os.environ.get("SOMA_DB_PORT", "5432"),
    }
}

# Legacy DSN format (for backwards compatibility with existing stores)
SOMA_POSTGRES_URL = os.environ.get(
    "SOMA_POSTGRES_URL",
    os.environ.get(
        "POSTGRES_URL",
        f"postgresql://{DATABASES['default']['USER']}:{DATABASES['default']['PASSWORD']}@"
        f"{DATABASES['default']['HOST']}:{DATABASES['default']['PORT']}/{DATABASES['default']['NAME']}",
    ),
)

# PostgreSQL SSL/TLS options
SOMA_POSTGRES_SSL_MODE = os.environ.get("SOMA_POSTGRES_SSL_MODE")
SOMA_POSTGRES_SSL_ROOT_CERT = os.environ.get("SOMA_POSTGRES_SSL_ROOT_CERT")
SOMA_POSTGRES_SSL_CERT = os.environ.get("SOMA_POSTGRES_SSL_CERT")
SOMA_POSTGRES_SSL_KEY = os.environ.get("SOMA_POSTGRES_SSL_KEY")

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

    if SOMA_API_TOKEN_FILE and os.path.exists(SOMA_API_TOKEN_FILE):
        try:
            with open(SOMA_API_TOKEN_FILE, encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass

    # Try .env file
    env_paths = [
        BASE_DIR / ".env",
        Path.cwd() / ".env",
    ]
    for env_path in env_paths:
        if env_path.is_file():
            try:
                with env_path.open(encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("SOMA_API_TOKEN="):
                            return line.strip().split("=", 1)[1]
            except Exception:
                continue

    return None
