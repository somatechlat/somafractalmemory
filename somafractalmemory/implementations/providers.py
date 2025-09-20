import os
from typing import Dict, List, Tuple

from transformers import AutoModel, AutoTokenizer

from somafractalmemory.interfaces.providers import IEmbeddingProvider, IPredictionProvider


class TransformersEmbeddingProvider(IEmbeddingProvider):
    """An embedding provider that uses Hugging Face Transformers.

    The provider supports optional pinning of the model revision via the
    `SOMA_MODEL_REV` environment variable for reproducible builds. Unpinned
    downloads are allowed only when explicitly opted-in by setting
    `SOMA_ALLOW_UNPINNED_HF=true` in the environment.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        rev = os.getenv("SOMA_MODEL_REV")
        kwargs = {"revision": rev} if rev else {}

        allow_unpinned = os.getenv("SOMA_ALLOW_UNPINNED_HF", "false").lower() == "true"
        if not rev and not allow_unpinned:
            # Keep tokenizer/model unset to force fallback embeddings in secure environments.
            self.tokenizer = None
            self.model = None
            return

        # Load model (pinned or explicitly opted-in unpinned).  # nosec B615
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, **kwargs)
        self.model = AutoModel.from_pretrained(model_name, **kwargs)

    def embed_text(self, text: str) -> List[float]:
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if self.tokenizer is None or self.model is None:
            # Fallback behavior is implemented at a higher layer (core.embed_text).
            raise RuntimeError("Transformers model not available")
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

    def generate_prediction(self, data: Dict[str, object]) -> Tuple[str, float]:
        """Returns a dummy prediction."""
        return "This is a dummy prediction.", 0.9
