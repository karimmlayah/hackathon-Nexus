#!/usr/bin/env python
"""
Quick test script for RAG endpoints
"""
import sys
import json
sys.path.insert(0, 'rag_app')

from api.routes import router, SearchRequest, ChatRequest
from services.rag import search_and_answer

async def test_endpoints():
    """Test the endpoints without running the server"""
    print("✅ Testing endpoint imports...")
    print(f"   - SearchRequest fields: {SearchRequest.model_fields.keys()}")
    print(f"   - ChatRequest fields: {ChatRequest.model_fields.keys()}")
    print("\n✅ All imports successful!")
    print(f"\n📍 Router routes:")
    for route in router.routes:
        print(f"   - {route.path} {route.methods}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_endpoints())
