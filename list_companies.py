#!/usr/bin/env python
"""
List available companies in the database for scoring
"""
from backend.utils.neo4j_store import Neo4jStore

def list_companies(limit=20):
    """List companies with their IDs, names, and batches"""
    store = Neo4jStore()
    
    with store.driver.session() as session:
        result = session.run("""
            MATCH (c:Company) 
            RETURN c.id as id, c.name as name, c.batch as batch, c.industries as industries
            ORDER BY c.batch DESC, c.name
            LIMIT $limit
        """, limit=limit)
        
        print("Available companies in database:")
        print("=" * 80)
        print(f"{'ID':<15} {'Name':<30} {'Batch':<10} {'Industries':<30}")
        print("-" * 80)
        
        for record in result:
            industries = ', '.join(record['industries'][:2]) if record['industries'] else 'N/A'
            if len(record['industries']) > 2:
                industries += '...'
            
            print(f"{record['id']:<15} {record['name']:<30} {record['batch']:<10} {industries:<30}")
        
        print("\nTo score a company, use its ID with the API:")
        print("  curl http://localhost:8000/score/{company_id}")
        print("\nTo score multiple companies:")
        print('  curl -X POST http://localhost:8000/score/batch -H "Content-Type: application/json" -d \'{"company_ids": ["id1", "id2", "id3"]}\'')

if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    list_companies(limit)