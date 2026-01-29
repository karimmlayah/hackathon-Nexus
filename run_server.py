#!/usr/bin/env python
"""
Standalone test server for RAG endpoints
Run with: python run_server.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from rag_app.main import app
import uvicorn

if __name__ == "__main__":
    # Run with proper Windows compatibility
    uvicorn.run(
        app, 
        host="127.0.0.1", 
        port=8000, 
        log_level="info"
    )
