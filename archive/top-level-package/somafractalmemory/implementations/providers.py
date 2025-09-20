import os
from typing import List

from transformers import AutoModel, AutoTokenizer

from somafractalmemory.interfaces.providers import IEmbeddingProvider


class TransformersEmbeddingProvider(IEmbeddingProvider):
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        rev = os.getenv("SOMA_MODEL_REV")
        kwargs = {"revision": rev} if rev else {}

        allow_unpinned = os.getenv("SOMA_ALLOW_UNPINNED_HF", "false").lower() == "true"
        if not rev and not allow_unpinned:
            self.tokenizer = None
            self.model = None
            return

        self.tokenizer = AutoTokenizer.from_pretrained(model_name, **kwargs)
        self.model = AutoModel.from_pretrained(model_name, **kwargs)

    def embed_text(self, text: str) -> List[float]:
        return self.embed_texts([text])[0]
