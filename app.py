#!/usr/bin/env python
"""
Alternative entry point for Replit - runs just the backend API
Frontend can be run separately if needed
"""
import os
import sys

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the FastAPI app
from backend.api.main import app

# This allows Replit to find the 'app' object
__all__ = ['app']

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)