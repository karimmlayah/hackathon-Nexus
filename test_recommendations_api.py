"""Quick test: GET products -> get ids -> GET recommendations with product_ids.
Run with the server started: uvicorn app:app --reload
Override URL: set API_BASE=http://localhost:8000 or pass as first arg.
"""
import os
import sys
import requests

BASE = os.environ.get("API_BASE") or (sys.argv[1] if len(sys.argv) > 1 else None) or "http://127.0.0.1:8000"

def main():
    # 1) Get a few products to get valid ids
    try:
        r = requests.get(f"{BASE}/products?limit=3", timeout=10)
    except requests.exceptions.ConnectionError:
        print("Connexion refusée. Le serveur n'est pas démarré.")
        print("Lancez d'abord dans un autre terminal:  uvicorn app:app --reload")
        print(f"(Le script essaie d'appeler {BASE})")
        sys.exit(1)
    r.raise_for_status()
    data = r.json()
    products = data if isinstance(data, list) else data.get("products") or data.get("results") or []
    if not products:
        print("No products from /products")
        return
    ids = []
    for p in products[:3]:
        pid = p.get("id") or p.get("asin")
        if pid is not None:
            ids.append(str(pid))
    if not ids:
        print("No id/asin in products:", [list(p.keys()) for p in products[:1]])
        return
    print("Product ids for seed:", ids)

    # 2) Call recommendations by-seed (works without login; same logic as "Pour vous")
    url = f"{BASE}/api/recommendations/by-seed?product_ids={','.join(ids)}&limit=12"
    r2 = requests.get(url, timeout=15)
    print("Recommendations status:", r2.status_code)
    if r2.status_code != 200:
        print("Response:", r2.text[:500])
        return
    out = r2.json()
    recs = out.get("recommendations") or out.get("products") or []
    strategy = out.get("strategy", "")
    message = out.get("message", "")
    print("Strategy:", strategy)
    print("Message:", message)
    print("Count:", len(recs))
    if recs:
        print("First rec:", recs[0].get("name", recs[0].get("title", ""))[:60])
    else:
        print("No recommendations returned (by-seed may have failed).")

if __name__ == "__main__":
    main()
