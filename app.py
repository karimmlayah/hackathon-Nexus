"""
Main entry point for the FinFit RAG application
Run with: uvicorn app:app --reload
"""
from rag_app.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)

