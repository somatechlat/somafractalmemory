from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple


class IPredictionProvider(ABC):
    @abstractmethod
    def predict(self, memory_data: Dict[str, Any]) -> Tuple[str, float]:
        """
        Takes memory data and returns a predicted outcome (str) and confidence (float).
        """

    @abstractmethod
    def health_check(self) -> bool:
        """
        Returns True if the provider is healthy, False otherwise.
        """
