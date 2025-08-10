"""
Neo4j Data Pipeline - Loads data with embeddings directly into Neo4j
"""
import asyncio
import json
import os
from typing import List, Dict, Any
from datetime import datetime
from tqdm import tqdm
import hashlib
import time

from backend.collectors.yc_scraper import YCCompaniesScraper
from backend.collectors.github_collector import GitHubCollector
from backend.utils.embeddings import EmbeddingGenerator
from backend.utils.neo4j_store import Neo4jStore

class Neo4jDataPipeline:
    def __init__(self):
        self.collectors = {
            'yc': YCCompaniesScraper(),
            'github': GitHubCollector()
        }
        self.embedding_generator = EmbeddingGenerator()
        self.neo4j_store = Neo4jStore()
        # Track processed people to avoid redundant embedding generation
        self.processed_person_ids = set()
        
    async def run_full_pipeline(self):
        """Run the complete data pipeline"""
        print("Starting Neo4j Graph RAG Pipeline...")
        print("=" * 60)
        start_time = datetime.now()
        
        # Step 1: Collect data from all sources
        all_data = await self.collect_all_data()
        
        # Step 2: Load data with embeddings into Neo4j
        await self.load_data_to_neo4j(all_data)
        
        # Step 3: Create relationships
        self.create_relationships()
        
        # Step 4: Generate summary report
        self.generate_summary_report()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"\nPipeline completed in {duration:.2f} seconds")
        
    async def collect_all_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Collect data from all sources"""
        print("\n[DATA] Collecting data from all sources...")
        
        all_data = {}
        
        # Collect YC companies
        try:
            yc_companies = await self.collectors['yc'].fetch_all_companies()
            if yc_companies:
                all_data['companies'] = yc_companies
                print(f"[SUCCESS] Collected {len(yc_companies)} YC companies")
            else:
                # Load from existing raw data
                yc_path = 'data/raw/yc_companies.json'
                if os.path.exists(yc_path):
                    with open(yc_path, 'r', encoding='utf-8') as f:
                        all_data['companies'] = json.load(f)
                        print(f"[LOADED] Loaded {len(all_data['companies'])} YC companies from file")
                else:
                    all_data['companies'] = []
        except Exception as e:
            print(f"[ERROR] Error collecting YC data: {e}")
            all_data['companies'] = []
        
        # Collect GitHub repos
        try:
            if hasattr(self.collectors['github'], 'token') and self.collectors['github'].token:
                repos = await self.collectors['github'].fetch_startup_repos()
                all_data['repos'] = repos
                print(f"[SUCCESS] Collected {len(repos)} GitHub repos")
            else:
                # Load sample data
                sample_path = 'data/samples/github_repos.json'
                if os.path.exists(sample_path):
                    with open(sample_path, 'r', encoding='utf-8') as f:
                        all_data['repos'] = json.load(f)
                        print(f"[LOADED] Loaded {len(all_data['repos'])} GitHub repos from samples")
                else:
                    all_data['repos'] = []
        except Exception as e:
            print(f"[ERROR] Error collecting GitHub data: {e}")
            all_data['repos'] = []
        
        return all_data
    
    async def load_data_to_neo4j(self, all_data: Dict[str, List[Dict[str, Any]]]):
        """Load data with embeddings into Neo4j"""
        print("\n[LOADING] Loading data into Neo4j with embeddings...")
        
        # Load companies
        if all_data.get('companies'):
            await self._load_companies(all_data['companies'])  # Load all companies
        
        # Load repos
        if all_data.get('repos'):
            await self._load_repositories(all_data['repos'])
    
    async def _load_companies(self, companies: List[Dict[str, Any]], skip_existing: bool = True):
        """Load companies with embeddings"""
        print(f"\n[PROCESSING] Processing {len(companies)} companies...")
        
        # Get existing company IDs if skip_existing is True
        existing_ids = set()
        if skip_existing:
            with self.neo4j_store.driver.session() as session:
                result = session.run("""
                    MATCH (c:Company)
                    WHERE c.source = 'yc'
                    RETURN c.id as id
                """)
                existing_ids = {record['id'] for record in result}
                print(f"[INFO] Found {len(existing_ids)} existing YC companies in database")
        
        # Filter out existing companies
        new_companies = []
        skipped_count = 0
        for company in companies:
            company_id = self._generate_id(company, 'company')
            if company_id not in existing_ids:
                new_companies.append(company)
            else:
                skipped_count += 1
        
        if skipped_count > 0:
            print(f"[INFO] Skipping {skipped_count} companies that already exist")
        
        if not new_companies:
            print("[INFO] All companies are already loaded!")
            return
        
        print(f"[INFO] Loading {len(new_companies)} new companies...")
        
        # Process in batches to avoid rate limits
        batch_size = 50
        total_batches = (len(new_companies) + batch_size - 1) // batch_size
        
        for batch_idx in range(total_batches):
            batch_start = batch_idx * batch_size
            batch_end = min((batch_idx + 1) * batch_size, len(new_companies))
            batch = new_companies[batch_start:batch_end]
            
            print(f"\n[BATCH {batch_idx + 1}/{total_batches}] Processing companies {batch_start + 1}-{batch_end}")
            
            for company in tqdm(batch, desc=f"Batch {batch_idx + 1}"):
                try:
                    # Generate embedding
                    embedding_text = self._create_company_text(company)
                    embedding = self._get_embedding(embedding_text)
                    
                    if embedding:
                        # Create company node with embedding
                        company_id = self._generate_id(company, 'company')
                        company_data = {
                            'id': company_id,
                            'name': company.get('name'),
                            'description': company.get('description', ''),
                            'location': company.get('location', ''),
                            'website': company.get('website', ''),
                            'batch': company.get('batch', ''),
                            'industries': company.get('industries', []),
                            'source': 'yc'
                        }
                        
                        self.neo4j_store.create_company_with_embedding(company_data, embedding)
                        
                        # Create founder nodes and relationships
                        if 'founders' in company and isinstance(company['founders'], list):
                            for founder in company['founders']:
                                if isinstance(founder, dict) and founder.get('name'):
                                    person_id = self._generate_id(founder, 'person')
                                    person_data = {
                                        'id': person_id,
                                        'name': founder.get('name'),
                                        'role': 'Founder',
                                        'company': company.get('name'),
                                        'source': 'yc'
                                    }
                                    
                                    # Generate embedding for person (founder)
                                    if person_id not in self.processed_person_ids:
                                        person_text = f"Name: {founder.get('name')}\nRole: Founder\nCompany: {company.get('name')}"
                                        person_embedding = self._get_embedding(person_text)
                                        self.processed_person_ids.add(person_id)
                                    else:
                                        person_embedding = None
                                    
                                    self.neo4j_store.create_person_with_embedding(person_data, person_embedding)
                                    
                                    # Create FOUNDED relationship
                                    self.neo4j_store.create_relationship(
                                        from_id=person_id,
                                        to_id=company_id,
                                        rel_type='FOUNDED',
                                        properties={'role': 'Founder'}
                                    )
                    
                except Exception as e:
                    print(f"\n[ERROR] Error processing company {company.get('name', 'Unknown')}: {e}")
            
            # Add delay between batches to avoid rate limits
            if batch_idx < total_batches - 1:
                print(f"[DELAY] Waiting 2 seconds before next batch...")
                time.sleep(2)
    
    async def _load_repositories(self, repos: List[Dict[str, Any]]):
        """Load repositories with embeddings"""
        print(f"\n[PROCESSING] Processing {len(repos)} repositories...")
        
        for repo in tqdm(repos, desc="Loading repositories"):
            try:
                # Generate embedding for repository
                embedding_text = self._create_repo_text(repo)
                embedding = self._get_embedding(embedding_text)
                
                if embedding:
                    # Create repo node with embedding
                    repo_id = self._generate_id(repo, 'repo')
                    repo_data = {
                        'id': repo_id,
                        'name': repo.get('name'),
                        'description': repo.get('description', ''),
                        'language': repo.get('language', ''),
                        'stars': repo.get('stars', 0),
                        'url': repo.get('url', ''),
                        'owner': repo.get('owner', {}),
                        'topics': repo.get('topics', []),
                        'source': 'github'
                    }
                    
                    self.neo4j_store.create_repository_with_embedding(repo_data, embedding)
                    
                    # Create owner node if exists (with embedding when first seen)
                    if repo.get('owner', {}).get('login'):
                        owner_login = repo['owner']['login']
                        owner_id = self._generate_id({'name': owner_login, 'source': 'github'}, 'person')
                        owner_data = {
                            'id': owner_id,
                            'name': owner_login,
                            'role': 'Developer',
                            'source': 'github'
                        }
                        
                        if owner_id not in self.processed_person_ids:
                            owner_text = (
                                f"Name: {owner_login}\n"
                                f"Role: Developer\n"
                                f"Repository: {repo.get('name', '')}\n"
                                f"Description: {repo.get('description', '')}"
                            )
                            owner_embedding = self._get_embedding(owner_text)
                            self.processed_person_ids.add(owner_id)
                        else:
                            owner_embedding = None
                        
                        self.neo4j_store.create_person_with_embedding(owner_data, owner_embedding)
                        
                        # Create OWNS relationship
                        self.neo4j_store.create_relationship(
                            from_id=owner_id,
                            to_id=repo_id,
                            rel_type='OWNS',
                            properties={'source': 'github'}
                        )
                        
            except Exception as e:
                print(f"\n[ERROR] Error processing repo {repo.get('name', 'Unknown')}: {e}")
    
    def create_relationships(self):
        """Create additional relationships between entities"""
        print("\n[RELATIONSHIPS] Creating cross-entity relationships...")
        
        with self.neo4j_store.driver.session() as session:
            # Remove dense pairwise edges if they exist
            print("  - Removing SAME_BATCH/SAME_INDUSTRY pairwise edges (if any)...")
            session.run("MATCH ()-[r:SAME_BATCH]->() DELETE r")
            session.run("MATCH ()-[r:SAME_INDUSTRY]->() DELETE r")

            # Ensure uniqueness constraints for hub nodes
            print("  - Ensuring constraints for hub nodes...")
            session.run("CREATE CONSTRAINT batch_name IF NOT EXISTS FOR (b:Batch) REQUIRE b.name IS UNIQUE")
            session.run("CREATE CONSTRAINT industry_name IF NOT EXISTS FOR (i:Industry) REQUIRE i.name IS UNIQUE")

            # Batch hubs (Company)-[:IN_BATCH]->(Batch)
            print("  - Creating IN_BATCH hub relationships...")
            session.run(
                """
                MATCH (c:Company) WHERE c.batch IS NOT NULL AND c.batch <> ''
                MERGE (b:Batch {name: c.batch})
                MERGE (c)-[:IN_BATCH]->(b)
                """
            )

            # Industry hubs (Company)-[:IN_INDUSTRY]->(Industry)
            print("  - Creating IN_INDUSTRY hub relationships...")
            session.run(
                """
                MATCH (c:Company)
                WITH c, coalesce(c.industries, []) AS inds
                UNWIND inds AS ind
                WITH c, toLower(trim(ind)) AS ind
                WHERE ind <> ''
                MERGE (i:Industry {name: ind})
                MERGE (c)-[:IN_INDUSTRY]->(i)
                """
            )
            
            # Keep repo links
            print("  - Linking repos to potential company owners...")
            session.run(
                """
                MATCH (c:Company), (r:Repository)
                WHERE toLower(r.name) CONTAINS toLower(c.name) 
                   OR toLower(r.description) CONTAINS toLower(c.name)
                MERGE (c)-[:LIKELY_OWNS]->(r)
                """
            )

            # Create sparse SIMILAR_TO edges using vector indexes (top-3 per node)
            top_k = 3
            threshold = 0.85

            print("  - Rebuilding SIMILAR_TO edges (Company)...")
            session.run("MATCH ()-[r:SIMILAR_TO]->() DELETE r")
            session.run(
                """
                MATCH (c:Company) WHERE c.embedding IS NOT NULL
                CALL db.index.vector.queryNodes('company_embedding', $topKPlusSelf, c.embedding)
                YIELD node, score
                WHERE node <> c AND score >= $threshold
                WITH c, node, score
                ORDER BY score DESC
                WITH c, collect({node: node, score: score})[0..$topK] AS top
                UNWIND top AS t
                WITH c, t.node AS other, t.score AS s
                MERGE (c)-[r:SIMILAR_TO]-(other)
                SET r.score = s
                """,
                {
                    "topKPlusSelf": top_k + 1,
                    "topK": top_k,
                    "threshold": threshold,
                }
            )

            print("  - Rebuilding SIMILAR_TO edges (Person)...")
            session.run(
                """
                MATCH (p:Person) WHERE p.embedding IS NOT NULL
                CALL db.index.vector.queryNodes('person_embedding', $topKPlusSelf, p.embedding)
                YIELD node, score
                WHERE node <> p AND score >= $threshold
                WITH p, node, score
                ORDER BY score DESC
                WITH p, collect({node: node, score: score})[0..$topK] AS top
                UNWIND top AS t
                WITH p, t.node AS other, t.score AS s
                MERGE (p)-[r:SIMILAR_TO]-(other)
                SET r.score = s
                """,
                {
                    "topKPlusSelf": top_k + 1,
                    "topK": top_k,
                    "threshold": threshold,
                }
            )

            print("  - Rebuilding SIMILAR_TO edges (Repository)...")
            session.run(
                """
                MATCH (r:Repository) WHERE r.embedding IS NOT NULL
                CALL db.index.vector.queryNodes('repo_embedding', $topKPlusSelf, r.embedding)
                YIELD node, score
                WHERE node <> r AND score >= $threshold
                WITH r, node, score
                ORDER BY score DESC
                WITH r, collect({node: node, score: score})[0..$topK] AS top
                UNWIND top AS t
                WITH r, t.node AS other, t.score AS s
                MERGE (r)-[rel:SIMILAR_TO]-(other)
                SET rel.score = s
                """,
                {
                    "topKPlusSelf": top_k + 1,
                    "topK": top_k,
                    "threshold": threshold,
                }
            )
    
    def generate_summary_report(self):
        """Generate summary report of the pipeline run"""
        stats = self.neo4j_store.get_statistics()
        
        print("\n[SUMMARY] Pipeline Summary Report")
        print("=" * 60)
        print(f"Total nodes: {stats['total_nodes']}")
        print(f"Total relationships: {stats['total_relationships']}")
        print("\nNodes by type:")
        for node_type in ['company', 'person', 'repository']:
            count = stats.get(f'{node_type}_count', 0)
            with_embeddings = stats.get(f'{node_type}_with_embeddings', 0)
            print(f"  - {node_type.capitalize()}: {count} (with embeddings: {with_embeddings})")
        
        print("\nRelationships by type:")
        for rel_type, count in stats.get('relationships', {}).items():
            print(f"  - {rel_type}: {count}")
        
        # Save report
        report = {
            'timestamp': datetime.now().isoformat(),
            'statistics': stats
        }
        
        os.makedirs('data', exist_ok=True)
        with open(f'data/neo4j_pipeline_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
            json.dump(report, f, indent=2)
    
    def _create_company_text(self, company: Dict) -> str:
        """Create text representation of a company"""
        parts = [
            f"Company: {company.get('name', '')}",
            f"Description: {company.get('description', '')}",
            f"Industries: {', '.join(company.get('industries', []))}",
            f"Location: {company.get('location', '')}",
            f"Batch: {company.get('batch', '')}",
        ]
        return '\n'.join(filter(None, parts))
    
    def _create_repo_text(self, repo: Dict) -> str:
        """Create text representation of a repo"""
        parts = [
            f"Repository: {repo.get('name', '')}",
            f"Description: {repo.get('description', '')}",
            f"Language: {repo.get('language', '')}",
            f"Topics: {', '.join(repo.get('topics', []))}",
            f"Stars: {repo.get('stars', 0)}",
        ]
        return '\n'.join(filter(None, parts))
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding from OpenAI"""
        try:
            import openai
            openai.api_key = os.getenv('OPENAI_API_KEY')
            
            response = openai.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"\n[ERROR] Error generating embedding: {e}")
            return None
    
    def _generate_id(self, item: Dict, data_type: str) -> str:
        """Generate unique ID for an item"""
        if 'id' in item:
            return str(item['id'])
        
        content = f"{data_type}_{item.get('name', '')}_{item.get('source', '')}"
        return hashlib.md5(content.encode()).hexdigest()

# Main execution
async def main(load_remaining_only: bool = False):
    """Run the Neo4j data pipeline"""
    pipeline = Neo4jDataPipeline()
    
    if load_remaining_only:
        print("Loading only remaining YC companies (skipping existing)...")
        # Load YC companies from file
        yc_path = 'data/raw/yc_companies.json'
        if os.path.exists(yc_path):
            with open(yc_path, 'r', encoding='utf-8') as f:
                companies = json.load(f)
                await pipeline._load_companies(companies, skip_existing=True)
            
            # Show statistics
            pipeline.generate_summary_report()
        else:
            print(f"[ERROR] YC companies file not found: {yc_path}")
    else:
        await pipeline.run_full_pipeline()

if __name__ == "__main__":
    import sys
    load_remaining = '--load-remaining' in sys.argv
    asyncio.run(main(load_remaining_only=load_remaining))