"""
Minimal FastAPI example exposing store/recall/stats endpoints.

Run (after installing fastapi and uvicorn):
  pip install fastapi uvicorn
  uvicorn examples.api:app --reload
"""

from typing import Optional, Dict, Any, Tuple
import os
import time
from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel

from somafractalmemory.factory import create_memory_system, MemoryMode
from somafractalmemory.core import MemoryType


def parse_coord(text: str) -> Tuple[float, ...]:
    parts = [p.strip() for p in text.split(',') if p.strip()]
    return tuple(float(p) for p in parts)


app = FastAPI(title="SomaFractalMemory API")
mem = create_memory_system(
    MemoryMode.LOCAL_AGENT, "api_ns", config={"redis": {"testing": True}, "qdrant": {"path": "./qdrant.db"}}
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


@app.post("/store", dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/store"))])
def store(req: StoreRequest):
    mtype = MemoryType.SEMANTIC if req.type == "semantic" else MemoryType.EPISODIC
    mem.store_memory(parse_coord(req.coord), req.payload, memory_type=mtype)
    return {"ok": True}


@app.post("/recall", dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/recall"))])
def recall(req: RecallRequest):
    mtype = None
    if req.type:
        mtype = MemoryType.SEMANTIC if req.type == "semantic" else MemoryType.EPISODIC
    # If filters provided, call hybrid-by-type with filters directly for exact-match attr filtering
    if req.filters:
        res = mem.find_hybrid_by_type(req.query, top_k=req.top_k, memory_type=mtype, filters=req.filters)
    else:
        res = mem.recall(req.query, top_k=req.top_k, memory_type=mtype)
    return {"matches": res}

@app.post("/recall_batch", dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/recall_batch"))])
def recall_batch(req: RecallBatchRequest):
    mtype = None
    if req.type:
        mtype = MemoryType.SEMANTIC if req.type == "semantic" else MemoryType.EPISODIC
    res = mem.recall_batch(req.queries, top_k=req.top_k, memory_type=mtype, filters=req.filters)
    return {"batches": res}


@app.get("/stats", dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/stats"))])
def stats():
    return mem.memory_stats()


@app.get("/health")
def health():
    return mem.health_check()


@app.get("/neighbors", dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/neighbors"))])
def neighbors(coord: str, link_type: str | None = None, limit: int | None = None):
    c = parse_coord(coord)
    nbrs = mem.graph_store.get_neighbors(c, link_type=link_type, limit=limit)
    # Convert coords to lists for JSON
    return {"neighbors": [[list(co), data] for co, data in nbrs]}


@app.post("/export_memories", dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/export_memories"))])
def export_memories(req: ExportMemoriesRequest):
    n = mem.export_memories(req.path)
    return {"exported": n}


@app.post("/import_memories", dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/import_memories"))])
def import_memories(req: ImportMemoriesRequest):
    n = mem.import_memories(req.path, replace=req.replace)
    return {"imported": n}


@app.post("/delete_many", dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/delete_many"))])
def delete_many(req: DeleteManyRequest):
    coords = [parse_coord(s) for s in req.coords]
    n = mem.delete_many(coords)
    return {"deleted": n}


@app.post("/link", dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/link"))])
def link(req: LinkRequest):
    mem.link_memories(parse_coord(req.from_coord), parse_coord(req.to_coord), link_type=req.type, weight=req.weight)
    return {"ok": True}


@app.get("/shortest_path", dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/shortest_path"))])
def shortest_path(frm: str, to: str, link_type: str | None = None):
    path = mem.find_shortest_path(parse_coord(frm), parse_coord(to), link_type=link_type)
    return {"path": [list(c) for c in path]}


@app.post("/store_bulk", dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/store_bulk"))])
def store_bulk(req: StoreBulkRequest):
    from somafractalmemory.core import MemoryType
    items = []
    for it in req.items:
        mtype = MemoryType.SEMANTIC if it.type == "semantic" else MemoryType.EPISODIC
        items.append((parse_coord(it.coord), it.payload, mtype))
    mem.store_memories_bulk(items)
    return {"stored": len(items)}


@app.post("/recall_with_scores", dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/recall_with_scores"))])
def recall_with_scores(query: str, top_k: int = 5, type: str | None = None):
    from somafractalmemory.core import MemoryType
    mtype = MemoryType.SEMANTIC if type == "semantic" else (MemoryType.EPISODIC if type == "episodic" else None)
    res = mem.recall_with_scores(query, top_k=top_k, memory_type=mtype)
    return {"results": res}


@app.post("/recall_with_context", dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/recall_with_context"))])
def recall_with_context(query: str, context: dict, top_k: int = 5, type: str | None = None):
    from somafractalmemory.core import MemoryType
    mtype = MemoryType.SEMANTIC if type == "semantic" else (MemoryType.EPISODIC if type == "episodic" else None)
    res = mem.find_hybrid_with_context(query, context, top_k=top_k, memory_type=mtype)
    return {"results": res}


@app.get("/range", dependencies=[Depends(auth_dep), Depends(lambda: rate_limit_dep("/range"))])
def range_search(min: str, max: str, type: str | None = None):
    from somafractalmemory.core import MemoryType
    mtype = MemoryType.SEMANTIC if type == "semantic" else (MemoryType.EPISODIC if type == "episodic" else None)
    mi = parse_coord(min)
    ma = parse_coord(max)
    res = mem.find_by_coordinate_range(mi, ma, memory_type=mtype)
    return {"coords": [m.get("coordinate") for m in res if m.get("coordinate")]}
