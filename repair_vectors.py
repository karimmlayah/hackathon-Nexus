"""Repair script to fix zeroed image vectors"""
import os
import requests
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from qdrant import get_qdrant_client
from image_embedder import ImageEmbedder

load_dotenv()

from concurrent.futures import ThreadPoolExecutor
from typing import Tuple

def download_image(args: Tuple[str, str]) -> Tuple[str, bytes]:
    point_id, url = args
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return point_id, response.content
    except Exception as e:
        print(f"[!] Download Error {point_id}: {e}")
    return point_id, None

def repair_all():
    client = get_qdrant_client()
    collection_name = "nexus-multivector_3k_f"
    embedder = ImageEmbedder()
    
    print(f"[*] Starting FAST FULL repair of '{collection_name}'")
    
    next_page = None
    total_fixed = 0
    BATCH_SIZE = 50 # Process in batches of 50
    
    while True:
        results, next_page = client.scroll(
            collection_name=collection_name,
            limit=BATCH_SIZE,
            with_payload=True,
            offset=next_page
        )
        
        if not results:
            break
            
        # Collect download tasks
        to_download = []
        for point in results:
            if not point.payload.get("_fixed_image") and point.payload.get("image_url"):
                to_download.append((point.id, point.payload.get("image_url")))
        
        if not to_download:
            if next_page is None: break
            continue
            
        print(f"[*] Batch: downloading {len(to_download)} images...")
        
        # Multi-threaded download
        downloaded_images = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            downloaded_images = list(executor.map(download_image, to_download))
            
        # Filter successful downloads
        valid_items = [(pid, content) for pid, content in downloaded_images if content]
        
        if valid_items:
            print(f"[*] Batch: Encoding {len(valid_items)} images...")
            # Prepare images for batch encoding
            pil_images = []
            for _, content in valid_items:
                img = Image.open(BytesIO(content))
                if img.mode != "RGB":
                    img = img.convert("RGB")
                pil_images.append(img)
                
            # Batch encode
            vectors = embedder.model.encode(
                pil_images, 
                batch_size=len(pil_images),
                normalize_embeddings=True
            ).tolist()
            
            # Update points in Qdrant INDIVIDUALLY to be resilient to missing points
            for (pid, _), vec in zip(valid_items, vectors):
                try:
                    client.update_vectors(
                        collection_name=collection_name,
                        points=[{"id": pid, "vector": {"image_dense": vec}}]
                    )
                    client.set_payload(
                        collection_name=collection_name,
                        payload={"_fixed_image": True},
                        points=[pid]
                    )
                    total_fixed += 1
                except Exception as e:
                    print(f"[!] Warning: Could not update point {pid}: {e}")
            
            print(f"[*] Progress: {total_fixed} products repaired so far...")
        
        if next_page is None:
            break

    print(f"[*] Repair complete. Total products fixed: {total_fixed}")

if __name__ == "__main__":
    repair_all()
