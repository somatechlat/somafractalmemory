"""
Enterprise FastAPI example exposing store/recall/stats endpoints.

This example launches the API in ENTERPRISE mode. It defaults to local
fallbacks for development (fakeredis and local Qdrant DB file) unless
`SOMA_ENTERPRISE_REAL=true` is set in the environment, in which case
it will read real Redis/Qdrant connection info from environment vars.

Run (after installing fastapi and uvicorn):
  pip install fastapi uvicorn
  uvicorn examples.api_enterprise:app --reload
"""

import os
import time
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from somafractalmemory.core import MemoryType
from somafractalmemory.factory import MemoryMode, create_memory_system


def parse_coord(text: str) -> Tuple[float, ...]:
    parts = [p.strip() for p in text.split(",") if p.strip()]
    return tuple(float(p) for p in parts)


app = FastAPI(title="SomaFractalMemory ENTERPRISE API")

# Enterprise config: use real services if requested via env, otherwise fall back to
# a local testing-friendly configuration so the server can run without external
# dependencies.
if os.getenv("SOMA_ENTERPRISE_REAL", "false").lower() == "true":
    redis_cfg = {
        "host": os.getenv("SOMA_REDIS_HOST", "localhost"),
        "port": int(os.getenv("SOMA_REDIS_PORT", 6379)),
    }
    qdrant_cfg = {}
    # Prefer a URL if provided
    if os.getenv("SOMA_QDRANT_URL"):
        qdrant_cfg["url"] = os.getenv("SOMA_QDRANT_URL")
    else:
        qdrant_cfg["host"] = os.getenv("SOMA_QDRANT_HOST", "localhost")
        qdrant_cfg["port"] = int(os.getenv("SOMA_QDRANT_PORT", 6333))
    config = {"redis": redis_cfg, "qdrant": qdrant_cfg}
else:
    # Developer-friendly defaults (fakeredis + local qdrant file)
    config = {"redis": {"testing": True}, "qdrant": {"path": "./qdrant.db"}}

mem = create_memory_system(
    MemoryMode.ENTERPRISE,
    "enterprise_ns",
    config=config,
)

# Simple auth + rate limit stubs
API_TOKEN = os.getenv("SOMA_API_TOKEN")
_RATE: dict[tuple[str, str], list[float]] = {}


def auth_dep(authorization: str | None = Header(default=None)):
    if API_TOKEN:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing bearer token")
        token = authorization.split(" ", 1)[1]
        if token != API_TOKEN:
            raise HTTPException(status_code=403, detail="Invalid token")


def rate_limit_dep(path: str):
    # Allow up to 60 requests per minute per path
    window = 60.0
    max_reqs = 60
    key = (path, "global")
    now = time.time()
    bucket = _RATE.setdefault(key, [])
    # Drop old
    while bucket and now - bucket[0] > window:
        bucket.pop(0)
    if len(bucket) >= max_reqs:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    bucket.append(now)


class StoreRequest(BaseModel):
    coord: str
    payload: Dict[str, Any]
    type: Optional[str] = "episodic"


class RecallRequest(BaseModel):
    query: str
    top_k: int = 5
    type: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None


class ExportMemoriesRequest(BaseModel):
    path: str


class ImportMemoriesRequest(BaseModel):
    path: str
    replace: bool = False


class DeleteManyRequest(BaseModel):
    coords: list[str]


class LinkRequest(BaseModel):
    from_coord: str
    to_coord: str
    type: str = "related"
    weight: float = 1.0


class BulkItem(BaseModel):
    coord: str
    payload: dict
    type: str = "episodic"


class StoreBulkRequest(BaseModel):
    items: list[BulkItem]


class RecallBatchRequest(BaseModel):
    queries: list[str]
    top_k: int = 5
    type: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None


# --- Response models ---
class OkResponse(BaseModel):
    ok: bool


class MatchesResponse(BaseModel):
    matches: List[Dict[str, Any]]


class BatchesResponse(BaseModel):
    batches: List[List[Dict[str, Any]]]


class ScoreItem(BaseModel):
    payload: Dict[str, Any]
    score: Optional[float] = None


class ScoresResponse(BaseModel):
    results: List[ScoreItem]


class ResultsResponse(BaseModel):
    results: List[Dict[str, Any]]


class NeighborsResponse(BaseModel):
    neighbors: List[List[Any]]


class PathResponse(BaseModel):
    path: List[List[float]]


class ExportMemoriesResponse(BaseModel):
    exported: int


class ImportMemoriesResponse(BaseModel):
    imported: int


class DeleteManyResponse(BaseModel):
    deleted: int


class StoreBulkResponse(BaseModel):
    stored: int


class StatsResponse(BaseModel):
    total_memories: int
    episodic: int
    semantic: int


class HealthResponse(BaseModel):
    kv_store: bool
    vector_store: bool
    graph_store: bool
    prediction_provider: bool


@app.post(
    "/store",
    response_model=OkResponse,
    tags=["memories"],
    dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/store"))],
)
def store(req: StoreRequest) -> OkResponse:
    mtype = MemoryType.SEMANTIC if req.type == "semantic" else MemoryType.EPISODIC
    mem.store_memory(parse_coord(req.coord), req.payload, memory_type=mtype)
    return OkResponse(ok=True)


@app.post(
    "/recall",
    response_model=MatchesResponse,
    tags=["memories"],
    dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/recall"))],
)
def recall(req: RecallRequest) -> MatchesResponse:
    mtype = None
    if req.type:
        mtype = MemoryType.SEMANTIC if req.type == "semantic" else MemoryType.EPISODIC
    if req.filters:
        res = mem.find_hybrid_by_type(
            req.query, top_k=req.top_k, memory_type=mtype, filters=req.filters
        )
    else:
        res = mem.recall(req.query, top_k=req.top_k, memory_type=mtype)
    return MatchesResponse(matches=res)


@app.get(
    "/stats",
    response_model=StatsResponse,
    tags=["system"],
    dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/stats"))],
)
def stats() -> StatsResponse:
    return StatsResponse(**mem.memory_stats())


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(**mem.health_check())
