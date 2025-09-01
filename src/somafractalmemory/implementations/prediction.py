from somafractalmemory.interfaces.prediction import IPredictionProvider
from typing import Tuple, Dict, Any, Optional
import numpy as np

def _safe_requests_get(url: str) -> Optional[Any]:
    """Lazily import requests and perform a GET; return None on failure/missing."""
    try:
        import requests  # type: ignore
        return requests.get(url)
    except Exception:
        return None

class NoPredictionProvider(IPredictionProvider):
    def predict(self, memory_data: Dict[str, Any]) -> Tuple[str, float]:
        return "", 0.0

    def health_check(self) -> bool:
        return True

class OllamaPredictionProvider(IPredictionProvider):
    def __init__(self, host: str = 'http://localhost:11434') -> None:
        self.host = host

    def predict(self, memory_data: Dict[str, Any]) -> Tuple[str, float]:
        # Placeholder for actual Ollama call
        predicted_outcome = "Predicted by Ollama."
        confidence = np.random.uniform(0.7, 0.99)
        return predicted_outcome, confidence

    def health_check(self) -> bool:
        resp = _safe_requests_get(self.host)
        return bool(resp and resp.status_code == 200)

class ExternalPredictionProvider(IPredictionProvider):
    def __init__(self, api_key: str, endpoint: str) -> None:
        self.api_key = api_key
        self.endpoint = endpoint

    def predict(self, memory_data: Dict[str, Any]) -> Tuple[str, float]:
        # Placeholder for actual external API call
        predicted_outcome = "Predicted by External API."
        confidence = np.random.uniform(0.8, 0.99)
        return predicted_outcome, confidence

    def health_check(self) -> bool:
        resp = _safe_requests_get(self.endpoint)
        return bool(resp and resp.status_code == 200)
