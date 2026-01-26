from typing import List
from groq import Groq
from fastembed import TextEmbedding
from .config import settings

# Initialize Groq Client
groq_client = Groq(api_key=settings.GROQ_API_KEY)

from sentence_transformers import SentenceTransformer

# Initialize Embedding Model
# "all-MiniLM-L6-v2" is used for consistency with the Search API indexing.
embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)

def get_embedding(text: str) -> List[float]:
    """Generates an embedding for a single text string."""
    # Ensure normalization for cosine similarity
    embedding = embedding_model.encode(
        text, 
        convert_to_numpy=True, 
        normalize_embeddings=True
    )
    return embedding.tolist()

def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Generates embeddings for a list of texts."""
    embeddings = embedding_model.encode(
        texts, 
        convert_to_numpy=True, 
        normalize_embeddings=True
    )
    return embeddings.tolist()

def query_llm(context: str, question: str) -> str:
    """Sends the context and question to Groq LLM and returns the answer."""
    
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
    
    chat_completion = groq_client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model=settings.GROQ_MODEL,
        temperature=0.0, # Strategic for RAG (deterministic)
    )
    
    return chat_completion.choices[0].message.content
