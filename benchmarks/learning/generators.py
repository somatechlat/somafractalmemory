from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any


@dataclass
class MemoryItem:
    coord: tuple[float, ...]
    payload: dict[str, Any]
    mtype: str  # "episodic" | "semantic"


@dataclass
class QueryCase:
    query: str
    kind: str  # "semantic" | "hybrid" | "keyword"
    topic: str | None
    token: str | None


def make_tokens(n: int, prefix: str = "TOK") -> list[str]:
    return [f"{prefix}{i:04d}" for i in range(n)]


def generate_dataset(
    n_topics: int = 5,
    items_per_topic: int = 10,
    seed: int = 42,
) -> tuple[list[MemoryItem], list[QueryCase]]:
    rnd = random.Random(seed)
    topics = [f"topic-{i}" for i in range(n_topics)]
    tokens = make_tokens(n_topics * items_per_topic)

    items: list[MemoryItem] = []
    queries: list[QueryCase] = []

    tok_idx = 0
    # Create items per topic with occasional token anchors
    for t in topics:
        for j in range(items_per_topic):
            token = tokens[tok_idx]
            tok_idx += 1
            coord = (float(j + 1), float(j + 2))
            text = f"{t} base note with token {token}"
            payload = {
                "text": text,
                "topic": t,
                "importance": rnd.choice([0, 1, 2, 3, 5]),
            }
            items.append(MemoryItem(coord=coord, payload=payload, mtype="episodic"))

            # For hybrid/keyword queries, we’ll use the token itself
            queries.append(QueryCase(query=token, kind="hybrid", topic=t, token=token))
            queries.append(QueryCase(query=token, kind="keyword", topic=t, token=token))

        # Add semantic-only queries per topic (no tokens)
        queries.append(QueryCase(query=f"about {t}", kind="semantic", topic=t, token=None))

    return items, queries
