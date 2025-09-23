"""Small FastAPI example exposing the MinimalSoma math-first core.

Usage (venv):
  uvicorn examples.math_api:app --port 9595
"""

from typing import Dict

from fastapi import FastAPI, HTTPException

from somafractalmemory.minimal_core import MinimalSoma

app = FastAPI(title="Soma Minimal Math API")

store = MinimalSoma(dim=3)


@app.on_event("startup")
def _startup():
    # seed with a couple of math points
    store.store((0.0, 0.0, 0.0), {"name": "origin"})
    store.store((1.0, 0.0, 0.0), {"name": "point-x"})


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/store")
def api_store(coord: Dict[str, float], payload: Dict):
    try:
        c = (float(coord["x"]), float(coord["y"]), float(coord["z"]))
    except Exception:
        raise HTTPException(
            status_code=400, detail="coordinate must contain x,y,z floats"
        ) from None
    store.store(c, payload)
    return {"stored": True}


@app.get("/recall")
def api_recall(x: float, y: float, z: float, top_k: int = 3):
    res = store.recall((x, y, z), top_k=top_k)
    return {"results": res}
