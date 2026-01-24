import io
from typing import List

import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel


class ImageEmbedder:
    """
    Multimodal embedder using CLIP from Transformers.
    
    This implementation uses raw Transformers to avoid bugs in wrappers
    and to match the Kaggle pipeline implementation.
    """

    def __init__(self, model_name: str = "openai/clip-vit-base-patch32") -> None:
        """
        Initialize with CLIP model.
        """
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        try:
            self.processor = CLIPProcessor.from_pretrained(model_name)
            self.model = CLIPModel.from_pretrained(model_name).to(self.device)
            self.model.eval()
        except Exception:
            # Fallback to a common CLIP model
            alt_model = "sentence-transformers/clip-ViT-B-32"
            self.processor = CLIPProcessor.from_pretrained(alt_model)
            self.model = CLIPModel.from_pretrained(alt_model).to(self.device)
            self.model.eval()

    @property
    def vector_size(self) -> int:
        if hasattr(self.model.config, "projection_dim"):
            return self.model.config.projection_dim
        return 512 # Fallback for ViT-B-32

    def embed_image(self, image: Image.Image) -> List[float]:
        """Encode a single image into a vector."""
        try:
            inputs = self.processor(images=image, return_tensors="pt").to(self.device)
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
            
            # Normalize for cosine similarity
            image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
            return image_features[0].cpu().tolist()
        except Exception as e:
            print(f"Error in embed_image: {e}")
            # Return zero vector if it fails
            return [0.0] * self.vector_size

    def embed_image_from_bytes(self, image_bytes: bytes) -> List[float]:
        """Encode an image from bytes (e.g., uploaded file)."""
        image = Image.open(io.BytesIO(image_bytes))
        # Convert to RGB if needed
        if image.mode != "RGB":
            image = image.convert("RGB")
        return self.embed_image(image)
