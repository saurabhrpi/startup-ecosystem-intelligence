#!/usr/bin/env python
"""
Resume loading companies from where we left off
"""
import asyncio
import json
import os
from backend.neo4j_pipeline import Neo4jDataPipeline
from backend.utils.neo4j_store import Neo4jStore

async def resume_pipeline():
    """Resume loading companies starting from company 2138"""
    print("[RESUME] Resuming Neo4j Data Pipeline")
    print("=" * 60)
    
    # Check current state
    store = Neo4jStore()
    stats = store.get_statistics()
    already_loaded = stats.get('company_count', 0)
    print(f"Companies already loaded: {already_loaded}")
    
    # Load all companies
    with open('data/raw/yc_companies.json', 'r', encoding='utf-8') as f:
        all_companies = json.load(f)
    
    print(f"Total companies in dataset: {len(all_companies)}")
    print(f"Companies remaining: {len(all_companies) - already_loaded}")
    
    # Get remaining companies (assuming they were loaded in order)
    remaining_companies = all_companies[already_loaded:]
    
    if not remaining_companies:
        print("All companies already loaded!")
        return
    
    # Create pipeline and load remaining
    pipeline = Neo4jDataPipeline()
    
    # Load only the remaining companies
    print(f"\n[LOADING] Loading {len(remaining_companies)} remaining companies...")
    await pipeline._load_companies(remaining_companies)
    
    # Create relationships for all companies
    print("\n[RELATIONSHIPS] Creating cross-entity relationships...")
    pipeline.create_relationships()
    
    # Generate report
    pipeline.generate_summary_report()
    
    print("\n[COMPLETE] All companies loaded successfully!")

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(resume_pipeline())