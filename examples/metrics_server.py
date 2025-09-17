"""
Example: Expose Prometheus metrics and exercise a basic store operation.

Run:
  python examples/metrics_server.py
Then scrape:
  http://localhost:8000/
"""

from time import sleep

from prometheus_client import start_http_server

from somafractalmemory.core import MemoryType
from somafractalmemory.factory import MemoryMode, create_memory_system


def main():
    start_http_server(8000)
    mem = create_memory_system(
        MemoryMode.LOCAL_AGENT,
        "metrics_ns",
        config={"redis": {"testing": True}, "qdrant": {"path": "./qdrant.db"}},
    )
    mem.store_memory((0.1, 0.2, 0.3), {"task": "emit metric"}, memory_type=MemoryType.EPISODIC)
    print("Metrics server on http://localhost:8000/")
    while True:
        sleep(5)


if __name__ == "__main__":
    main()
