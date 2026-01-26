import asyncio
import json
import os
import sys

# Add the project root to sys.path so we can import internal modules
sys.path.append(os.getcwd())

from services.rag import search_and_answer
from core.config import settings

async def verify_rag():
    print("--- 🚀 RAG PRODUCTION VERIFICATION ---")
    print(f"Collection: {settings.COLLECTION_NAME}")
    
    query = "best laptop under 500 dollars"
    print(f"Query: '{query}'")
    
    try:
        # Execute the refactored logic in production mode
        result = await search_and_answer(query, production_mode=True)
        
        # Verify JSON structure
        print("\n✅ API RESPONSE PREVIEW:")
        print(json.dumps(result, indent=2))
        
        # Validation checks
        has_answer = "answer" in result and len(result["answer"]) > 0
        has_products = "products" in result and isinstance(result["products"], list)
        
        if has_answer and has_products:
            print("\n✅ STRUCTURE VALIDATION: SUCCESS")
            print(f"✅ Found {len(result['products'])} products.")
        else:
            print("\n❌ STRUCTURE VALIDATION: FAILED")
            
    except Exception as e:
        print(f"\n❌ EXECUTION ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Ensure we are in rag_app directory
    if not os.path.exists("main.py"):
        print("Please run this script from the 'rag_app' directory.")
        sys.exit(1)
        
    asyncio.run(verify_rag())
