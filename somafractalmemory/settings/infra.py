import os
from pathlib import Path

# -----------------------------------------------------------------------------
# Vault Secrets Injection (Runtime Only)
# -----------------------------------------------------------------------------
try:
    # Vault client import placeholder
    pass
except ImportError:
    pass

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
# OPA Configuration
# -----------------------------------------------------------------------------
SOMA_OPA_URL = os.environ.get("SOMA_OPA_URL", "http://opa:8181")
SOMA_OPA_TIMEOUT = float(os.environ.get("SOMA_OPA_TIMEOUT", "1.0"))
SOMA_OPA_FAIL_OPEN = os.environ.get("SOMA_OPA_FAIL_OPEN", "false").lower() in ("true", "1", "yes")


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
