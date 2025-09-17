from abc import ABC, abstractmethod
from typing import Any


class IPredictionProvider(ABC):
    @abstractmethod
    def predict(self, memory_data: dict[str, Any]) -> tuple[str, float]:
        """
        Takes memory data and returns a predicted outcome (str) and confidence (float).
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Returns True if the provider is healthy, False otherwise.
        """
        pass
