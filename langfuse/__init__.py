class Langfuse:
    """Lightweight stub used when the optional langfuse package is not installed."""

    def __init__(self, *args, **kwargs):
        pass

    def log(self, *args, **kwargs):
        pass

    def __getattr__(self, _name):
        def _noop(*_a, **_k):
            return None

        return _noop


__all__ = ["Langfuse"]
