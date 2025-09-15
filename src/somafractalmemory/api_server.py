"""
FastAPI server for SomaFractalMemory

Exposes memory operations as HTTP endpoints with OpenAPI docs at /docs.
Configurable via environment variables (SFM_MODE, SFM_NAMESPACE, etc).
"""

import os

from fastapi import FastAPI
from pydantic import BaseModel

from somafractalmemory.factory import MemoryMode, create_memory_system


# --- Models for request/response ---
class StoreRequest(BaseModel):
    coord: list[float]
    payload: dict
    mem_type: str | None = "episodic"


class RecallRequest(BaseModel):
    query: str
    top_k: int = 5
    mem_type: str | None = None


class LinkRequest(BaseModel):
    from_coord: list[float]
    to_coord: list[float]
    link_type: str | None = "related"
    weight: float = 1.0


class PayloadsByCoordsRequest(BaseModel):
    coords: list[list[float]]


# --- FastAPI app ---
app = FastAPI(
    title="SomaFractalMemory API", description="Memory microservice for agents.", version="0.1.0"
)


# --- Dependency: get memory system instance ---
def get_mem():
    mode = os.environ.get("SFM_MODE", "on_demand")
    ns = os.environ.get("SFM_NAMESPACE", "api_ns")
    config_json = os.environ.get("SFM_CONFIG_JSON")
    config = None
    if config_json:
        import json

        if config_json.strip().startswith("{"):
            config = json.loads(config_json)
        elif os.path.exists(config_json):
            with open(config_json) as f:
                config = json.load(f)
    return create_memory_system(MemoryMode(mode), ns, config)


@app.get("/health", tags=["system"])
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/store", tags=["memory"])
def store(req: StoreRequest):
    """Store a memory coordinate and payload."""
    mem = get_mem()
    ok = mem.store(tuple(req.coord), req.payload)
    return {"ok": ok}


@app.post("/recall", tags=["memory"])
def recall(req: RecallRequest):
    """Recall memories by query string."""
    mem = get_mem()
    from somafractalmemory.core import MemoryType

    mtype = None
    if req.mem_type:
        mtype = MemoryType.SEMANTIC if req.mem_type == "semantic" else MemoryType.EPISODIC
    res = mem.recall(req.query, top_k=req.top_k, memory_type=mtype)
    return {"results": res}


@app.get("/stats", tags=["system"])
def stats():
    """Get memory system stats."""
    mem = get_mem()
    return mem.memory_stats()


@app.post("/link", tags=["graph"])
def link(req: LinkRequest):
    """Link two memory coordinates in the semantic graph."""
    mem = get_mem()
    link_type = req.link_type if req.link_type is not None else "related"
    ok = mem.link_memories(
        tuple(req.from_coord), tuple(req.to_coord), link_type=link_type, weight=req.weight
    )
    return {"ok": ok}


# Add more endpoints as needed (neighbors, path, export, etc.)


@app.post("/payloads_by_coords", tags=["memory"])
def payloads_by_coords(req: PayloadsByCoordsRequest):
    """Return payloads for the provided list of coordinates.

    Body: { "coords": [[x,y,z], ...] }
    Response: { "payloads": [ {...}, ... ] }
    Missing coordinates are skipped.
    """
    mem = get_mem()
    out: list[dict] = []
    for c in req.coords or []:
        try:
            if not isinstance(c, list) or len(c) < 3:
                continue
            payload = mem.retrieve(tuple(c))  # type: ignore[arg-type]
            if isinstance(payload, dict):
                out.append(payload)
        except Exception:
            continue
    return {"payloads": out}
