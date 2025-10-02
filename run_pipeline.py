#!/usr/bin/env python
"""
Main entry point for the Startup Ecosystem Intelligence Data Pipeline
Not called anywhere in the main workflow. Only used to populate the bakend data stores.
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.neo4j_pipeline import main

if __name__ == "__main__":
    print("🚀 Starting Startup Ecosystem Intelligence Data Pipeline")
    print("=" * 60)
    
    # Check for required environment variables
    required_vars = ['OPENAI_API_KEY', 'NEO4J_URI', 'NEO4J_USER', 'NEO4J_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set them in your .env file")
        sys.exit(1)
    
    # Run the pipeline
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Pipeline interrupted by user")
    except Exception as e:
        print(f"\n❌ Pipeline failed with error: {e}")
        raise
