# somafractalmemory/operations/search.py
"""Search operations for SomaFractalMemory.

Extracted from core.py for VIBE compliance (<500 lines per file).
"""

import json
import math
import re
import time
from typing import TYPE_CHECKING, Any, Optional

import numpy as np
import structlog

if TYPE_CHECKING:
    from ..core import MemoryType, SomaFractalMemoryEnterprise

logger = structlog.get_logger()


def _iter_string_fields(obj: Any):
    """Yield all string fields from nested dict/list payloads."""
    max_items = 4096
    max_depth = 6

    def _walk(o: Any, depth: int):
        nonlocal max_items
        if max_items <= 0 or depth > max_depth:
            return
        if isinstance(o, str):
            max_items -= 1
            yield o
        elif isinstance(o, dict):
            for v in o.values():
                yield from _walk(v, depth + 1)
        elif isinstance(o, list):
            for v in o:
                yield from _walk(v, depth + 1)

    yield from _walk(obj, 0)


def recall_op(
    system: "SomaFractalMemoryEnterprise",
    query: str,
    context: dict[str, Any] | None = None,
    top_k: int = 5,
    memory_type: Optional["MemoryType"] = None,
) -> list[dict[str, Any]]:
    """Recall memories matching a query."""
    from common.config.settings import load_settings
    from common.utils.async_metrics import submit as _submit_metric

    _settings = load_settings()
    _USE_ASYNC_METRICS = _settings.async_metrics_enabled

    def _maybe_submit(fn):
        if _USE_ASYNC_METRICS:
            try:
                _submit_metric(fn)
                return
            except Exception as exc:
                logger.debug("Async metric submission failed", extra={"error": str(exc)})
        try:
            fn()
        except Exception as exc:
            logger.debug("Metric submission failed", extra={"error": str(exc)})

    system._call_hook("before_recall", query, context, top_k, memory_type)
    with system.recall_latency.labels(system.namespace).time():
        _maybe_submit(lambda: system.recall_count.labels(system.namespace).inc())
        if context:
            results = find_hybrid_with_context_op(
                system, query, context, top_k=top_k, memory_type=memory_type
            )
        else:
            if getattr(system, "hybrid_recall_default", True):
                scored = hybrid_recall_with_scores_op(
                    system, query, top_k=top_k, memory_type=memory_type
                )
                results = [r.get("payload") for r in scored if r.get("payload")]
            else:
                results = find_hybrid_by_type_op(
                    system, query, top_k=top_k, memory_type=memory_type
                )
    system._call_hook("after_recall", query, context, top_k, memory_type, results)
    return results


def hybrid_recall_op(
    system: "SomaFractalMemoryEnterprise",
    query: str,
    *,
    top_k: int = 5,
    memory_type: Optional["MemoryType"] = None,
    exact: bool = True,
    case_sensitive: bool = False,
    terms: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Return payload-only results from hybrid scoring."""
    scored = hybrid_recall_with_scores_op(
        system,
        query,
        terms=terms,
        top_k=top_k,
        memory_type=memory_type,
        exact=exact,
        case_sensitive=case_sensitive,
    )
    return [r.get("payload") for r in scored if r.get("payload")]


def hybrid_recall_with_scores_op(
    system: "SomaFractalMemoryEnterprise",
    query: str,
    *,
    terms: list[str] | None = None,
    boost: float | None = None,
    top_k: int = 5,
    memory_type: Optional["MemoryType"] = None,
    exact: bool = True,
    case_sensitive: bool = False,
) -> list[dict[str, Any]]:
    """Hybrid retrieval combining vector similarity with term boosts."""
    if not terms:
        try:
            derived: list[str] = []
            derived += re.findall(r'"([^"]+)"|\'([^\']+)\'', query)
            flat: list[str] = []
            for tup in derived:
                if isinstance(tup, tuple):
                    for s in tup:
                        if s:
                            flat.append(s)
                elif tup:
                    flat.append(tup)
            derived = flat
            derived += re.findall(r"0x[0-9a-fA-F]+", query)
            derived += [w for w in re.findall(r"[A-Za-z0-9_\-]+", query) if len(w) >= 4]
            seen: set[str] = set()
            terms = [x for x in derived if not (x in seen or seen.add(x))]
        except Exception:
            terms = []

    if boost is None:
        boost = getattr(system, "_hybrid_boost", 2.0)

    qv = system.embed_text(query)
    try:
        mult = float(getattr(system, "_hybrid_candidate_multiplier", 4.0))
    except Exception:
        mult = 4.0
    search_k = max(int(top_k), int(math.ceil(top_k * mult)))
    vec_hits = []
    try:
        vec_hits = system.vector_store.search(qv.flatten().tolist(), top_k=search_k)
    except Exception:
        vec_hits = []

    terms = terms or []
    terms_cmp = [t.lower() for t in terms] if not case_sensitive else terms

    def term_match_count(payload: dict[str, Any]) -> int:
        if not terms_cmp:
            return 0
        cnt = 0
        try:
            for s in _iter_string_fields(payload):
                if s is None:
                    continue
                s_cmp = s if case_sensitive else s.lower()
                for t in terms_cmp:
                    if exact:
                        if s_cmp == t:
                            cnt += 1
                    else:
                        if t in s_cmp:
                            cnt += 1
        except Exception as exc:
            logger.debug("Term match count failed", extra={"error": str(exc)})
        return cnt

    def coord_key(payload: dict[str, Any]) -> str:
        c = payload.get("coordinate")
        return repr(tuple(c)) if isinstance(c, list) else json.dumps(payload, sort_keys=True)

    combined: dict[str, dict[str, Any]] = {}

    for h in vec_hits:
        payload = getattr(h, "payload", {}) or {}
        if memory_type and payload.get("memory_type") != memory_type.value:
            continue
        base = float(getattr(h, "score", 0.0) or 0.0)
        b = float(boost) * term_match_count(payload)
        key = coord_key(payload)
        cur = combined.get(key)
        score = base + b
        if not cur or score > float(cur.get("score", -1e9)):
            combined[key] = {"payload": payload, "score": score}

    if terms_cmp:
        from .retrieve import iter_memories_op

        for payload in iter_memories_op(system):
            if memory_type and payload.get("memory_type") != memory_type.value:
                continue
            if term_match_count(payload) > 0:
                try:
                    pv = system.embed_text(json.dumps(payload))
                    base = float(np.dot(pv.flatten(), qv.flatten()))
                except Exception:
                    base = 0.0
                score = base + float(boost) * term_match_count(payload)
                key = coord_key(payload)
                cur = combined.get(key)
                if not cur or score > float(cur.get("score", -1e9)):
                    combined[key] = {"payload": payload, "score": score}

    ranked = sorted(combined.values(), key=lambda x: float(x.get("score", 0.0)), reverse=True)
    return ranked[:top_k]


def keyword_search_op(
    system: "SomaFractalMemoryEnterprise",
    term: str,
    *,
    exact: bool = True,
    case_sensitive: bool = False,
    top_k: int = 50,
    memory_type: Optional["MemoryType"] = None,
) -> list[dict[str, Any]]:
    """Scan payloads and return those matching the term."""
    term_cmp = term if case_sensitive else term.lower()

    def matches(payload: dict[str, Any]) -> bool:
        try:
            for s in _iter_string_fields(payload):
                if s is None:
                    continue
                s_cmp = s if case_sensitive else s.lower()
                if exact:
                    if s_cmp == term_cmp:
                        return True
                else:
                    if term_cmp in s_cmp:
                        return True
        except Exception:
            return False
        return False

    try:
        from ..implementations.storage import PostgresKeyValueStore

        if isinstance(getattr(system.kv_store, "pg_store", system.kv_store), PostgresKeyValueStore):
            pg: PostgresKeyValueStore = getattr(system.kv_store, "pg_store", system.kv_store)
            memtype_str = memory_type.value if memory_type else None
            db_hits = pg.search_text(
                system.namespace,
                term if case_sensitive else term.lower(),
                case_sensitive=case_sensitive,
                limit=top_k * 5,
                memory_type=memtype_str,
            )
            filtered: list[dict[str, Any]] = []
            for p in db_hits:
                if memory_type and p.get("memory_type") != memtype_str:
                    continue
                if matches(p):
                    filtered.append(p)
                    if len(filtered) >= top_k:
                        break
            if filtered:
                return filtered[:top_k]
    except Exception as e:
        logger.debug(f"Postgres search fallback: {e}")

    from .retrieve import iter_memories_op

    out: list[dict[str, Any]] = []
    for payload in iter_memories_op(system):
        if memory_type and payload.get("memory_type") != memory_type.value:
            continue
        if matches(payload):
            out.append(payload)
            if len(out) >= top_k:
                break
    return out


def find_hybrid_with_context_op(
    system: "SomaFractalMemoryEnterprise",
    query: str,
    context: dict[str, Any],
    top_k: int = 5,
    memory_type: Optional["MemoryType"] = None,
    **kwargs,
) -> list[dict[str, Any]]:
    """Find memories using hybrid search with context."""
    context_str = json.dumps(context, sort_keys=True)
    full_query = f"{query} [CTX] {context_str}"
    results = find_hybrid_by_type_op(
        system, full_query, top_k=top_k, memory_type=memory_type, **kwargs
    )

    def score(mem):
        s = 0.0
        if "timestamp" in mem:
            s += 1.0 / (1 + (time.time() - mem["timestamp"]))
        if "access_count" in mem:
            s += 0.1 * mem["access_count"]
        return s

    return sorted(results, key=score, reverse=True)


def find_hybrid_by_type_op(
    system: "SomaFractalMemoryEnterprise",
    query: str,
    top_k: int = 5,
    memory_type: Optional["MemoryType"] = None,
    filters: dict[str, Any] | None = None,
    **kwargs,
) -> list[dict[str, Any]]:
    """Find memories using hybrid search, optionally filtered by type."""
    if system.fast_core_enabled:
        payloads = _fast_search_op(system, query, top_k, memory_type, filters)
    else:
        query_vector = system.embed_text(query)
        results = system.vector_store.search(query_vector.flatten().tolist(), top_k=top_k)
        weighted = []
        for r in results:
            payload = getattr(r, "payload", {}) or {}
            base_score = float(getattr(r, "score", 0.0) or 0.0)
            query_token = query.lower()
            token_present = any(
                isinstance(v, str) and query_token in v.lower() for v in payload.values()
            )
            token_flag = 1 if token_present else 0
            importance_norm = float(payload.get("importance_norm", 0.0) or 0.0)
            weighted.append((payload, token_flag, importance_norm, base_score))
        if filters:
            weighted = [
                (p, t, i, s)
                for p, t, i, s in weighted
                if all(p.get(k) == v for k, v in filters.items())
            ]
        weighted.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)
        payloads = [p for p, _, _, _ in weighted[:top_k]]
    if memory_type:
        return [p for p in payloads if p.get("memory_type") == memory_type.value]
    return payloads


def _fast_search_op(
    system: "SomaFractalMemoryEnterprise",
    query: str,
    top_k: int,
    memory_type: Optional["MemoryType"],
    filters: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Fast core search using contiguous slabs."""
    if system._fast_size == 0:
        return []
    qv = system.embed_text(query)
    q = qv[0] if qv.shape[0] == 1 else qv
    sims = system._fast_vectors[: system._fast_size] @ q
    if not getattr(system, "_allow_negative", False):
        np.maximum(sims, 0.0, out=sims)
    sims *= system._fast_importance[: system._fast_size]
    k = min(top_k, system._fast_size)
    if k <= 0:
        return []
    idx = np.argpartition(sims, -k)[-k:]
    idx = idx[np.argsort(sims[idx])[::-1]]
    out: list[dict[str, Any]] = []
    for i in idx:
        payload = system._fast_payloads[i]
        if not payload:
            continue
        if memory_type and payload.get("memory_type") != memory_type.value:
            continue
        if filters and not all(payload.get(fk) == fv for fk, fv in filters.items()):
            continue
        out.append(payload)
        if len(out) >= top_k:
            break
    return out


def find_by_coordinate_range_op(
    system: "SomaFractalMemoryEnterprise",
    min_coord: tuple[float, ...],
    max_coord: tuple[float, ...],
    memory_type: Optional["MemoryType"] = None,
) -> list[dict[str, Any]]:
    """Find memories within a coordinate range."""
    from .retrieve import get_all_memories_op

    def inside(c: list[float]) -> bool:
        try:
            return all(
                min_coord[i] <= c[i] <= max_coord[i]
                for i in range(min(len(min_coord), len(max_coord), len(c)))
            )
        except Exception:
            return False

    out: list[dict[str, Any]] = []
    for m in get_all_memories_op(system):
        coord = m.get("coordinate")
        if coord is None:
            continue
        if inside(coord):
            if memory_type is None or m.get("memory_type") == memory_type.value:
                out.append(m)
    return out
