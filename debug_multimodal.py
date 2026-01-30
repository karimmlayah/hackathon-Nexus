import asyncio
import os
import sys
import base64

# Add paths
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "rag_app"))

from dotenv import load_dotenv
load_dotenv()

from rag_app.services.rag import multimodal_search_and_answer

async def test():
    print("Testing multimodal search...")
    img_b64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
    try:
        result = await multimodal_search_and_answer(image_base64=img_b64, limit=1)
        print("Success!")
        print(f"Results: {len(result['products'])}")
    except Exception as e:
        import traceback
        print(f"Failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
