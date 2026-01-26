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
    COLLECTION_NAME: str = "amazon30015"
    VECTOR_NAME: str = "text_dense"
    
    # Embeddings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    class Config:
        env_file = ".env"

settings = Settings()
