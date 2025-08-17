"""
Neo4j Data Pipeline - Loads data with embeddings directly into Neo4j
"""
import asyncio
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from tqdm import tqdm
import hashlib
import time

from backend.collectors.yc_scraper import YCCompaniesScraper
from backend.collectors.github_collector import GitHubCollector
from backend.collectors.website_scraper import WebsiteScraper
from backend.utils.embeddings import EmbeddingGenerator
from backend.utils.neo4j_store import Neo4jStore
from backend.utils.name_guard import is_probable_person_name
from urllib.parse import urlparse
import re
from backend.collectors.google_cse import GoogleCSEClient
from backend.config import settings

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
        self.cse_client = None
        try:
            if settings.use_cse_for_founders and settings.google_cse_api_key and settings.google_cse_cx:
                self.cse_client = GoogleCSEClient()
                print("[FOUNDERS] Google Custom Search enabled for founder discovery")
        except Exception:
            self.cse_client = None
        
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
        
        # Collect GitHub repos using company-first approach
        if not (hasattr(self.collectors['github'], 'token') and self.collectors['github'].token):
            print("[WARN] GITHUB_TOKEN not set. Skipping GitHub repository collection.")
            all_data['repos'] = []
            self.repo_company_mappings = []
        elif not all_data.get('companies'):
            print("[WARN] No companies loaded. Skipping GitHub repository discovery.")
            all_data['repos'] = []
            self.repo_company_mappings = []
        else:
            print("[GitHub] Starting company-first repository discovery...")
            import os as _os
            # Limit per-company repo discovery to a reasonable default
            MAX_COMPANY_REPO_QUERIES = int(_os.getenv('MAX_COMPANY_REPO_QUERIES', '100'))
            selection = _os.getenv('COMPANY_SELECTION_STRATEGY', 'zero_repos').lower()

            # Build candidate pool based on DB state
            companies_pool = all_data.get('companies', [])
            if selection in ('zero_repos', 'zero_founders'):
                try:
                    with self.neo4j_store.driver.session() as session:
                        if selection == 'zero_repos':
                            query = """
                            MATCH (c:Company)
                            OPTIONAL MATCH (c)-[:OWNS|:LIKELY_OWNS]->(:Repository)
                            WITH c, count(*) AS rels
                            WHERE rels = 0
                            RETURN c.id AS id
                            """
                        else:
                            query = """
                            MATCH (c:Company)
                            OPTIONAL MATCH (c)<-[:FOUNDED]-(:Person)
                            WITH c, count(*) AS founders
                            WHERE founders = 0
                            RETURN c.id AS id
                            """
                        rows = session.run(query)
                        empty_ids = {row['id'] for row in rows}
                    companies_pool = [c for c in companies_pool if self._generate_id(c, 'company') in empty_ids]
                    print(f"[SELECT] Strategy='{selection}': {len(companies_pool)} companies selected from DB state")
                except Exception as e:
                    print(f"[WARN] Selection strategy '{selection}' failed: {e}. Falling back to full list")

            # Apply limit
            companies_to_process = companies_pool[:MAX_COMPANY_REPO_QUERIES]
            print(f"[INFO] Processing {len(companies_to_process)} companies (limit {MAX_COMPANY_REPO_QUERIES}; set MAX_COMPANY_REPO_QUERIES to change)")
            
            try:
                repos = await self.collectors['github'].fetch_all_company_repos(
                    companies_to_process,
                    max_companies=len(companies_to_process)
                )
                
                if not repos:
                    print("[WARN] No GitHub repositories discovered. This might be due to rate limits or no matching repos.")
                    all_data['repos'] = []
                else:
                    all_data['repos'] = repos
                    print(f"[SUCCESS] Discovered {len(repos)} GitHub repos from {len(companies_to_process)} companies")
                
                # Store the repo-company mappings for later relationship creation
                self.repo_company_mappings = getattr(self.collectors['github'], 'repo_company_mappings', [])
            except Exception as e:
                print(f"[ERROR] Failed to fetch GitHub repos: {e}")
                all_data['repos'] = []
                self.repo_company_mappings = []

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
        
        # Split into new vs existing companies
        new_companies: List[Dict[str, Any]] = []
        existing_companies: List[Dict[str, Any]] = []
        skipped_count = 0
        for company in companies:
            company_id = self._generate_id(company, 'company')
            if company_id not in existing_ids:
                new_companies.append(company)
            else:
                existing_companies.append(company)
                skipped_count += 1
        
        if skipped_count > 0:
            print(f"[INFO] Skipping {skipped_count} companies that already exist")
        
        if not new_companies:
            print("[INFO] All companies are already loaded! Running founders backfill for existing companies...")
            await self._backfill_founders_for_existing(existing_companies)
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
                            # location_code will be set by DB backfill or alias pass; accept inbound if present
                            'location_code': company.get('location_code', ''),
                            'website': company.get('website', ''),
                            'batch': company.get('batch', ''),
                            # batch_code compact form if present
                            'batch_code': company.get('batch_code', ''),
                            'industries': company.get('industries', []),
                            'source': 'yc'
                        }
                        # Compute normalized website domain for matching
                        company_data['website_domain'] = self._extract_domain(company_data.get('website', ''))
                        
                        self.neo4j_store.create_company_with_embedding(company_data, embedding)
                        
                        # Derive founders/investors if missing: from text, CSE, then website scrape
                        founders = []
                        investors: List[str] = []
                        if isinstance(company.get('founders'), list) and company['founders']:
                            founders = [f['name'] if isinstance(f, dict) else f for f in company['founders'] if f]
                        if not founders:
                            text = f"{company.get('long_description','')}\n{company.get('description','')}"
                            founders = self._extract_founders_from_text(text)
                        if self.cse_client:
                            try:
                                # fetch both founders and investors in one pass where possible
                                both = await self.cse_client.search_founders_and_investors(
                                    company.get('name') or '',
                                    company_data.get('website_domain') if 'company_data' in locals() else self._extract_domain(company.get('website') or '')
                                )
                                founders = both.get('founders') or founders
                                investors = both.get('investors') or investors
                            except Exception:
                                pass
                        if not founders and company.get('website') and os.getenv('USE_WEBSITE_SCRAPER', 'false').lower() == 'true':
                            try:
                                scraper = WebsiteScraper()
                                founders = await scraper.scrape_founders(company.get('website'))
                            except Exception:
                                founders = []

                        # Create founder nodes and relationships (guard against non-person entries)
                        for founder_name in founders:
                            if not founder_name:
                                continue
                            if not is_probable_person_name(founder_name):
                                continue
                            founder_obj = {'name': founder_name, 'source': 'yc'}
                            person_id = self._generate_id(founder_obj, 'person')
                            person_data = {
                                'id': person_id,
                                'name': founder_name,
                                'role': 'founder',
                                'roles': ['founder'],
                                'company': company.get('name'),
                                'source': 'yc',
                                'location': company_data.get('location', ''),
                                'location_code': company_data.get('location_code', ''),
                                'batch': company_data.get('batch', ''),
                                'batch_code': company_data.get('batch_code', '')
                            }
                            # Generate embedding for person (founder)
                            if person_id not in self.processed_person_ids:
                                person_text = f"Name: {founder_name}\nRole: Founder\nCompany: {company.get('name')}"
                                person_embedding = self._get_embedding(person_text)
                                self.processed_person_ids.add(person_id)
                            else:
                                person_embedding = None
                            self.neo4j_store.create_person_with_embedding(person_data, person_embedding)
                            self.neo4j_store.create_relationship(
                                from_id=person_id,
                                to_id=company_id,
                                rel_type='FOUNDED',
                                properties={'role': 'Founder'}
                            )

                        # Create investor person nodes and WORKS_AT relationships (non-destructive)
                        for investor_name in investors:
                            if not investor_name:
                                continue
                            if not is_probable_person_name(investor_name):
                                continue
                            inv_obj = {'name': investor_name, 'source': 'google_cse'}
                            inv_id = self._generate_id(inv_obj, 'person')
                            inv_data = {
                                'id': inv_id,
                                'name': investor_name,
                                'role': 'investor',
                                'roles': ['investor'],
                                'company': company.get('name'),
                                'source': 'google_cse',
                                'location': company_data.get('location', ''),
                                'location_code': company_data.get('location_code', ''),
                                'batch': company_data.get('batch', ''),
                                'batch_code': company_data.get('batch_code', '')
                            }
                            if inv_id not in self.processed_person_ids:
                                inv_text = f"Name: {investor_name}\nRole: Investor\nCompany: {company.get('name')}"
                                inv_embedding = self._get_embedding(inv_text)
                                self.processed_person_ids.add(inv_id)
                            else:
                                inv_embedding = None
                            self.neo4j_store.create_person_with_embedding(inv_data, inv_embedding)
                            self.neo4j_store.create_relationship(
                                from_id=inv_id,
                                to_id=company_id,
                                rel_type='INVESTS_IN',
                                properties={'role': 'Investor'}
                            )
                    
                except Exception as e:
                    print(f"\n[ERROR] Error processing company {company.get('name', 'Unknown')}: {e}")
            
            # Add delay between batches to avoid rate limits
            if batch_idx < total_batches - 1:
                print(f"[DELAY] Waiting 2 seconds before next batch...")
                time.sleep(2)

        # Also backfill founders for existing companies in this run
        if existing_companies:
            print("\n[BACKFILL] Processing founders for existing companies...")
            await self._backfill_founders_for_existing(existing_companies)

    async def _backfill_founders_for_existing(self, companies: List[Dict[str, Any]]):
        """Create founder Person nodes and FOUNDED relationships for companies that already exist in DB.
        The number of companies processed can be limited via env MAX_FOUNDER_BACKFILL (default: 100).
        """
        import os as _os
        limit = int(_os.getenv('MAX_FOUNDER_BACKFILL', '100'))
        subset = companies[:limit] if limit > 0 else companies
        print(f"[BACKFILL] Founders backfill will process up to {len(subset)} companies (MAX_FOUNDER_BACKFILL={limit}).")
        for company in tqdm(subset, desc="Backfilling founders"):
            try:
                company_id = self._generate_id(company, 'company')
                # Derive founders using same logic as new companies
                founders: List[str] = []
                if isinstance(company.get('founders'), list) and company['founders']:
                    founders = [f['name'] if isinstance(f, dict) else f for f in company['founders'] if f]
                if not founders:
                    text = f"{company.get('long_description','')}\n{company.get('description','')}"
                    founders = self._extract_founders_from_text(text)
                if not founders and self.cse_client:
                    try:
                        founders = await self.cse_client.search_founders(
                            company.get('name') or '',
                            self._extract_domain(company.get('website') or '')
                        )
                    except Exception:
                        founders = []
                if not founders and company.get('website') and os.getenv('USE_WEBSITE_SCRAPER', 'false').lower() == 'true':
                    try:
                        scraper = WebsiteScraper()
                        founders = await scraper.scrape_founders(company.get('website'))
                    except Exception:
                        founders = []

                for founder_name in founders:
                    if not founder_name:
                        continue
                    if not is_probable_person_name(founder_name):
                        continue
                    founder_obj = {'name': founder_name, 'source': 'yc'}
                    person_id = self._generate_id(founder_obj, 'person')
                    person_data = {
                        'id': person_id,
                        'name': founder_name,
                        'role': 'founder',
                        'roles': ['founder'],
                        'company': company.get('name'),
                        'source': 'yc',
                        'location': company.get('location', ''),
                        'location_code': '',
                        'batch': company.get('batch', ''),
                        'batch_code': ''
                    }
                    # Generate embedding for person if not already processed
                    if person_id not in self.processed_person_ids:
                        person_text = f"Name: {founder_name}\nRole: Founder\nCompany: {company.get('name')}"
                        person_embedding = self._get_embedding(person_text)
                        self.processed_person_ids.add(person_id)
                    else:
                        person_embedding = None
                    self.neo4j_store.create_person_with_embedding(person_data, person_embedding)
                    self.neo4j_store.create_relationship(
                        from_id=person_id,
                        to_id=company_id,
                        rel_type='FOUNDED',
                        properties={'role': 'Founder'}
                    )
            except Exception as e:
                print(f"[WARN] Backfill founders error for company {company.get('name','Unknown')}: {e}")
    
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
                    owner_login = repo.get('owner', {}).get('login', '')
                    owner_type = (repo.get('owner', {}).get('type') or '').lower()
                    homepage = repo.get('homepage', '')
                    repo_data = {
                        'id': repo_id,
                        'name': repo.get('name'),
                        'description': repo.get('description', ''),
                        'language': repo.get('language', ''),
                        'stars': repo.get('stars', 0),
                        'url': repo.get('url', ''),
                        'owner': repo.get('owner', {}),
                        'owner_login': owner_login,
                        'owner_type': owner_type,
                        'homepage': homepage,
                        'homepage_domain': self._extract_domain(homepage),
                        'topics': repo.get('topics', []),
                        'source': 'github'
                    }
                    
                    self.neo4j_store.create_repository_with_embedding(repo_data, embedding)
                    
                    # Create owner person only if it's a user (not organization)
                    if owner_login and owner_type == 'user':
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
            
            # Create company-repo relationships with confidence scores from discovery
            print("  - Creating company-repository ownership relationships...")
            
            # Use the mappings from the GitHub collector if available
            if hasattr(self, 'repo_company_mappings') and self.repo_company_mappings:
                print(f"    Creating {len(self.repo_company_mappings)} repo-company relationships...")
                for mapping in self.repo_company_mappings:
                    session.run(
                        """
                        MATCH (c:Company {id: $company_id})
                        MATCH (r:Repository {id: $repo_id})
                        MERGE (c)-[rel:OWNS]->(r)
                        SET rel.confidence = $confidence,
                            rel.method = $method,
                            rel.discovered_at = datetime()
                        """,
                        {
                            'company_id': mapping['company_id'],
                            'repo_id': mapping['repo_id'],
                            'confidence': mapping['confidence'],
                            'method': mapping['method']
                        }
                    )
            
            # Also run fallback matching for any repos not discovered through company-first approach
            print("  - Running fallback repo matching...")
            # Only create LIKELY_OWNS for repos without existing OWNS relationships
            session.run(
                """
                MATCH (c:Company), (r:Repository)
                WHERE c.website_domain IS NOT NULL AND c.website_domain <> ''
                  AND r.homepage_domain IS NOT NULL AND r.homepage_domain <> ''
                  AND c.website_domain = r.homepage_domain
                  AND NOT EXISTS((c)-[:OWNS]->(r))
                MERGE (c)-[rel:LIKELY_OWNS {method: 'fallback_domain', confidence: 0.8}]->(r)
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


    def _extract_domain(self, url: str) -> str:
        try:
            if not url:
                return ''
            host = urlparse(url).netloc.lower()
            if host.startswith('www.'):
                host = host[4:]
            return host
        except Exception:
            return ''

    def _extract_founders_from_text(self, text: str) -> List[str]:
        if not text:
            return []
        patterns = [
            r"Founders?:\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+)+(?:\s*(?:,|and)\s*[A-Z][a-z]+(?:\s[A-Z][a-z]+)+)*)",
            r"Founded by\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)+(?:\s*(?:,|and)\s*[A-Z][a-z]+(?:\s[A-Z][a-z]+)+)*)",
            r"Co-?founders?:\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+)+(?:\s*(?:,|and)\s*[A-Z][a-z]+(?:\s[A-Z][a-z]+)+)*)",
        ]
        for pat in patterns:
            m = re.search(pat, text, flags=re.IGNORECASE)
            if m:
                names_blob = m.group(1)
                parts = re.split(r',| and ', names_blob)
                names = [p.strip() for p in parts if len(p.strip().split()) >= 2]
                if names:
                    return names
        return []
    
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