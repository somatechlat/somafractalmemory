"""Simple async metrics queue used to offload Prometheus metric updates.

This is intentionally minimal: a background thread consumes a queue of callables
and executes them. It's opt-in via environment variable `SOMA_ASYNC_METRICS`.
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from collections.abc import Callable

logger = logging.getLogger(__name__)

_queue: deque[Callable[[], None]] = deque()
_lock = threading.Lock()
_stop = threading.Event()


def _worker():
    """Execute worker."""

    while not _stop.is_set():
        fn = None
        try:
            with _lock:
                if _queue:
                    fn = _queue.popleft()
        except Exception as e:
            logger.debug("Failed to dequeue metric task: %s", e)
            fn = None
        if fn:
            try:
                fn()
            except Exception as e:
                logger.debug("Metric task execution failed: %s", e)
        else:
            _stop.wait(0.01)


_thread = threading.Thread(target=_worker, daemon=True)
_thread.start()


def submit(fn: Callable[[], None]) -> None:
    """Execute submit.

    Args:
        fn: The fn.
    """

    try:
        with _lock:
            _queue.append(fn)
    except Exception as e:
        # Log the failure but allow synchronous fallback to proceed
        logger.debug("Failed to queue metric task, synchronous fallback will run: %s", e)


def stop():
    """Execute stop."""

    _stop.set()
    try:
        _thread.join(timeout=1.0)
    except Exception:
        pass
