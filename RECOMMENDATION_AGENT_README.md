# Recommendation agent (ADK) and behaviour data

## 1. Seed static behaviour data (SQLite)

Generate synthetic clicks, favourites, and purchases and insert them into **SQLite** in the project repo (`rag_app.db`). No data is written to Qdrant.

**Tables used:**
- `auth_user` – synthetic users (alice@example.com, bob@example.com, …)
- `products` – products synced from Qdrant into SQLite for the seed
- `user_interactions` – behaviour rows (view, click, wishlist, add_to_cart, purchase)

**Prerequisites:** Django migrations applied (`python run_django_migrate.py`). For product sync, `.env` with Qdrant URL/API key and product collection populated; if Qdrant is unavailable, the script uses existing products in SQLite.

```bash
python seed_behaviour_data.py
```

**Environment (optional):**
- `SEED_INTERACTIONS_PER_USER` – interactions per user (default `25`)
- `SEED_MAX_PRODUCTS` – max products to sync and use (default `500`)

**Synthetic users:** `alice@example.com`, `bob@example.com`, `carol@example.com`, `dave@example.com`, `eve@example.com`, etc. Each gets random views, wishlists, cart adds, and purchases stored in `user_interactions`.

---

## 2. ADK recommendation agent

Base agent built with [Google ADK](https://github.com/google/adk-python) that uses the seeded behaviour data (via the FinFit API) to recommend products.

**Install:**

```bash
pip install google-adk
```

**Configure:** Copy `recommendation_agent/.env.example` to `recommendation_agent/.env` and set `GOOGLE_API_KEY` (from [Google AI Studio](https://aistudio.google.com/app/apikey)).

**Run FinFit API** (so the agent can call recommendations):

```bash
uvicorn app:app --reload
```

**Run the agent:**

From the **project root** (parent of `recommendation_agent/`):

```bash
# CLI
adk run recommendation_agent

# Web UI (e.g. http://localhost:8001)
adk web --port 8001
```

**Example prompts:**
- “Recommend products for alice@example.com”
- “What do you suggest for bob@example.com?”
- “List example users” (uses `list_seeded_users`)

The agent uses:
- **get_recommendations(user_email, limit)** – calls `GET /api/recommendations?user_email=...&limit=...`
- **list_seeded_users()** – returns example user emails with seeded behaviour
