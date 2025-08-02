#!/usr/bin/env python
"""
Main entry point for the Startup Ecosystem Intelligence API Server
"""
import sys
import os
from dotenv import load_dotenv
import uvicorn

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("[START] Starting Startup Ecosystem Intelligence API Server")
    print("=" * 60)
    
    # Check for required environment variables
    required_vars = ['OPENAI_API_KEY', 'NEO4J_URI', 'NEO4J_USER', 'NEO4J_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"[ERROR] Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set them in your .env file")
        sys.exit(1)
    
    # Run the API server
    try:
        print("[API] API Server starting at http://localhost:8000")
        print("[DOCS] API Documentation available at http://localhost:8000/docs")
        print("Press CTRL+C to stop")
        print("=" * 60)
        
        uvicorn.run(
            "backend.api.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n[STOPPED] API Server stopped by user")
    except Exception as e:
        print(f"\n[ERROR] API Server failed with error: {e}")
        raise