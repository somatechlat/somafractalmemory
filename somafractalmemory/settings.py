"""Django settings for SomaFractalMemory.

100% Django-compliant configuration module.
All settings are centralized here following Django patterns.
Environment variables use SOMA_ prefix for consistency with existing infrastructure.

VIBE Compliance:
- NO hardcoded values (all from environment)
- Centralized configuration (Django settings pattern)
- Production-grade security defaults
"""

import os
from pathlib import Path

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------------------------------------------------------------
# Security Settings
# -----------------------------------------------------------------------------
SECRET_KEY = os.environ.get("SOMA_SECRET_KEY") or os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SOMA_SECRET_KEY or DJANGO_SECRET_KEY must be set")
DEBUG = os.environ.get("SOMA_DEBUG", "false").lower() in ("true", "1", "yes")
ALLOWED_HOSTS_STR = os.environ.get("SOMA_ALLOWED_HOSTS")
if not ALLOWED_HOSTS_STR:
    raise ValueError("SOMA_ALLOWED_HOSTS must be set")
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
    "somafractalmemory.saas",  # SaaS: API keys, usage tracking
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    # CORS handled via custom middleware or django-cors-headers if installed
    # SaaS Usage Tracking (billing)
    "somafractalmemory.saas.middleware.UsageTrackingMiddleware",
]

ROOT_URLCONF = "somafractalmemory.urls"

# -----------------------------------------------------------------------------
# Database Configuration (PostgreSQL)
# -----------------------------------------------------------------------------

# Primary database for Django ORM (not used by SomaFractalMemory stores directly)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("SOMA_DB_NAME"),
        "USER": os.environ.get("SOMA_DB_USER"),
        "PASSWORD": os.environ.get("SOMA_DB_PASSWORD"),
        "HOST": os.environ.get("SOMA_DB_HOST"),
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
# Redis Configuration
# -----------------------------------------------------------------------------
SOMA_REDIS_HOST = os.environ.get("SOMA_REDIS_HOST")
SOMA_REDIS_PORT = os.environ.get("SOMA_REDIS_PORT")
SOMA_REDIS_DB = os.environ.get("SOMA_REDIS_DB", "0")
SOMA_REDIS_PASSWORD = os.environ.get("SOMA_REDIS_PASSWORD")

# -----------------------------------------------------------------------------
# Milvus Vector Store Configuration
# -----------------------------------------------------------------------------
SOMA_MILVUS_HOST = os.environ.get("SOMA_MILVUS_HOST")
SOMA_MILVUS_PORT = os.environ.get("SOMA_MILVUS_PORT")

# -----------------------------------------------------------------------------
# Memory System Configuration
# -----------------------------------------------------------------------------
SOMA_NAMESPACE = os.environ.get("SOMA_NAMESPACE", "default")
SOMA_MEMORY_NAMESPACE = os.environ.get("SOMA_MEMORY_NAMESPACE", "api_ns")
SOMA_MEMORY_MODE = os.environ.get("SOMA_MEMORY_MODE", "evented_enterprise")
SOMA_MODEL_NAME = os.environ.get("SOMA_MODEL_NAME", "microsoft/codebert-base")
SOMA_VECTOR_DIM = int(os.environ.get("SOMA_VECTOR_DIM", "768"))
SOMA_MAX_MEMORY_SIZE = int(os.environ.get("SOMA_MAX_MEMORY_SIZE", "100000"))
SOMA_PRUNING_INTERVAL_SECONDS = int(os.environ.get("SOMA_PRUNING_INTERVAL_SECONDS", "600"))

# Embedding configuration
SOMA_FORCE_HASH_EMBEDDINGS = os.environ.get("SOMA_FORCE_HASH_EMBEDDINGS", "false").lower() in (
    "true",
    "1",
    "yes",
)

# Hybrid search configuration
SOMA_HYBRID_RECALL_DEFAULT = os.environ.get("SOMA_HYBRID_RECALL_DEFAULT", "true").lower() in (
    "true",
    "1",
    "yes",
)
SOMA_HYBRID_BOOST = float(os.environ.get("SOMA_HYBRID_BOOST", "2.0"))
SOMA_HYBRID_CANDIDATE_MULTIPLIER = float(os.environ.get("SOMA_HYBRID_CANDIDATE_MULTIPLIER", "4.0"))

# Similarity configuration
SOMA_SIMILARITY_METRIC = os.environ.get("SOMA_SIMILARITY_METRIC", "cosine")
SOMA_SIMILARITY_ALLOW_NEGATIVE = os.environ.get(
    "SOMA_SIMILARITY_ALLOW_NEGATIVE", "false"
).lower() in ("true", "1", "yes")

# -----------------------------------------------------------------------------
# API Configuration
# -----------------------------------------------------------------------------
SOMA_API_PORT = int(os.environ.get("SOMA_API_PORT", "10101"))
SOMA_LOG_LEVEL = os.environ.get("SOMA_LOG_LEVEL", "INFO")
SOMA_MAX_REQUEST_BODY_MB = float(os.environ.get("SOMA_MAX_REQUEST_BODY_MB", "5.0"))

# Rate limiting
SOMA_RATE_LIMIT_MAX = int(os.environ.get("SOMA_RATE_LIMIT_MAX", "60"))
SOMA_RATE_LIMIT_WINDOW = float(os.environ.get("SOMA_RATE_LIMIT_WINDOW", "60.0"))

# CORS
SOMA_CORS_ORIGINS = os.environ.get("SOMA_CORS_ORIGINS", "")

# -----------------------------------------------------------------------------
# Importance Normalization Parameters
# -----------------------------------------------------------------------------
SOMA_IMPORTANCE_RESERVOIR_MAX = int(os.environ.get("SOMA_IMPORTANCE_RESERVOIR_MAX", "512"))
SOMA_IMPORTANCE_RECOMPUTE_STRIDE = int(os.environ.get("SOMA_IMPORTANCE_RECOMPUTE_STRIDE", "64"))
SOMA_IMPORTANCE_WINSOR_DELTA = float(os.environ.get("SOMA_IMPORTANCE_WINSOR_DELTA", "0.25"))
SOMA_IMPORTANCE_LOGISTIC_TARGET_RATIO = float(
    os.environ.get("SOMA_IMPORTANCE_LOGISTIC_TARGET_RATIO", "9.0")
)
SOMA_IMPORTANCE_LOGISTIC_K_MAX = float(os.environ.get("SOMA_IMPORTANCE_LOGISTIC_K_MAX", "25.0"))

# -----------------------------------------------------------------------------
# Decay Configuration
# -----------------------------------------------------------------------------
SOMA_DECAY_AGE_HOURS_WEIGHT = float(os.environ.get("SOMA_DECAY_AGE_HOURS_WEIGHT", "1.0"))
SOMA_DECAY_RECENCY_HOURS_WEIGHT = float(os.environ.get("SOMA_DECAY_RECENCY_HOURS_WEIGHT", "1.0"))
SOMA_DECAY_ACCESS_WEIGHT = float(os.environ.get("SOMA_DECAY_ACCESS_WEIGHT", "0.5"))
SOMA_DECAY_IMPORTANCE_WEIGHT = float(os.environ.get("SOMA_DECAY_IMPORTANCE_WEIGHT", "2.0"))
SOMA_DECAY_THRESHOLD = float(os.environ.get("SOMA_DECAY_THRESHOLD", "2.0"))

# -----------------------------------------------------------------------------
# Batch Processing Configuration
# -----------------------------------------------------------------------------
SOMA_ENABLE_BATCH_UPSERT = os.environ.get("SOMA_ENABLE_BATCH_UPSERT", "false").lower() in (
    "true",
    "1",
    "yes",
)
SOMA_BATCH_SIZE = int(os.environ.get("SOMA_BATCH_SIZE", "1"))
SOMA_BATCH_FLUSH_MS = int(os.environ.get("SOMA_BATCH_FLUSH_MS", "0"))

# -----------------------------------------------------------------------------
# Feature Flags
# -----------------------------------------------------------------------------
SOMA_ASYNC_METRICS_ENABLED = os.environ.get("SOMA_ASYNC_METRICS_ENABLED", "false").lower() in (
    "true",
    "1",
    "yes",
)
SOMA_FAST_CORE_ENABLED = os.environ.get("SFM_FAST_CORE", "false").lower() in ("true", "1", "yes")
SOMA_FAST_CORE_INITIAL_CAPACITY = int(os.environ.get("SOMA_FAST_CORE_INITIAL_CAPACITY", "1024"))

# -----------------------------------------------------------------------------
# JWT Authentication (Optional)
# -----------------------------------------------------------------------------
SOMA_JWT_ENABLED = os.environ.get("SOMA_JWT_ENABLED", "false").lower() in ("true", "1", "yes")
SOMA_JWT_ISSUER = os.environ.get("SOMA_JWT_ISSUER", "")
SOMA_JWT_AUDIENCE = os.environ.get("SOMA_JWT_AUDIENCE", "")
SOMA_JWT_SECRET = os.environ.get("SOMA_JWT_SECRET", "")
SOMA_JWT_PUBLIC_KEY = os.environ.get("SOMA_JWT_PUBLIC_KEY", "")

# -----------------------------------------------------------------------------
# External Services (Vault, Langfuse, etc.)
# -----------------------------------------------------------------------------
SOMA_VAULT_URL = os.environ.get("SOMA_VAULT_URL", "")
SOMA_SECRETS_PATH = os.environ.get("SOMA_SECRETS_PATH", "")

SOMA_LANGFUSE_PUBLIC = os.environ.get("SOMA_LANGFUSE_PUBLIC", "")
SOMA_LANGFUSE_SECRET = os.environ.get("SOMA_LANGFUSE_SECRET", "")
SOMA_LANGFUSE_HOST = os.environ.get("SOMA_LANGFUSE_HOST", "")

# -----------------------------------------------------------------------------
# Circuit Breaker Configuration
# -----------------------------------------------------------------------------
SOMA_CIRCUIT_FAILURE_THRESHOLD = int(os.environ.get("SOMA_CIRCUIT_FAILURE_THRESHOLD", "3"))
SOMA_CIRCUIT_RESET_INTERVAL = float(os.environ.get("SOMA_CIRCUIT_RESET_INTERVAL", "60.0"))
SOMA_CIRCUIT_COOLDOWN_INTERVAL = float(os.environ.get("SOMA_CIRCUIT_COOLDOWN_INTERVAL", "0.0"))

# -----------------------------------------------------------------------------
# Data Directories
# -----------------------------------------------------------------------------
SOMA_BACKUP_DIR = Path(os.environ.get("SOMA_BACKUP_DIR", "./backups"))
SOMA_MEMORY_DATA_DIR = Path(os.environ.get("SOMA_MEMORY_DATA_DIR", "./data"))
SOMA_S3_BUCKET = os.environ.get("SOMA_S3_BUCKET", "")
SOMA_SERIALIZER = os.environ.get("SOMA_SERIALIZER", "json")

# Test namespace
SOMA_TEST_MEMORY_NAMESPACE = os.environ.get("SOMA_TEST_MEMORY_NAMESPACE", "test_ns")

# -----------------------------------------------------------------------------
# Internationalization
# -----------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = True

# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": SOMA_LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "somafractalmemory": {
            "handlers": ["console"],
            "level": SOMA_LOG_LEVEL,
            "propagate": False,
        },
    },
}

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
