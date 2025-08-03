#!/usr/bin/env python
"""
Create relationships between companies in batches
"""
from backend.utils.neo4j_store import Neo4jStore
import time

def create_relationships_efficiently():
    """Create relationships with better performance"""
    print("[START] Creating relationships between companies")
    print("=" * 60)
    
    store = Neo4jStore()
    
    with store.driver.session() as session:
        # First, get counts
        result = session.run("MATCH (c:Company) RETURN count(c) as count")
        company_count = result.single()['count']
        print(f"Total companies: {company_count}")
        
        # Create SAME_BATCH relationships
        print("\n[1/2] Creating SAME_BATCH relationships...")
        start = time.time()
        result = session.run("""
            MATCH (c1:Company), (c2:Company)
            WHERE c1.batch = c2.batch 
              AND c1.batch <> ''
              AND id(c1) < id(c2)
            MERGE (c1)-[:SAME_BATCH]->(c2)
            RETURN count(*) as created
        """)
        batch_count = result.single()['created']
        print(f"  Created {batch_count} SAME_BATCH relationships in {time.time()-start:.2f}s")
        
        # Create SAME_INDUSTRY relationships in smaller chunks
        print("\n[2/2] Creating SAME_INDUSTRY relationships...")
        
        # Get unique batches to process in chunks
        result = session.run("MATCH (c:Company) WHERE c.batch <> '' RETURN DISTINCT c.batch as batch")
        batches = [r['batch'] for r in result]
        
        total_industry = 0
        for i, batch in enumerate(batches):
            if i % 10 == 0:
                print(f"  Processing batch {i+1}/{len(batches)}...")
            
            start = time.time()
            result = session.run("""
                MATCH (c1:Company), (c2:Company)
                WHERE c1.batch = $batch
                  AND c2.batch = $batch
                  AND id(c1) < id(c2)
                  AND ANY(ind IN c1.industries WHERE ind IN c2.industries)
                MERGE (c1)-[:SAME_INDUSTRY]->(c2)
                RETURN count(*) as created
            """, batch=batch)
            
            count = result.single()['created']
            total_industry += count
        
        print(f"  Created {total_industry} SAME_INDUSTRY relationships")
        
        # Get final stats
        result = session.run("""
            MATCH ()-[r]->()
            RETURN type(r) as type, count(r) as count
        """)
        
        print("\n[SUMMARY] Relationship counts:")
        for record in result:
            print(f"  - {record['type']}: {record['count']}")

if __name__ == "__main__":
    create_relationships_efficiently()