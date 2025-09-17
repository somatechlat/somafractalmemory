from typing import Any

from transformers import AutoModel, AutoTokenizer

from somafractalmemory.interfaces.providers import (
    IEmbeddingProvider,
    IPredictionProvider,
)


class TransformersEmbeddingProvider(IEmbeddingProvider):
    """An embedding provider that uses Hugging Face Transformers."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        inputs = self.tokenizer(
            texts, padding=True, truncation=True, return_tensors="pt", max_length=512
        )
        with self.model.no_grad():
            outputs = self.model(**inputs)
        # Perform pooling
        embeddings = outputs.last_hidden_state.mean(dim=1)
        return embeddings.cpu().numpy().tolist()


class StubPredictionProvider(IPredictionProvider):
    """A stub implementation of the prediction provider for testing."""

    def generate_prediction(self, data: dict[str, Any]) -> tuple[str, float]:
        """Returns a dummy prediction."""
        return "This is a dummy prediction.", 0.9
