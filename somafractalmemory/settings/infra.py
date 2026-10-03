"""Infrastructure settings for SomaFractalMemory.

This module used to begin with a Vault bootstrap that fetched database and
Redis credentials and **wrote them into ``os.environ``**. That is a Rule 164
violation dressed as a feature: a secret in the process environment is visible
in ``ps``, ``/proc/*/environ`` and every child process. It was also ordered
wrong -- ``settings/__init__`` imports ``django_core`` before ``infra``, so the
injection ran after the values it was meant to supply had already been read,
and only ``settings.standalone`` compensated for that with an explicit
re-read hack.

Credential resolution now lives in ``django_core._credential``: Vault first,
the deployment's injection channel second, never a code default (Rule 91),
never written back to the environment. This module holds topology and
behaviour knobs only.
"""

from pathlib import Path

import environ

env = environ.Env()

# -----------------------------------------------------------------------------
# Redis Configuration
# -----------------------------------------------------------------------------
SOMA_REDIS_HOST = env.str("SOMA_REDIS_HOST", default=None)
SOMA_REDIS_PORT = env.int("SOMA_REDIS_PORT", default=6379)
SOMA_REDIS_DB = env.str("SOMA_REDIS_DB", default="0")
# Absent (None) is a real topology: a Redis with no AUTH. It is not an empty
# password and it is not a silent fallback -- when this deployment requires
# Redis AUTH, the operator sets SOMA_REDIS_PASSWORD or Vault supplies it.
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
# Vector dimension for stored embeddings (Milvus collections are fixed-dim).
# The agent seam computes embeddings once and sends them precomputed, at
# MEM_EMBED_DIM (default 768). SOMA_VECTOR_DIM overrides when set explicitly;
# otherwise MEM_EMBED_DIM is honoured so both sides share one vector space.
#
# 768 is not arbitrary: it is the hidden size of SOMA_MODEL_NAME
# (microsoft/codebert-base, line 63) and the dim the Milvus collection was
# created at. Lowering it shrinks capacity for no benefit and orphans the
# collection. MEM_EMBED_DIM (agent) must equal SOMA_VECTOR_DIM (here).
SOMA_VECTOR_DIM = env.int("SOMA_VECTOR_DIM", default=env.int("MEM_EMBED_DIM", default=768))
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
SOMA_FAST_CORE_ENABLED = env.bool("SOMA_FAST_CORE_ENABLED", default=False)
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
