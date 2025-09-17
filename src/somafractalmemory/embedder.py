# embedder.py - Handles multi-modal embeddings

import logging

import numpy as np

logger = logging.getLogger(__name__)


class MultiModalEmbedder:
    """Handles multi-modal embedding (text, image, audio)."""

    def __init__(
        self,
        text_model_name="microsoft/codebert-base",
        image_model_name="openai/clip-vit-base-patch16",
        audio_model_name="openai/whisper-base",
    ):
        self.text_model_name = text_model_name
        self.image_model_name = image_model_name
        self.audio_model_name = audio_model_name
        self._load_models()

    def _load_models(self):
        # Text embedding
        try:
            from transformers import AutoModel, AutoTokenizer

            self.text_tokenizer = AutoTokenizer.from_pretrained(self.text_model_name)
            self.text_model = AutoModel.from_pretrained(self.text_model_name, use_safetensors=True)
        except Exception as e:
            logger.warning(f"Text model loading failed: {e}")
            self.text_tokenizer = None
            self.text_model = None

        # Image embedding
        try:
            from transformers import CLIPModel, CLIPProcessor

            self.image_processor = CLIPProcessor.from_pretrained(self.image_model_name)
            self.image_model = CLIPModel.from_pretrained(
                self.image_model_name, use_safetensors=True
            )
        except Exception as e:
            logger.warning(f"Image model loading failed: {e}")
            self.image_processor = None
            self.image_model = None

        # Audio embedding
        try:
            from transformers import WhisperModel, WhisperProcessor

            self.audio_processor = WhisperProcessor.from_pretrained(self.audio_model_name)
            self.audio_model = WhisperModel.from_pretrained(
                self.audio_model_name, use_safetensors=True
            )
        except Exception as e:
            logger.warning(f"Audio model loading failed: {e}")
            self.audio_processor = None
            self.audio_model = None

    def embed_text(self, text: str) -> np.ndarray:
        if self.text_tokenizer is None or self.text_model is None:
            # Fallback to hash-based embedding with consistent dimensions
            import hashlib

            h = hashlib.blake2b(text.encode("utf-8")).digest()
            arr = np.frombuffer(h, dtype=np.uint8).astype("float32")
            # Ensure consistent 768 dimensions
            if arr.size < 768:
                reps = int(np.ceil(768 / arr.size))
                arr = np.tile(arr, reps)
            elif arr.size > 768:
                arr = arr[:768]
            return arr.reshape(1, -1)

        try:
            inputs = self.text_tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            outputs = self.text_model(**inputs)
            emb = outputs.last_hidden_state.mean(dim=1).detach().cpu().numpy().astype("float32")
            # Ensure consistent dimensions
            if emb.shape[1] != 768:
                if emb.shape[1] < 768:
                    # Pad with zeros
                    pad = np.zeros((emb.shape[0], 768 - emb.shape[1]), dtype=emb.dtype)
                    emb = np.concatenate([emb, pad], axis=1)
                else:
                    # Truncate
                    emb = emb[:, :768]
            return emb
        except Exception as e:
            logger.warning(f"Text embedding failed: {e}, using hash fallback")
            # Fallback to hash-based embedding
            h = hashlib.blake2b(text.encode("utf-8")).digest()
            arr = np.frombuffer(h, dtype=np.uint8).astype("float32")
            if arr.size < 768:
                reps = int(np.ceil(768 / arr.size))
                arr = np.tile(arr, reps)
            elif arr.size > 768:
                arr = arr[:768]
            return arr.reshape(1, -1)

    def embed_image(self, image_bytes: bytes) -> np.ndarray:
        if self.image_processor is None or self.image_model is None:
            raise NotImplementedError("Image embedding model not loaded.")
        import io

        from PIL import Image

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        inputs = self.image_processor(images=image, return_tensors="pt")
        outputs = self.image_model(**inputs)
        emb = outputs.pooler_output.detach().cpu().numpy().astype("float32")
        return emb

    def embed_audio(self, audio_bytes: bytes) -> np.ndarray:
        if self.audio_processor is None or self.audio_model is None:
            raise NotImplementedError("Audio embedding model not loaded.")
        import io

        import torchaudio

        waveform, sample_rate = torchaudio.load(io.BytesIO(audio_bytes))
        inputs = self.audio_processor(waveform, sampling_rate=sample_rate, return_tensors="pt")
        outputs = self.audio_model(**inputs)
        emb = outputs.last_hidden_state.mean(dim=1).detach().cpu().numpy().astype("float32")
        return emb

    def embed(self, data: str | bytes, modality: str = "text") -> np.ndarray:
        if modality == "text":
            return self.embed_text(data)
        elif modality == "image":
            return self.embed_image(data)
        elif modality == "audio":
            return self.embed_audio(data)
        else:
            raise ValueError(f"Unsupported modality: {modality}")
