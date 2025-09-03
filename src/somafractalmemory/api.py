from __future__ import annotations

import json
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .core import MemoryType
from .factory import MemoryMode, create_memory_system


def _load_config_dict() -> dict[str, Any]:
    cfg = os.environ.get("SFM_CONFIG_JSON", "").strip()
    if not cfg:
        return {}
    # If looks like a JSON object, parse it; otherwise treat as path
    if cfg.startswith("{"):
        try:
            return json.loads(cfg)
        except Exception:
            return {}
    if os.path.isfile(cfg):
        try:
            with open(cfg, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _get_mode() -> MemoryMode:
    m = (os.environ.get("SFM_MODE", "on_demand") or "on_demand").lower()
    return {
        "on_demand": MemoryMode.ON_DEMAND,
        "local_agent": MemoryMode.LOCAL_AGENT,
        "enterprise": MemoryMode.ENTERPRISE,
    }.get(m, MemoryMode.ON_DEMAND)


def _get_namespace() -> str:
    return os.environ.get("SFM_NAMESPACE", "cli_ns")


app = FastAPI(title="SomaFractalMemory API", version="0.1.0")

# Initialize memory system once per process
_MEM = create_memory_system(_get_mode(), _get_namespace(), config=_load_config_dict())


class StoreRequest(BaseModel):
    coord: list[float] = Field(..., description="Coordinate, e.g., [1,2,3]")
    payload: dict[str, Any] = Field(..., description="Arbitrary JSON payload")
    type: str | None = Field(default="episodic", description="episodic|semantic")


class RecallResponseItem(BaseModel):
    coordinate: list[float] | None = None
    score: float | None = None
    payload: dict[str, Any] | None = None


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "mode": _get_mode().value,
        "namespace": _get_namespace(),
    }


@app.get("/stats")
def stats() -> dict[str, Any]:
    try:
        return _MEM.memory_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/store")
def store(req: StoreRequest) -> dict[str, Any]:
    try:
        t = MemoryType.SEMANTIC if (req.type or "episodic") == "semantic" else MemoryType.EPISODIC
        ok = _MEM.store_memory(tuple(req.coord), req.payload, memory_type=t)
        return {"ok": bool(ok)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/recall", response_model=list[RecallResponseItem])
def recall(q: str = Query(..., description="Query text"), top_k: int = 5, type: str | None = None):  # noqa: A002
    try:
        t = None
        if type:
            t = MemoryType.SEMANTIC if type == "semantic" else MemoryType.EPISODIC
        res = _MEM.recall(q, top_k=top_k, memory_type=t)
        # Ensure list of dicts with standard fields
        out: list[dict[str, Any]] = []
        for r in res:
            if isinstance(r, dict):
                out.append(r)
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
