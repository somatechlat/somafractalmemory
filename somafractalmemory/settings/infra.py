from pathlib import Path

import environ

env = environ.Env()

# -----------------------------------------------------------------------------
# Vault Secrets Injection (Runtime Only)
# -----------------------------------------------------------------------------
try:
    # Vault client import placeholder for standardization
    pass
except ImportError:
    pass

# -----------------------------------------------------------------------------
# Redis Configuration
# -----------------------------------------------------------------------------
SOMA_REDIS_HOST = env.str("SOMA_REDIS_HOST", default=None)
SOMA_REDIS_PORT = env.int("SOMA_REDIS_PORT", default=6379)
SOMA_REDIS_DB = env.str("SOMA_REDIS_DB", default="0")
SOMA_REDIS_PASSWORD = env.str("SOMA_REDIS_PASSWORD", default=None)

# -----------------------------------------------------------------------------
# Milvus Vector Store Configuration
# -----------------------------------------------------------------------------
SOMA_MILVUS_HOST = env.str("SOMA_MILVUS_HOST", default=None)
SOMA_MILVUS_PORT = env.str("SOMA_MILVUS_PORT", default="19530")

# -----------------------------------------------------------------------------
# Memory System Configuration
# -----------------------------------------------------------------------------
SOMA_NAMESPACE = env.str("SOMA_NAMESPACE", default="default")
SOMA_MEMORY_NAMESPACE = env.str("SOMA_MEMORY_NAMESPACE", default="api_ns")
SOMA_MEMORY_MODE = env.str("SOMA_MEMORY_MODE", default="evented_enterprise")
SOMA_MODEL_NAME = env.str("SOMA_MODEL_NAME", default="microsoft/codebert-base")
SOMA_VECTOR_DIM = env.int("SOMA_VECTOR_DIM", default=768)
SOMA_MAX_MEMORY_SIZE = env.int("SOMA_MAX_MEMORY_SIZE", default=100000)
SOMA_PRUNING_INTERVAL_SECONDS = env.int("SOMA_PRUNING_INTERVAL_SECONDS", default=600)

# Embedding configuration
SOMA_FORCE_HASH_EMBEDDINGS = env.bool("SOMA_FORCE_HASH_EMBEDDINGS", default=False)

# Hybrid search configuration
SOMA_HYBRID_RECALL_DEFAULT = env.bool("SOMA_HYBRID_RECALL_DEFAULT", default=True)
SOMA_HYBRID_BOOST = env.float("SOMA_HYBRID_BOOST", default=2.0)
SOMA_HYBRID_CANDIDATE_MULTIPLIER = env.float("SOMA_HYBRID_CANDIDATE_MULTIPLIER", default=4.0)

# Similarity configuration
SOMA_SIMILARITY_METRIC = env.str("SOMA_SIMILARITY_METRIC", default="cosine")
SOMA_SIMILARITY_ALLOW_NEGATIVE = env.bool("SOMA_SIMILARITY_ALLOW_NEGATIVE", default=False)

# -----------------------------------------------------------------------------
# API Configuration
# -----------------------------------------------------------------------------
SOMA_API_PORT = env.int("SOMA_API_PORT", default=10101)
SOMA_LOG_LEVEL = env.str("SOMA_LOG_LEVEL", default="INFO")
SOMA_MAX_REQUEST_BODY_MB = env.float("SOMA_MAX_REQUEST_BODY_MB", default=5.0)

# Rate limiting
SOMA_RATE_LIMIT_MAX = env.int("SOMA_RATE_LIMIT_MAX", default=60)
SOMA_RATE_LIMIT_WINDOW = env.float("SOMA_RATE_LIMIT_WINDOW", default=60.0)

# CORS
SOMA_CORS_ORIGINS = env.list("SOMA_CORS_ORIGINS", default=[])

# -----------------------------------------------------------------------------
# Importance Normalization Parameters
# -----------------------------------------------------------------------------
SOMA_IMPORTANCE_RESERVOIR_MAX = env.int("SOMA_IMPORTANCE_RESERVOIR_MAX", default=512)
SOMA_IMPORTANCE_RECOMPUTE_STRIDE = env.int("SOMA_IMPORTANCE_RECOMPUTE_STRIDE", default=64)
SOMA_IMPORTANCE_WINSOR_DELTA = env.float("SOMA_IMPORTANCE_WINSOR_DELTA", default=0.25)
SOMA_IMPORTANCE_LOGISTIC_TARGET_RATIO = env.float(
    "SOMA_IMPORTANCE_LOGISTIC_TARGET_RATIO", default=9.0
)
SOMA_IMPORTANCE_LOGISTIC_K_MAX = env.float("SOMA_IMPORTANCE_LOGISTIC_K_MAX", default=25.0)

# -----------------------------------------------------------------------------
# Decay Configuration
# -----------------------------------------------------------------------------
SOMA_DECAY_AGE_HOURS_WEIGHT = env.float("SOMA_DECAY_AGE_HOURS_WEIGHT", default=1.0)
SOMA_DECAY_RECENCY_HOURS_WEIGHT = env.float("SOMA_DECAY_RECENCY_HOURS_WEIGHT", default=1.0)
SOMA_DECAY_ACCESS_WEIGHT = env.float("SOMA_DECAY_ACCESS_WEIGHT", default=0.5)
SOMA_DECAY_IMPORTANCE_WEIGHT = env.float("SOMA_DECAY_IMPORTANCE_WEIGHT", default=2.0)
SOMA_DECAY_THRESHOLD = env.float("SOMA_DECAY_THRESHOLD", default=2.0)

# -----------------------------------------------------------------------------
# Batch Processing Configuration
# -----------------------------------------------------------------------------
SOMA_ENABLE_BATCH_UPSERT = env.bool("SOMA_ENABLE_BATCH_UPSERT", default=False)
SOMA_BATCH_SIZE = env.int("SOMA_BATCH_SIZE", default=1)
SOMA_BATCH_FLUSH_MS = env.int("SOMA_BATCH_FLUSH_MS", default=0)

# -----------------------------------------------------------------------------
# Feature Flags
# -----------------------------------------------------------------------------
SOMA_ASYNC_METRICS_ENABLED = env.bool("SOMA_ASYNC_METRICS_ENABLED", default=False)
SOMA_FAST_CORE_ENABLED = env.bool("SFM_FAST_CORE", default=False)
SOMA_FAST_CORE_INITIAL_CAPACITY = env.int("SOMA_FAST_CORE_INITIAL_CAPACITY", default=1024)

# -----------------------------------------------------------------------------
# JWT Authentication (Optional)
# -----------------------------------------------------------------------------
SOMA_JWT_ENABLED = env.bool("SOMA_JWT_ENABLED", default=False)
SOMA_JWT_ISSUER = env.str("SOMA_JWT_ISSUER", default="")
SOMA_JWT_AUDIENCE = env.str("SOMA_JWT_AUDIENCE", default="")
SOMA_JWT_SECRET = env.str("SOMA_JWT_SECRET", default="")
SOMA_JWT_PUBLIC_KEY = env.str("SOMA_JWT_PUBLIC_KEY", default="")

# -----------------------------------------------------------------------------
# External Services (Vault, Langfuse, etc.)
# -----------------------------------------------------------------------------
SOMA_VAULT_URL = env.str("SOMA_VAULT_URL", default="")
SOMA_SECRETS_PATH = env.str("SOMA_SECRETS_PATH", default="")

SOMA_LANGFUSE_PUBLIC = env.str("SOMA_LANGFUSE_PUBLIC", default="")
SOMA_LANGFUSE_SECRET = env.str("SOMA_LANGFUSE_SECRET", default="")
SOMA_LANGFUSE_HOST = env.str("SOMA_LANGFUSE_HOST", default="")

# -----------------------------------------------------------------------------
# Circuit Breaker Configuration
# -----------------------------------------------------------------------------
SOMA_CIRCUIT_FAILURE_THRESHOLD = env.int("SOMA_CIRCUIT_FAILURE_THRESHOLD", default=3)
SOMA_CIRCUIT_RESET_INTERVAL = env.float("SOMA_CIRCUIT_RESET_INTERVAL", default=60.0)
SOMA_CIRCUIT_COOLDOWN_INTERVAL = env.float("SOMA_CIRCUIT_COOLDOWN_INTERVAL", default=0.0)

# -----------------------------------------------------------------------------
# OPA Configuration
# -----------------------------------------------------------------------------
SOMA_OPA_URL = env.str("SOMA_OPA_URL", default="http://opa:8181")
SOMA_OPA_TIMEOUT = env.float("SOMA_OPA_TIMEOUT", default=1.0)
SOMA_OPA_FAIL_OPEN = env.bool("SOMA_OPA_FAIL_OPEN", default=False)

# -----------------------------------------------------------------------------
# Data Directories
# -----------------------------------------------------------------------------
SOMA_BACKUP_DIR = Path(env.str("SOMA_BACKUP_DIR", default="./backups"))
SOMA_MEMORY_DATA_DIR = Path(env.str("SOMA_MEMORY_DATA_DIR", default="./data"))
SOMA_S3_BUCKET = env.str("SOMA_S3_BUCKET", default="")
SOMA_SERIALIZER = env.str("SOMA_SERIALIZER", default="json")

# Test namespace
SOMA_TEST_MEMORY_NAMESPACE = env.str("SOMA_TEST_MEMORY_NAMESPACE", default="test_ns")

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
