"""
ADK base agent for product recommendations.
Uses behaviour data (clicks, favourites, purchases) from the FinFit API to suggest products.

Requires:
  - FinFit API running (e.g. uvicorn app:app --reload) for GET /api/recommendations
  - GOOGLE_API_KEY in .env for the LLM (Gemini)

Run:
  adk run recommendation_agent
  or
  adk web --port 8001
  (from parent directory that contains recommendation_agent/)
"""
import os
import json
import urllib.request
import urllib.parse
import urllib.error

# Default API base (override with RECOMMENDATION_API_BASE env)
API_BASE = os.environ.get("RECOMMENDATION_API_BASE", "http://127.0.0.1:8000")


def get_recommendations(user_email: str, limit: int = 6) -> dict:
    """
    Get personalized product recommendations for a user based on their behaviour
    (clicks, favourites, cart, purchases) stored in the database.
    Returns a dict with success, count, recommendations (list of products), and message.
    """
    try:
        url = f"{API_BASE}/api/recommendations?user_email={urllib.parse.quote(user_email)}&limit={limit}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        return data
    except urllib.error.URLError as e:
        return {"success": False, "count": 0, "recommendations": [], "message": str(e)}
    except Exception as e:
        return {"success": False, "count": 0, "recommendations": [], "message": str(e)}


def list_seeded_users() -> dict:
    """
    Return a short list of example user emails that have seeded behaviour data.
    Use these emails with get_recommendations to test.
    """
    return {
        "users": [
            "alice@example.com",
            "bob@example.com",
            "carol@example.com",
            "dave@example.com",
            "eve@example.com",
        ],
        "message": "Run get_recommendations(user_email=..., limit=6) for personalized suggestions.",
    }


# ADK agent
try:
    from google.adk.agents.llm_agent import Agent

    root_agent = Agent(
        model=os.environ.get("ADK_MODEL", "gemini-2.0-flash"),
        name="recommendation_agent",
        description="Recommends products based on user behaviour (clicks, favourites, purchases). Use get_recommendations for a user email, or list_seeded_users to see example users.",
        instruction=(
            "You are a helpful shopping recommendation assistant. "
            "You use behaviour data (clicks, favourites, cart, purchases) to suggest products. "
            "When the user asks for recommendations, use get_recommendations(user_email=..., limit=6) "
            "with their email (or suggest they try one of the example users from list_seeded_users). "
            "Summarize the recommended products in a friendly way: name, price, and why it was recommended if present."
        ),
        tools=[get_recommendations, list_seeded_users],
    )
except ImportError:
    root_agent = None  # google-adk not installed
