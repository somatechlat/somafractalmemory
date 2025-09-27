from typing import List

from transformers import AutoModel, AutoTokenizer

from somafractalmemory.interfaces.providers import IEmbeddingProvider


class TransformersEmbeddingProvider(IEmbeddingProvider):
    """An embedding provider that uses Hugging Face Transformers."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)

    def embed_text(self, text: str) -> List[float]:
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        inputs = self.tokenizer(
            texts, padding=True, truncation=True, return_tensors="pt", max_length=512
        )
        with self.model.no_grad():
            outputs = self.model(**inputs)
        # Perform pooling
        embeddings = outputs.last_hidden_state.mean(dim=1)
        return embeddings.cpu().numpy().tolist()
