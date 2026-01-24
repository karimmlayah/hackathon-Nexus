from __future__ import annotations

from typing import List

from sentence_transformers import SentenceTransformer


class Embedder:
    """
    Small wrapper around SentenceTransformers.

    Model requirement: "all-MiniLM-L6-v2"
    - Embedding dimension: 384
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)

    @property
    def vector_size(self) -> int:
        return self._model.get_sentence_embedding_dimension()

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        vectors = self._model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,  # cosine similarity-friendly
            show_progress_bar=False,
        )
        return vectors.tolist()

    def embed_text(self, text: str) -> List[float]:
        return self.embed_texts([text])[0]

