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
never written back to the environment.

Topology and behaviour knobs
----------------------------
Every tunable is declared **once** on the ``TUNABLES`` registry in
``somafractalmemory.settings.model``. This module loads the deployment's
override (environment) into Django settings using that single schema default —
it never invents a literal of its own. Call sites read through
``resolve_setting`` / ``service_url`` / ``milvus_uri`` and never name a bare
default or a deployment URL.

A tunable with no reader is a lie. The following were deleted because nothing
in this codebase reads them, and inventing a feature just to give a knob a
reader would violate the thin/fast/latency order:

* ``SOMA_MEMORY_MODE`` (``"evented_enterprise"``) — no mode switch exists.
* ``SOMA_MODEL_NAME`` (``"microsoft/codebert-base"``) — embeddings arrive
  precomputed from the agent seam or from HashEmbedder; there is no local
  model loader. The provenance label on ``VectorEmbedding.model_name`` records
  the source (``precomputed`` / ``hash-embedder``), not a HuggingFace id.
* ``SOMA_FORCE_HASH_EMBEDDINGS`` — there is no second embedder to force off.
  The precomputed-embedding contract is the real path; HashEmbedder is the
  documented fallback when no vector is supplied.
* ``SOMA_PRUNING_INTERVAL_SECONDS``, ``SOMA_MAX_MEMORY_SIZE``,
  ``SOMA_DECAY_*`` — there is no decay scorer, no eviction and no prune
  command in this tree. ``Memory.access_count`` / ``last_accessed`` are
  recorded; nothing computes a decay score from them. Scheduling a prune that
  does not exist is a lie.
* ``SOMA_IMPORTANCE_*`` (reservoir / winsor / logistic) — ``Memory.importance``
  is a caller-supplied float used for ordering. There is no normalization
  algorithm to parameterize.
* ``SOMA_HYBRID_RECALL_DEFAULT``, ``SOMA_HYBRID_BOOST``,
  ``SOMA_SIMILARITY_ALLOW_NEGATIVE`` — search ranks vector hits (with
  hash-fallback demotion) and falls back to ORM text search. There is no
  score fusion and no negative-score clamp. The over-fetch factor and the
  hash penalty that *do* exist are ``SOMA_SEARCH_CANDIDATE_MULTIPLIER`` and
  ``SOMA_HASH_EMBEDDING_PENALTY``.
* ``SOMA_ENABLE_BATCH_UPSERT``, ``SOMA_BATCH_SIZE``, ``SOMA_BATCH_FLUSH_MS`` —
  ``store()`` writes one row per call. There is no batch path.
* ``SOMA_JWT_*`` — authentication is the bearer token (``SOMA_API_TOKEN``) via
  ``StandaloneAuth``. JWT is a different auth stack and nothing validated one.
* ``SOMA_LANGFUSE_*`` — tracing is OpenTelemetry (house policy). Nothing spoke
  to Langfuse.
* ``SOMA_FAST_CORE_*``, ``SOMA_ASYNC_METRICS_ENABLED`` — feature flags with no
  feature.
* ``SOMA_SERIALIZER`` — the wire format is JSON (Django/Postgres JSONField).
* ``SOMA_POSTGRES_URL`` — a "legacy DSN" that embedded the password into a
  second settings attribute. Compat aliases and second secret stores are
  prohibited; the ORM reads ``DATABASES``.
* ``SOMA_API_PORT`` — gunicorn/daphne bind where they are told to bind. No
  process in this tree opens a listen socket on a settings value.
* ``SOMA_MAX_REQUEST_BODY_MB``, ``SOMA_RATE_LIMIT_*``, ``SOMA_CORS_ORIGINS`` —
  there is no body-size, rate-limit or CORS middleware in ``MIDDLEWARE``.
  ``api.core.get_rate_limiter`` used to return ``None`` and claim otherwise;
  the stub is gone with the knobs.
* ``SOMA_OPA_*``, ``SOMA_CIRCUIT_*`` — there is no OPA client and no circuit
  breaker in this tree. AuthZ is the bearer token and fail-closed behaviour
  lives where the gate actually is (Vault, dim checks, tenant resolution).
* ``SOMA_SECRETS_PATH`` — Vault paths are named per credential in
  ``django_core._credential``. A generic prefix nothing builds paths from is
  a second, unused secret-addressing scheme.
* ``SOMA_NAMESPACE`` — ``SOMA_MEMORY_NAMESPACE`` is the namespace the API
  operates in; a second label nothing reads is a fork.
"""

from pathlib import Path

import environ

from .model import schema_default

env = environ.Env()


def _read(name: str, default: object) -> object:
    """Read ``name`` from the environment onto the schema default from TUNABLES.

    ``default=None`` is not a fallback for a required credential (those live in
    ``django_core._credential``). For a tunable whose schema default is
    ``None``, absent means absent — a real topology (no Redis, no Milvus, no
    Vault).
    """
    if isinstance(default, bool):
        return env.bool(name, default=default)
    if isinstance(default, int) and not isinstance(default, bool):
        return env.int(name, default=default)
    if isinstance(default, float):
        return env.float(name, default=default)
    if isinstance(default, list):
        return env.list(name, default=list(default))
    return env.str(name, default=default)


def _read_vector_dim() -> int:
    """Resolve the shared vector dimension (seam dim unity).

    Order: ``SOMA_VECTOR_DIM`` (explicit) → ``MEM_EMBED_DIM`` (the agent
    seam's name for the same value) → the schema default on TUNABLES. The two
    names exist because the agent and SFM must share one vector space; they
    are not two dimensions. There is no further fallback — a dim is not
    guessed (Rule 91).
    """
    explicit = env.str("SOMA_VECTOR_DIM", default=None)
    if explicit is not None and explicit != "":
        return env.int("SOMA_VECTOR_DIM")
    seam = env.str("MEM_EMBED_DIM", default=None)
    if seam is not None and seam != "":
        return env.int("MEM_EMBED_DIM")
    return int(schema_default("SOMA_VECTOR_DIM"))


# -----------------------------------------------------------------------------
# Redis topology
# -----------------------------------------------------------------------------
SOMA_REDIS_HOST = _read("SOMA_REDIS_HOST", schema_default("SOMA_REDIS_HOST"))
SOMA_REDIS_PORT = _read("SOMA_REDIS_PORT", schema_default("SOMA_REDIS_PORT"))
SOMA_REDIS_DB = _read("SOMA_REDIS_DB", schema_default("SOMA_REDIS_DB"))
# Absent (None) is a real topology: a Redis with no AUTH. It is not an empty
# password and it is not a silent fallback -- when this deployment requires
# Redis AUTH, the operator sets SOMA_REDIS_PASSWORD or Vault supplies it.
SOMA_REDIS_PASSWORD = _read("SOMA_REDIS_PASSWORD", schema_default("SOMA_REDIS_PASSWORD"))

# -----------------------------------------------------------------------------
# Milvus vector store topology
# -----------------------------------------------------------------------------
SOMA_MILVUS_HOST = _read("SOMA_MILVUS_HOST", schema_default("SOMA_MILVUS_HOST"))
SOMA_MILVUS_PORT = _read("SOMA_MILVUS_PORT", schema_default("SOMA_MILVUS_PORT"))
SOMA_MILVUS_TIMEOUT_S = _read("SOMA_MILVUS_TIMEOUT_S", schema_default("SOMA_MILVUS_TIMEOUT_S"))

# -----------------------------------------------------------------------------
# Memory system
# -----------------------------------------------------------------------------
SOMA_MEMORY_NAMESPACE = _read("SOMA_MEMORY_NAMESPACE", schema_default("SOMA_MEMORY_NAMESPACE"))
SOMA_TEST_MEMORY_NAMESPACE = _read(
    "SOMA_TEST_MEMORY_NAMESPACE", schema_default("SOMA_TEST_MEMORY_NAMESPACE")
)
# Seam dim unity (ARCHITECTURE-INVARIANTS §2): SOMA_VECTOR_DIM ==
# MEM_EMBED_DIM == SOMABRAIN_EMBED_DIM. Never invent a fallback.
SOMA_VECTOR_DIM = _read_vector_dim()

# Index shape and distance metric — the values MilvusVectorStore used to hardcode.
SOMA_SIMILARITY_METRIC = _read("SOMA_SIMILARITY_METRIC", schema_default("SOMA_SIMILARITY_METRIC"))
SOMA_MILVUS_NLIST = _read("SOMA_MILVUS_NLIST", schema_default("SOMA_MILVUS_NLIST"))
SOMA_MILVUS_NPROBE = _read("SOMA_MILVUS_NPROBE", schema_default("SOMA_MILVUS_NPROBE"))

# Search ranking knobs — the values MemoryService.search used to hardcode.
SOMA_SEARCH_CANDIDATE_MULTIPLIER = _read(
    "SOMA_SEARCH_CANDIDATE_MULTIPLIER", schema_default("SOMA_SEARCH_CANDIDATE_MULTIPLIER")
)
SOMA_HASH_EMBEDDING_PENALTY = _read(
    "SOMA_HASH_EMBEDDING_PENALTY", schema_default("SOMA_HASH_EMBEDDING_PENALTY")
)

# -----------------------------------------------------------------------------
# API / observability
# -----------------------------------------------------------------------------
SOMA_LOG_LEVEL = _read("SOMA_LOG_LEVEL", schema_default("SOMA_LOG_LEVEL"))
SOMA_LOG_JSON = _read("SOMA_LOG_JSON", schema_default("SOMA_LOG_JSON"))
SOMA_PROBE_TIMEOUT_S = _read("SOMA_PROBE_TIMEOUT_S", schema_default("SOMA_PROBE_TIMEOUT_S"))

# -----------------------------------------------------------------------------
# External service (Vault topology)
# -----------------------------------------------------------------------------
SOMA_VAULT_URL = _read("SOMA_VAULT_URL", schema_default("SOMA_VAULT_URL"))

# -----------------------------------------------------------------------------
# Backup / data directories
# -----------------------------------------------------------------------------
SOMA_BACKUP_DIR = Path(_read("SOMA_BACKUP_DIR", schema_default("SOMA_BACKUP_DIR")))
SOMA_MEMORY_DATA_DIR = Path(_read("SOMA_MEMORY_DATA_DIR", schema_default("SOMA_MEMORY_DATA_DIR")))
SOMA_S3_BUCKET = _read("SOMA_S3_BUCKET", schema_default("SOMA_S3_BUCKET"))

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
