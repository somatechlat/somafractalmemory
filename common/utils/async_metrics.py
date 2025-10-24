"""Simple async metrics queue used to offload Prometheus metric updates.

This is intentionally minimal: a background thread consumes a queue of callables
and executes them. It's opt-in via environment variable `SOMA_ASYNC_METRICS`.
"""

from __future__ import annotations

import threading
from collections import deque
from collections.abc import Callable

_queue: deque[Callable[[], None]] = deque()
_lock = threading.Lock()
_stop = threading.Event()


def _worker():
    while not _stop.is_set():
        fn = None
        try:
            with _lock:
                if _queue:
                    fn = _queue.popleft()
        except Exception:
            fn = None
        if fn:
            try:
                fn()
            except Exception:
                pass
        else:
            _stop.wait(0.01)


_thread = threading.Thread(target=_worker, daemon=True)
_thread.start()


def submit(fn: Callable[[], None]) -> None:
    try:
        with _lock:
            _queue.append(fn)
    except Exception:
        # If queueing fails, best-effort: swallow and let synchronous fallback run
        pass


def stop():
    _stop.set()
    try:
        _thread.join(timeout=1.0)
    except Exception:
        pass
