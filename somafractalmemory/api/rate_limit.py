"""Redis token-bucket throttle for the memory/graph write and search routes.

A real bucket, not a knob with no reader. ``settings/infra`` used to document
``SOMA_RATE_LIMIT_*`` as deleted because ``api.core.get_rate_limiter`` returned
``None`` and claimed otherwise — a stub dressed as a feature. This module is
the feature; the tunables registered in ``settings.model`` are the values this
code actually reads.

Bucket
------
One bucket per (client IP, route class). Capacity is ``SOMA_RATE_LIMIT_BURST``
tokens; tokens refill at the class's ``*_RPS`` rate. A request consumes one
token. Exhaustion returns HTTP 429 with a ``Retry-After`` of one second.

Route classes
-------------
* ``write`` — mutating methods on the memory and graph routes
  (``POST /memories``, ``DELETE /memories/{coord}``, ``POST /graph/link``).
* ``search`` — the read-heavy query routes
  (``GET|POST /memories/search``, ``GET /graph/neighbors``, ``GET /graph/path``,
  ``GET /memories/{coord}``).

Health is exempt: an operator must still be able to ask why the throttle is
rejecting.

Fail-closed
-----------
If the bucket cannot be consulted (Redis down, not configured, script error)
the request is REJECTED. Rate limiting that silently opens on an outage is a
bypass (Rule 164: a swallowed error is a bypass). The response is 503 so the
caller can tell a throttle failure from a quota exhaustion.

Client identity
---------------
The bucket key uses ``REMOTE_ADDR`` only. ``X-Forwarded-For`` is caller-supplied
and trivially spoofable; trusting it would let one client mint unlimited
buckets. A reverse proxy in front of this service must present the real client
address on the socket.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse

from somafractalmemory.admin.common.messages import ErrorCode, get_message
from somafractalmemory.admin.common.utils.logger import get_logger

logger = get_logger(__name__)

# Atomic consume-one-token. Returns 1 when allowed, 0 when the bucket is empty.
# One round trip, no race between read and write — a non-atomic check-then-set
# is not a rate limit, it is a suggestion.
_TOKEN_BUCKET_LUA = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_per_sec = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

local data = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(data[1])
local ts = tonumber(data[2])

if tokens == nil or ts == nil then
  tokens = capacity
  ts = now
end

local elapsed = now - ts
if elapsed < 0 then
  elapsed = 0
end
tokens = tokens + elapsed * refill_per_sec
if tokens > capacity then
  tokens = capacity
end

local allowed = 0
if tokens >= 1 then
  tokens = tokens - 1
  allowed = 1
end

redis.call('HSET', key, 'tokens', tokens, 'ts', now)
redis.call('EXPIRE', key, 3600)
return allowed
"""

# Paths that are never throttled: liveness must survive a throttle failure.
_EXEMPT_PREFIXES = ("/health", "/docs", "/openapi.json")

# Route classification. Order matters — first match wins.
_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

_SEARCH_PATHS = (
    "/memories/search",
    "/graph/neighbors",
    "/graph/path",
)


class RateLimitError(Exception):
    """The bucket refused the request. Carries no secret and no stack."""

    def __init__(self, retry_after_s: int, *, throttle_unavailable: bool = False):
        super().__init__("rate limit exceeded")
        self.retry_after_s = max(1, int(retry_after_s))
        self.throttle_unavailable = throttle_unavailable


class TokenBucket:
    """Redis-backed token bucket. One bucket per key, capacity + refill rate.

    The bucket state lives in a Redis hash ``{tokens, ts}`` under a single key.
    The Lua script is the only writer: it reads, refills, consumes and stores
    in one atomic step.
    """

    def __init__(self, redis_client, *, capacity: int, refill_per_sec: float):
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        if refill_per_sec <= 0:
            raise ValueError("refill_per_sec must be > 0")
        self._redis = redis_client
        self._capacity = int(capacity)
        self._refill = float(refill_per_sec)
        self._script = redis_client.register_script(_TOKEN_BUCKET_LUA)

    def consume(self, key: str, *, now: float | None = None) -> bool:
        """Consume one token from ``key``'s bucket. True = allowed.

        Raises:
            RateLimitError: when the bucket cannot be consulted. Fail-closed —
                an unavailable throttle is not permission to proceed.
        """
        if now is None:
            now = time.time()
        try:
            allowed = self._script(
                keys=[key],
                args=[self._capacity, self._refill, now],
            )
        except Exception as exc:  # noqa: BLE001 — any Redis failure is one answer
            logger.error("rate-limit bucket unavailable: %s", type(exc).__name__)
            raise RateLimitError(retry_after_s=1, throttle_unavailable=True) from exc
        return bool(int(allowed))


def _client_ip(request: HttpRequest) -> str:
    """Socket peer address. Never X-Forwarded-For (caller-supplied, spoofable)."""
    return request.META.get("REMOTE_ADDR") or "unknown"


def classify(request: HttpRequest) -> str | None:
    """Route class for this request: ``'write'``, ``'search'`` or ``None``.

    ``None`` means the request is not throttled (health, docs, unknown paths).

    Classification order is load-bearing: ``POST /memories/search`` is a
    search, not a write, and a write-prefix match first would misfile it.
    """
    path = request.path or "/"
    for prefix in _EXEMPT_PREFIXES:
        if path == prefix or path.startswith(prefix + "/"):
            return None

    method = request.method.upper()
    stripped = path.rstrip("/")

    # Search first: POST /memories/search is a query, not a store.
    if method == "POST":
        for suffix in _SEARCH_PATHS:
            if stripped == suffix or stripped.endswith(suffix):
                return "search"
    if method == "GET" and (stripped.startswith("/memories") or stripped.startswith("/graph")):
        # /memories/{coord} fetch and /graph/neighbors, /graph/path are the
        # read-heavy query shapes.
        return "search"
    if method in _WRITE_METHODS and (
        stripped.startswith("/memories") or stripped.startswith("/graph")
    ):
        return "write"
    return None


def _bucket_for(request: HttpRequest, route_class: str) -> TokenBucket:
    """Build the bucket this request must pass through.

    Configuration is read from Django settings only — the TUNABLES registry
    is the single schema-default authority (``settings.model``). A missing
    Redis topology is an error here, not a silent in-process counter: a
    per-process counter resets on deploy, splits across replicas and fails
    open in multi-instance deployments.
    """
    import redis as redis_lib

    from somafractalmemory.settings.model import resolve_setting

    host = getattr(settings, "SOMA_REDIS_HOST", None)
    port = getattr(settings, "SOMA_REDIS_PORT", None)
    if not host or not port:
        raise RateLimitError(retry_after_s=1, throttle_unavailable=True)

    password = getattr(settings, "SOMA_REDIS_PASSWORD", None)
    db = int(resolve_setting("SOMA_REDIS_DB"))
    client = redis_lib.Redis(
        host=host,
        port=int(port),
        db=db,
        password=password,
        socket_timeout=float(resolve_setting("SOMA_PROBE_TIMEOUT_S")),
        socket_connect_timeout=float(resolve_setting("SOMA_PROBE_TIMEOUT_S")),
    )

    burst = int(resolve_setting("SOMA_RATE_LIMIT_BURST"))
    if route_class == "write":
        rps = float(resolve_setting("SOMA_RATE_LIMIT_WRITE_RPS"))
    else:
        rps = float(resolve_setting("SOMA_RATE_LIMIT_READ_RPS"))
    return TokenBucket(client, capacity=burst, refill_per_sec=rps)


class RateLimitMiddleware:
    """Throttle write and search routes with the Redis token bucket.

    Registered in ``MIDDLEWARE`` before the Ninja handler. ``ninja.testing.
    TestClient`` does not run Django middleware, so unit tests of the API
    surface are unaffected; tests of this class exercise it directly.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        route_class = classify(request)
        if route_class is None:
            return self.get_response(request)

        try:
            bucket = _bucket_for(request, route_class)
            allowed = bucket.consume(f"ratelimit:{route_class}:{_client_ip(request)}")
        except RateLimitError as exc:
            return self._reject(exc)

        if not allowed:
            return self._reject(RateLimitError(retry_after_s=1))

        return self.get_response(request)

    @staticmethod
    def _reject(exc: RateLimitError) -> JsonResponse:
        if exc.throttle_unavailable:
            body = {"detail": get_message(ErrorCode.INTERNAL_ERROR)}
            status = 503
        else:
            body = {"detail": get_message(ErrorCode.RATE_LIMIT_EXCEEDED)}
            status = 429
        response = JsonResponse(body, status=status)
        response["Retry-After"] = str(exc.retry_after_s)
        return response
