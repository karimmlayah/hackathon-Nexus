import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App
    APP_NAME: str = "RAG System (Groq + Qdrant)"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    FIXED_DATASET_PATH: str = r"C:\Users\Mega-PC\Downloads\finfit (2).csv"
    
    # LLM
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    
    # Qdrant
    QDRANT_URL: str = ":memory:" # Default to in-memory if no URL provided
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "amazon30015"  # From .env: QDRANT_COLLECTION
    COLLECTION_NAME: str = "amazon30015"
    VECTOR_NAME: str = "text_dense"
    
    # Embeddings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields from .env

    def __init__(self, **data):
        super().__init__(**data)
        # Use QDRANT_COLLECTION from env if available
        if self.QDRANT_COLLECTION and self.QDRANT_COLLECTION != "amazon30015":
            self.COLLECTION_NAME = self.QDRANT_COLLECTION

settings = Settings()
