import os

from qdrant_client import QdrantClient


def get_qdrant_client() -> QdrantClient:
    """
    Create a Qdrant client from environment variables.

    Required env vars:
      - QDRANT_URL
      - QDRANT_API_KEY
    """
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")

    if not url or not api_key:
        raise RuntimeError("Missing QDRANT_URL or QDRANT_API_KEY environment variables.")

    return QdrantClient(url=url, api_key=api_key)


def qdrant_ping() -> dict:
    """
    Simple connectivity check.
    Returns a small dict with status and collection count.
    """
    client = get_qdrant_client()
    cols = client.get_collections()
    return {"ok": True, "collections": len(cols.collections)}

