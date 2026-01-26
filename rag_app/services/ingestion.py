import pandas as pd
from pypdf import PdfReader
from fastapi import UploadFile
from typing import List, Dict
import io

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Simple text chunking with overlap."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)
    return chunks

async def process_file(file: UploadFile) -> List[Dict]:
    """
    Reads a file and returns a list of chunks with metadata.
    Returns: List[{"text": str, "source": str, "page": int (optional)}]
    """
    documents = []
    content = await file.read()
    filename = file.filename
    
    if filename.endswith(".pdf"):
        pdf = PdfReader(io.BytesIO(content))
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                chunks = chunk_text(text)
                for chunk in chunks:
                    documents.append({
                        "text": chunk,
                        "source": filename,
                        "page": i + 1,
                        "type": "pdf"
                    })
                    
    elif filename.endswith(".txt"):
        text = content.decode("utf-8")
        chunks = chunk_text(text)
        for chunk in chunks:
            documents.append({
                "text": chunk,
                "source": filename,
                "type": "txt"
            })
            
    elif filename.endswith(".csv"):
        # For CSV, we treat each row as a document if it's small, or concat columns
        df = pd.read_csv(io.BytesIO(content))
        # Convert each row to a rich text representation
        for i, row in df.iterrows():
            desc = row.get('description', 'N/A')
            desc_str = str(desc) if desc is not None and not pd.isna(desc) else "N/A"

            # Create a more searchable block of text
            row_text = f"PRODUCT ASIN: {row.get('asin', 'N/A')} | "
            row_text += f"TITLE: {row.get('title', 'N/A')} | "
            row_text += f"PRICE: {row.get('final_price', 'N/A')} | "
            row_text += f"BRAND: {row.get('brand', 'N/A')} | "
            row_text += f"CATEGORIES: {row.get('categories', 'N/A')} | "
            row_text += f"DESCRIPTION: {desc_str[:500]}..."
            
            documents.append({
                "text": row_text,
                "source": filename,
                "asin": str(row.get('asin', '')),
                "row": i,
                "type": "csv"
            })
            
    return documents

async def process_local_file(file_path: str) -> List[Dict]:
    """
    Reads a local file and returns a list of chunks with metadata.
    Designed for fixed dataset ingestion.
    """
    documents = []
    
    try:
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
            for i, row in df.iterrows():
                desc = row.get('description', 'N/A')
                desc_str = str(desc) if desc is not None and not pd.isna(desc) else "N/A"
                
                row_text = f"PRODUCT ASIN: {row.get('asin', 'N/A')} | "
                row_text += f"TITLE: {row.get('title', 'N/A')} | "
                row_text += f"PRICE: {row.get('final_price', 'N/A')} | "
                row_text += f"BRAND: {row.get('brand', 'N/A')} | "
                row_text += f"CATEGORIES: {row.get('categories', 'N/A')} | "
                row_text += f"DESCRIPTION: {desc_str[:500]}..."
                
                documents.append({
                    "text": row_text,
                    "source": file_path,
                    "asin": str(row.get('asin', '')),
                    "row": i,
                    "type": "csv"
                })
        else:
            print(f"Unsupported file type for fixed dataset: {file_path}")
            
    except Exception as e:
        print(f"Error reading fixed dataset {file_path}: {e}")
        
    return documents
