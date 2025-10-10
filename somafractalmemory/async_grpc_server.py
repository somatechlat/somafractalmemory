import asyncio
import json
import logging
import uuid
from contextlib import nullcontext

import grpc
import qdrant_client
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from common.utils.trace import configure_tracer
from somafractalmemory import memory_pb2, memory_pb2_grpc
from somafractalmemory.implementations.async_storage import (
    AsyncPostgresKeyValueStore,
    AsyncRedisKeyValueStore,
)

LOGGER = logging.getLogger(__name__)


class AsyncMemoryServicer(memory_pb2_grpc.MemoryServiceServicer):
    def __init__(
        self,
        redis_url: str = "redis://localhost:6381/0",
        pg_dsn: str = "postgresql://postgres:postgres@localhost:5433/somamemory",
    ):
        self._redis_url = redis_url
        self._pg_dsn = pg_dsn
        self._redis: AsyncRedisKeyValueStore | None = None
        self._pg: AsyncPostgresKeyValueStore | None = None

    async def startup(self) -> None:
        # configure tracer (no-op if OpenTelemetry not installed)
        try:
            self._tracer = configure_tracer("somafractalmemory-async")
        except Exception:
            self._tracer = None

        self._redis = AsyncRedisKeyValueStore.from_url(self._redis_url)
        self._pg = await AsyncPostgresKeyValueStore.from_url(self._pg_dsn)

    async def shutdown(self) -> None:
        if self._redis:
            await self._redis.close()
        if self._pg:
            await self._pg.close()

    async def _qdrant_client(self) -> qdrant_client.QdrantClient:
        # synchronous client wrapped via to_thread
        return qdrant_client.QdrantClient(url="http://localhost:6333")

    async def Store(self, request, context) -> memory_pb2.StoreResponse:
        try:
            mem = request.memory
            with (
                self._tracer.start_as_current_span("Store")
                if getattr(self, "_tracer", None)
                else nullcontext()
            ):
                coord = list(mem.coord.values)
            payload_json = mem.payload_json or "{}"
            memory_type = mem.memory_type or "memories"

            point_id = uuid.uuid5(uuid.NAMESPACE_URL, repr(coord)).hex

            # Upsert Qdrant in thread
            q = await asyncio.to_thread(qdrant_client.QdrantClient, url="http://localhost:6333")
            try:
                exists = await asyncio.to_thread(q.collection_exists, collection_name=memory_type)
                if not exists:
                    await asyncio.to_thread(
                        q.create_collection,
                        collection_name=memory_type,
                        vectors_config=VectorParams(size=len(coord), distance=Distance.COSINE),
                    )
            except Exception:
                pass
            point = PointStruct(id=point_id, vector=coord, payload=json.loads(payload_json))
            await asyncio.to_thread(q.upsert, collection_name=memory_type, points=[point])

            # Store in Postgres (async)
            if self._pg is None:
                raise RuntimeError("Postgres client not initialised")
            val = json.dumps(json.loads(payload_json)).encode("utf-8")
            LOGGER.debug(
                "Storing to Postgres key=%s type=%s sample=%s", point_id, type(val), str(val)[:200]
            )
            await self._pg.set(point_id, val)
            return memory_pb2.StoreResponse(ok=True, id=point_id)
        except Exception as exc:
            LOGGER.exception("async Store failed: %s", exc)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return memory_pb2.StoreResponse(ok=False, id="")

    async def Recall(self, request, context) -> memory_pb2.RecallResult:
        try:
            with (
                self._tracer.start_as_current_span("Recall")
                if getattr(self, "_tracer", None)
                else nullcontext()
            ):
                q = await asyncio.to_thread(qdrant_client.QdrantClient, url="http://localhost:6333")
                query = list(request.query.values)
            top_k = int(request.top_k or 5)
            memory_type = request.memory_type or "memories"

            # Query qdrant in thread
            try:
                resp = await asyncio.to_thread(
                    q.search,
                    collection_name=memory_type,
                    query_vector=query,
                    limit=top_k,
                    with_payload=True,
                )
                points = resp
            except Exception:
                resp = await asyncio.to_thread(
                    q.query_points,
                    collection_name=memory_type,
                    query=query,
                    limit=top_k,
                    with_payload=True,
                )
                points = getattr(resp, "points", resp)

            out = memory_pb2.RecallResult()
            for p in points:
                vector = getattr(p, "vector", None) or (
                    p.get("vector") if isinstance(p, dict) else []
                )
                payload = getattr(p, "payload", None) or (
                    p.get("payload") if isinstance(p, dict) else {}
                )
                coord_msg = memory_pb2.Coordinate(values=list(vector))
                mem = memory_pb2.Memory(
                    coord=coord_msg, payload_json=json.dumps(payload or {}), memory_type=memory_type
                )
                out.memories.append(mem)
            return out
        except Exception as exc:
            LOGGER.exception("async Recall failed: %s", exc)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return memory_pb2.RecallResult()

    async def Delete(self, request, context) -> memory_pb2.DeleteResponse:
        try:
            with (
                self._tracer.start_as_current_span("Delete")
                if getattr(self, "_tracer", None)
                else nullcontext()
            ):
                coord = list(request.coord.values)
                point_id = uuid.uuid5(uuid.NAMESPACE_URL, repr(coord)).hex
                q = await asyncio.to_thread(qdrant_client.QdrantClient, url="http://localhost:6333")
                try:
                    await asyncio.to_thread(
                        q.delete,
                        collection_name="memories",
                        points_selector=PointStruct(id=point_id),
                    )
                except Exception:
                    pass
                if self._pg:
                    await self._pg.delete(point_id)
            return memory_pb2.DeleteResponse(ok=True)
        except Exception as exc:
            LOGGER.exception("async Delete failed: %s", exc)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return memory_pb2.DeleteResponse(ok=False)

    async def Health(self, request, context) -> memory_pb2.HealthResponse:
        """Health RPC returning simple status string."""
        # perform lightweight checks: redis and postgres health_check
        ok_redis = False
        ok_pg = False
        try:
            if self._redis:
                ok_redis = await self._redis.health_check()
        except Exception:
            ok_redis = False
        try:
            if self._pg:
                ok_pg = await self._pg.health_check()
        except Exception:
            ok_pg = False
        status = "ok" if (ok_redis and ok_pg) else "degraded"
        return memory_pb2.HealthResponse(status=status)


async def serve(host: str = "0.0.0.0", port: int = 50054):
    server = grpc.aio.server()
    servicer = AsyncMemoryServicer()
    await servicer.startup()
    memory_pb2_grpc.add_MemoryServiceServicer_to_server(servicer, server)
    bind = f"[::]:{port}"
    server.add_insecure_port(bind)
    await server.start()
    LOGGER.info("Async gRPC server started on %s", bind)
    try:
        await server.wait_for_termination()
    finally:
        await servicer.shutdown()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
