# prediction_manager.py - Handles prediction and LLM integration

import logging
from typing import Any

from .interfaces.prediction import IPredictionProvider

logger = logging.getLogger(__name__)


class PredictionManager:
    def __init__(self, prediction_provider: IPredictionProvider | None):
        self.prediction_provider = prediction_provider

    def predict(self, value: dict[str, Any]) -> tuple[Any, float]:
        if not self.prediction_provider:
            raise ValueError("Prediction provider not available")
        return self.prediction_provider.predict(value)

    def health_check(self) -> bool:
        if self.prediction_provider:
            try:
                return self.prediction_provider.health_check()
            except Exception:
                return False
        return True
