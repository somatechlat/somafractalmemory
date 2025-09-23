"""
Enterprise-mode FastAPI example for SomaFractalMemory.

Run with the project's venv:
  uvicorn examples.enterprise_api:app --port 9595 --host 0.0.0.0

By default this will attempt to connect to Redis on localhost:6379 and Qdrant on default ports.
Ensure those services are running, or set config overrides in the `config` dict below.
"""

import os
from typing import Any, Dict, Optional, Tuple

# Third‑party imports (alphabetical)
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from pydantic import BaseModel

from somafractalmemory.core import MemoryType
from somafractalmemory.factory import MemoryMode, create_memory_system


def parse_coord(text: str) -> Tuple[float, ...]:
    parts = [p.strip() for p in text.split(",") if p.strip()]
    return tuple(float(p) for p in parts)


app = FastAPI(title="SomaFractalMemory Enterprise API")

# OpenTelemetry tracer setup
trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
# Instrument FastAPI for automatic request tracing
FastAPIInstrumentor().instrument_app(app)

# Default enterprise config: leave Redis and Qdrant settings empty to use client defaults
# If you want to override host/port, set the values here or use environment variables.
_testing_mode = os.getenv("SOMA_ENTERPRISE_TESTING", "0").lower() in ("1", "true", "yes")

if _testing_mode:
    # Use in‑memory Qdrant and FakeRedis for a local testable ENTERPRISE‑style server
    # Hybrid Postgres + Redis for testing – assumes a local Postgres instance is reachable.
    # Adjust the URL as needed for your environment.
    config: Dict[str, Any] = {
        "redis": {"testing": True},
        "postgres": {"url": "postgresql://postgres:postgres@localhost:5432/somamemory"},
        "qdrant": {"path": ":memory:"},
    }
else:
    config: Dict[str, Any] = {"redis": {}, "qdrant": {}}

# Create an ENTERPRISE memory system instance
mem = create_memory_system(MemoryMode.EVENTED_ENTERPRISE, "enterprise_ns", config=config)


class StoreRequest(BaseModel):
    coord: str
    payload: Dict[str, Any]
    type: Optional[str] = "episodic"


class RecallRequest(BaseModel):
    query: str
    top_k: int = 5
    type: Optional[str] = None


@app.get("/health")
def health() -> Dict[str, bool]:
    return mem.health_check()


@app.post("/store")
def store(req: StoreRequest):
    mtype = MemoryType.SEMANTIC if req.type == "semantic" else MemoryType.EPISODIC
    mem.store_memory(parse_coord(req.coord), req.payload, memory_type=mtype)
    return {"ok": True}


@app.post("/recall")
def recall(req: RecallRequest):
    mtype = None
    if req.type:
        mtype = MemoryType.SEMANTIC if req.type == "semantic" else MemoryType.EPISODIC
    res = mem.recall(req.query, top_k=req.top_k, memory_type=mtype)
    return {"matches": res}
