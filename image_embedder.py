import io
from typing import List

import torch
from PIL import Image
from sentence_transformers import SentenceTransformer


class ImageEmbedder:
    """
    Multimodal embedder using CLIP from SentenceTransformers.
    """

    def __init__(self, model_name: str = "clip-ViT-B-32") -> None:
        """
        Initialize with CLIP model.
        """
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # SentenceTransformer handles the loading and CPU/GPU placement
        self.model = SentenceTransformer(model_name, device=self.device)

    @property
    def vector_size(self) -> int:
        return self.model.get_sentence_embedding_dimension()

    def embed_image(self, image: Image.Image) -> List[float]:
        """Encode a single image into a vector."""
        try:
            # sentence-transformers encode method already handles normalization if desired,
            # and works with PIL images directly.
            embedding = self.model.encode(
                image, 
                convert_to_numpy=True, 
                normalize_embeddings=True
            )
            return embedding.tolist()
        except Exception as e:
            print(f"Error in embed_image: {e}")
            # Return zero vector if it fails
            return [0.0] * self.vector_size

    def embed_image_from_bytes(self, image_bytes: bytes) -> List[float]:
        """Encode an image from bytes (e.g., uploaded file)."""
        image = Image.open(io.BytesIO(image_bytes))
        # Convert to RGB if needed (standard for CLIP)
        if image.mode != "RGB":
            image = image.convert("RGB")
        return self.embed_image(image)
