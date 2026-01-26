"""Quick script to check the structure of the images-only-clip collection"""
import os
from dotenv import load_dotenv
from qdrant import get_qdrant_client

load_dotenv()

client = get_qdrant_client()

# Check the collection structure
collection_name = "images-only-clip"
try:
    collection_info = client.get_collection(collection_name)
    print(f"\n✅ Collection '{collection_name}' found!")
    print(f"Points count: {collection_info.points_count}")
    print(f"\nVectors config:")
    print(collection_info.config.params.vectors)
    
    # Check if it's a dict (named vectors) or single vector
    vectors_config = collection_info.config.params.vectors
    if isinstance(vectors_config, dict):
        print(f"\n📋 Named vectors found:")
        for name, config in vectors_config.items():
            print(f"  - {name}: size={config.size}, distance={config.distance}")
    else:
        print(f"\n📋 Single vector (unnamed): size={vectors_config.size}, distance={vectors_config.distance}")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
