# Standard library imports
import json
import logging
import uuid
from concurrent import futures
from typing import Any

# Third‑party imports (alphabetical)
import grpc
import psycopg2
import qdrant_client
import redis
import requests
from grpc_health.v1 import health, health_pb2, health_pb2_grpc
from qdrant_client.http.models import Distance, PointStruct, VectorParams

# Local imports
try:
    from common.config.settings import load_settings
except Exception:  # pragma: no cover - optional in CI environments
    load_settings = None  # type: ignore

from somafractalmemory import memory_pb2, memory_pb2_grpc

LOGGER = logging.getLogger(__name__)


class MemoryServicer(memory_pb2_grpc.MemoryServiceServicer):
    def __init__(self, settings: Any | None = None):
        """Initialize the servicer.

        ``settings`` is an optional ``SMFSettings`` instance; if omitted the
        servicer falls back to environment variables for backwards
        compatibility. This keeps the original lightweight behaviour while
        allowing the new centralized configuration.
        """
        self.settings = settings
        # No heavy imports here – the core memory system is imported lazily
        # inside each RPC method when needed.

    def Store(self, request, context):
        # Persist memory payload in Postgres and vector in Qdrant.
        try:
            mem = request.memory
            coord: list[float] = list(mem.coord.values)
            payload_json = mem.payload_json or "{}"
            memory_type = mem.memory_type or "default"

            # Generate deterministic id from coordinate for idempotency
            point_id = uuid.uuid5(uuid.NAMESPACE_URL, repr(coord)).hex

            # Upsert into Qdrant
            # Use centralized Qdrant host if settings provided, else default.
            qdrant_host = self.settings.infra.qdrant if self.settings else "localhost"
            q = qdrant_client.QdrantClient(url=f"http://{qdrant_host}:6333")
            collection = memory_type or "memories"
            try:
                # Create collection if missing
                if not q.collection_exists(collection_name=collection):
                    q.create_collection(
                        collection_name=collection,
                        vectors_config=VectorParams(size=len(coord), distance=Distance.COSINE),
                    )
            except Exception:
                pass
            point = PointStruct(id=point_id, vector=coord, payload=json.loads(payload_json))
            q.upsert(collection_name=collection, points=[point])

            # Store canonical JSON in Postgres kv table
            from psycopg2.extras import Json

            pg_host = self.settings.infra.postgres if self.settings else "localhost"
            conn = psycopg2.connect(
                dbname="somamemory",
                user="postgres",
                password="postgres",
                host=pg_host,
                port=5433,
            )
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS kv_store (key TEXT PRIMARY KEY, value JSONB NOT NULL);"
                )
                cur.execute(
                    "INSERT INTO kv_store (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;",
                    (point_id, Json(json.loads(payload_json))),
                )
            conn.close()
            return memory_pb2.StoreResponse(ok=True, id=point_id)
        except Exception as exc:
            logging.exception("Store failed: %s", exc)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return memory_pb2.StoreResponse(ok=False, id="")

    def Recall(self, request, context):
        try:
            qdrant_host = self.settings.infra.qdrant if self.settings else "localhost"
            q = qdrant_client.QdrantClient(url=f"http://{qdrant_host}:6333")
            query: list[float] = list(request.query.values)
            top_k = int(request.top_k or 5)
            memory_type = request.memory_type or "memories"
            # Use query_points if available, otherwise search
            try:
                resp = q.search(
                    collection_name=memory_type, query_vector=query, limit=top_k, with_payload=True
                )
                points = resp
            except Exception:
                resp = q.query_points(
                    collection_name=memory_type, query=query, limit=top_k, with_payload=True
                )
                points = getattr(resp, "points", resp)

            out = memory_pb2.RecallResult()
            for p in points:
                # Normalize different client return types
                pid = None
                vector = []
                payload = {}
                # qdrant-client ScoredPoint or PointStruct objects
                if hasattr(p, "id"):
                    pid = p.id
                if hasattr(p, "vector"):
                    vector = p.vector or []
                if hasattr(p, "payload"):
                    payload = p.payload or {}
                # dict-like responses
                if isinstance(p, dict):
                    pid = p.get("id", pid)
                    vector = p.get("vector", vector)
                    payload = p.get("payload", payload)

                coord_msg = memory_pb2.Coordinate(values=list(vector))
                mem = memory_pb2.Memory(
                    coord=coord_msg, payload_json=json.dumps(payload or {}), memory_type=memory_type
                )
                out.memories.append(mem)
            return out
        except Exception as exc:
            logging.exception("Recall failed: %s", exc)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return memory_pb2.RecallResult()

    def Delete(self, request, context):
        try:
            coord = list(request.coord.values)
            point_id = uuid.uuid5(uuid.NAMESPACE_URL, repr(coord)).hex
            qdrant_host = self.settings.infra.qdrant if self.settings else "localhost"
            q = qdrant_client.QdrantClient(url=f"http://{qdrant_host}:6333")
            collection = "memories"
            try:
                q.delete(collection_name=collection, points_selector=PointStruct(id=point_id))
            except Exception:
                # best-effort
                pass
            pg_host = self.settings.infra.postgres if self.settings else "localhost"
            conn = psycopg2.connect(
                dbname="somamemory",
                user="postgres",
                password="postgres",
                host=pg_host,
                port=5433,
            )
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("DELETE FROM kv_store WHERE key = %s;", (point_id,))
            conn.close()
            return memory_pb2.DeleteResponse(ok=True)
        except Exception as exc:
            logging.exception("Delete failed: %s", exc)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return memory_pb2.DeleteResponse(ok=False)

    def Health(self, request, context):
        # Check Redis, Postgres, and Qdrant used by the compose stack.
        status = {}
        try:
            redis_host = self.settings.infra.redis if self.settings else "localhost"
            r = redis.Redis(host=redis_host, port=6381, db=0, socket_connect_timeout=2)
            status["redis"] = bool(r.ping())
        except Exception as e:
            LOGGER.debug("Redis health error: %s", e)
            status["redis"] = False

        try:
            pg_host = self.settings.infra.postgres if self.settings else "localhost"
            conn = psycopg2.connect(
                dbname="somamemory",
                user="postgres",
                password="postgres",
                host=pg_host,
                port=5433,
                connect_timeout=2,
            )
            conn.close()
            status["postgres"] = True
        except Exception as e:
            LOGGER.debug("Postgres health error: %s", e)
            status["postgres"] = False

        try:
            qdrant_host = self.settings.infra.qdrant if self.settings else "localhost"
            r = requests.get(f"http://{qdrant_host}:6333/collections", timeout=2)
            status["qdrant"] = r.status_code == 200
        except Exception as e:
            LOGGER.debug("Qdrant health error: %s", e)
            status["qdrant"] = False

        ok = all(status.values())
        msg = "OK" if ok else "DEGRADED"
        return memory_pb2.HealthResponse(status=msg)


def serve(host: str = "0.0.0.0", port: int = 50053):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    # Load centralized settings if available
    settings_obj = load_settings() if load_settings else None
    # Register the core memory RPCs with settings
    servicer = MemoryServicer(settings=settings_obj)
    memory_pb2_grpc.add_MemoryServiceServicer_to_server(servicer, server)

    # Register the standard health service (grpc-health-probe compatible)
    health_servicer = health.HealthServicer()
    # Set the overall service status to SERVING (empty service name = all services)
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)

    bind_addr = f"{host}:{port}"
    server.add_insecure_port(bind_addr)
    server.start()
    LOGGER.info("gRPC server started on %s", bind_addr)
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        LOGGER.info("Shutting down gRPC server")
        server.stop(0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    serve()
