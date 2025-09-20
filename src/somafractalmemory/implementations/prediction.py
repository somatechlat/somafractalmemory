from typing import Any, Dict, Tuple

import numpy as np

from somafractalmemory.interfaces.prediction import IPredictionProvider


def _safe_requests_get(url: str, timeout: float = 5.0):
    try:
        import requests  # type: ignore

        return requests.get(url, timeout=timeout)
    except Exception:
        return None


class NoPredictionProvider(IPredictionProvider):
    def predict(self, memory_data: Dict[str, Any]) -> Tuple[str, float]:
        return "", 0.0

    def health_check(self) -> bool:
        return True


class OllamaPredictionProvider(IPredictionProvider):
    def __init__(self, host="http://localhost:11434"):
        self.host = host

    def predict(self, memory_data: Dict[str, Any]) -> Tuple[str, float]:
        predicted_outcome = "Predicted by Ollama."
        confidence = np.random.uniform(0.7, 0.99)
        return predicted_outcome, confidence

    def health_check(self) -> bool:
        resp = _safe_requests_get(self.host)
        return bool(resp and resp.status_code == 200)


class ExternalPredictionProvider(IPredictionProvider):
    def __init__(self, api_key: str, endpoint: str):
        self.api_key = api_key
        self.endpoint = endpoint

    def predict(self, memory_data: Dict[str, Any]) -> Tuple[str, float]:
        predicted_outcome = "Predicted by External API."
        confidence = np.random.uniform(0.8, 0.99)
        return predicted_outcome, confidence

    def health_check(self) -> bool:
        resp = _safe_requests_get(self.endpoint)
        return bool(resp and resp.status_code == 200)
