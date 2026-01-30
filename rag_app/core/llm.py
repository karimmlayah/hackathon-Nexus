from typing import List
from groq import Groq
from groq._exceptions import APIError, APIConnectionError
from sentence_transformers import SentenceTransformer
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Groq Client with error handling
try:
    groq_client = Groq(api_key=settings.GROQ_API_KEY, timeout=30.0)
    logger.info("✅ Groq client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Groq client: {str(e)}")
    groq_client = None

# Initialize Embedding Model
try:
    embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
    logger.info(f"✅ Embedding model '{settings.EMBEDDING_MODEL}' loaded successfully")
except Exception as e:
    logger.error(f"Failed to load embedding model: {str(e)}")
    embedding_model = None

def get_embedding(text: str) -> List[float]:
    """Generates an embedding for a single text string."""
    if embedding_model is None:
        raise RuntimeError(
            f"Embedding model '{settings.EMBEDDING_MODEL}' not initialized. "
            "Check your environment and model availability."
        )
    
    try:
        # Ensure normalization for cosine similarity
        embedding = embedding_model.encode(
            text, 
            convert_to_numpy=True, 
            normalize_embeddings=True
        )
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Embedding generation failed: {str(e)}")
        raise RuntimeError(f"Failed to generate embedding: {str(e)}")

def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Generates embeddings for a list of texts."""
    if embedding_model is None:
        raise RuntimeError("Embedding model not initialized")
    
    try:
        embeddings = embedding_model.encode(
            texts, 
            convert_to_numpy=True, 
            normalize_embeddings=True
        )
        return embeddings.tolist()
    except Exception as e:
        logger.error(f"Batch embedding generation failed: {str(e)}")
        raise RuntimeError(f"Failed to generate embeddings: {str(e)}")

def query_llm(context: str, question: str) -> str:
    """
    Sends the context and question to Groq LLM and returns the answer.
    Includes retry logic for transient API failures.
    """
    if groq_client is None:
        raise RuntimeError(
            "Groq client not initialized. Check GROQ_API_KEY in your .env file."
        )
    
    prompt = f"""
    You are a professional Shopping Assistant. Your goal is to help users find the best products from our catalog.

    CRITICAL RULES:
    1. USE ONLY THE PRODUCTS LISTED BELOW.
    2. DO NOT hallucinate products, features, or prices that are not explicitly in the context.
    3. If no relevant products are found in the context, politely inform the user.
    4. Provide helpful advice for the products you recommend.
    5. Format your answer using markdown for better readability.

    PRODUCT CONTEXT (From amazon30015):
    {context}
    
    USER QUERY:
    {question}
    
    ASSISTANT ANSWER:
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=settings.GROQ_MODEL,
                temperature=0.0,  # Deterministic for RAG
                max_tokens=1024,
            )
            return chat_completion.choices[0].message.content
        except APIConnectionError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"LLM API connection error (attempt {attempt + 1}). Retrying in {wait_time}s: {str(e)}")
                import time
                time.sleep(wait_time)
            else:
                logger.error(f"LLM API connection failed after {max_retries} attempts")
                raise APIConnectionError("Failed to connect to Groq API. Please check your connection.")
        except APIError as e:
            logger.error(f"Groq API error: {str(e)}")
            raise APIError(f"LLM service error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected LLM error: {str(e)}")
            raise RuntimeError(f"Unexpected error querying LLM: {str(e)}")

def shorten_titles(titles: List[str], max_chars: int = 35) -> List[str]:
    """
    Use Groq LLM to shorten product titles to fit a fixed-width box (e.g. card).
    Returns one shortened title per input, in the same order.
    Falls back to truncation if LLM fails.
    """
    if not titles:
        return []
    # Fallback: truncate with ellipsis
    def truncate(s: str) -> str:
        s = (s or "").strip()
        if len(s) <= max_chars:
            return s
        return s[: max_chars - 1].rsplit(" ", 1)[0] if " " in s[: max_chars - 1] else s[: max_chars - 1] + "…"

    if groq_client is None:
        return [truncate(t) for t in titles]

    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(titles))
    prompt = f"""Shorten each product title below to at most {max_chars} characters. Keep the key product name. Do not add quotes or numbers.
Output ONLY the shortened titles, one per line, in the same order (line 1 = title 1, line 2 = title 2, etc.). No other text.

TITLES:
{numbered}

SHORTENED (one per line):"""

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=settings.GROQ_MODEL,
            temperature=0.0,
            max_tokens=512,
        )
        raw = (chat_completion.choices[0].message.content or "").strip()
        lines = [ln.strip() for ln in raw.split("\n") if ln.strip()]
        # Remove leading numbers/dots if LLM added them
        result = []
        for i, ln in enumerate(lines[: len(titles)]):
            cleaned = ln.lstrip("0123456789.)- ")
            if len(cleaned) > max_chars:
                cleaned = truncate(cleaned)
            result.append(cleaned or truncate(titles[i]))
        # Pad if we got fewer lines than titles
        while len(result) < len(titles):
            result.append(truncate(titles[len(result)]))
        return result[: len(titles)]
    except Exception as e:
        logger.warning(f"Shorten titles LLM failed, using truncation: {e}")
        return [truncate(t) for t in titles]