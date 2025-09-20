from typing import Any, Dict, Tuple

from somafractalmemory.interfaces.prediction import IPredictionProvider


class NoPredictionProvider(IPredictionProvider):
    def predict(self, memory_data: Dict[str, Any]) -> Tuple[str, float]:
        return "", 0.0

    def health_check(self) -> bool:
        return True
