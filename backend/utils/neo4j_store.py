"""
Neo4j Store - Unified storage for both graph relationships and vector embeddings
"""
import os
import time
from typing import List, Dict, Any, Optional, Tuple
from neo4j import GraphDatabase
from dotenv import load_dotenv
import numpy as np
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def retry_on_failure(max_retries=3, delay=1.0):
    """Decorator to retry Neo4j operations on failure"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay} seconds...")
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_retries} attempts failed.")
            raise last_exception
        return wrapper
    return decorator

class Neo4jStore:
    def __init__(self):
        # Neo4j connection details
        self.uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.user = os.getenv('NEO4J_USER', 'neo4j')
        self.password = os.getenv('NEO4J_PASSWORD', 'password')
        
        try:
            # Configure driver with connection pooling and timeouts
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password),
                max_connection_lifetime=3600,  # 1 hour
                max_connection_pool_size=50,
                connection_acquisition_timeout=60.0,  # 60 seconds
                connection_timeout=30.0,  # 30 seconds
                keep_alive=True
            )
            self._verify_connection()
            self._create_indexes()
            logger.info(f"Connected to Neo4j at {self.uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    @retry_on_failure(max_retries=3, delay=1.0)
    def _verify_connection(self):
        """Verify Neo4j connection"""
        with self.driver.session() as session:
            result = session.run("RETURN 1 as test")
            assert result.single()['test'] == 1
    
    def _create_indexes(self):
        """Create indexes for better query performance"""
        with self.driver.session() as session:
            # Create indexes for each entity type
            indexes = [
                # ID and name indexes
                "CREATE INDEX company_id IF NOT EXISTS FOR (c:Company) ON (c.id)",
                "CREATE INDEX company_name IF NOT EXISTS FOR (c:Company) ON (c.name)",
                "CREATE INDEX person_id IF NOT EXISTS FOR (p:Person) ON (p.id)",
                "CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.name)",
                "CREATE INDEX repo_id IF NOT EXISTS FOR (r:Repository) ON (r.id)",
                "CREATE INDEX repo_name IF NOT EXISTS FOR (r:Repository) ON (r.name)",
                "CREATE INDEX product_id IF NOT EXISTS FOR (p:Product) ON (p.id)",
                "CREATE INDEX product_name IF NOT EXISTS FOR (p:Product) ON (p.name)",
                
                # Vector indexes for similarity search
                "CREATE VECTOR INDEX company_embedding IF NOT EXISTS FOR (c:Company) ON (c.embedding) OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}",
                "CREATE VECTOR INDEX person_embedding IF NOT EXISTS FOR (p:Person) ON (p.embedding) OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}",
                "CREATE VECTOR INDEX repo_embedding IF NOT EXISTS FOR (r:Repository) ON (r.embedding) OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}",
                "CREATE VECTOR INDEX product_embedding IF NOT EXISTS FOR (p:Product) ON (p.embedding) OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}"
            ]
            
            for index_query in indexes:
                try:
                    session.run(index_query)
                    logger.info(f"Created/verified index: {index_query.split(' ')[2]}")
                except Exception as e:
                    # Neo4j will throw an error if index already exists, which is fine
                    if "already exists" not in str(e):
                        logger.warning(f"Index creation warning: {e}")
    
    def create_company_with_embedding(self, company_data: Dict[str, Any], embedding: List[float]) -> None:
        """Create a company node with its embedding"""
        with self.driver.session() as session:
            query = """
            MERGE (c:Company {id: $id})
            SET c.name = $name,
                c.description = $description,
                c.location = $location,
                c.website = $website,
                c.batch = $batch,
                c.industries = $industries,
                c.source = $source,
                c.embedding = $embedding,
                c.created_at = datetime()
            """
            
            session.run(query, {
                'id': company_data.get('id'),
                'name': company_data.get('name'),
                'description': company_data.get('description', ''),
                'location': company_data.get('location', ''),
                'website': company_data.get('website', ''),
                'batch': company_data.get('batch', ''),
                'industries': company_data.get('industries', []),
                'source': company_data.get('source', 'unknown'),
                'embedding': embedding
            })
    
    def create_person_with_embedding(self, person_data: Dict[str, Any], embedding: Optional[List[float]] = None) -> None:
        """Create a person node with optional embedding"""
        with self.driver.session() as session:
            query = """
            MERGE (p:Person {id: $id})
            SET p.name = $name,
                p.role = $role,
                p.company = $company,
                p.source = $source,
                p.created_at = datetime()
            """
            
            params = {
                'id': person_data.get('id'),
                'name': person_data.get('name'),
                'role': person_data.get('role', ''),
                'company': person_data.get('company', ''),
                'source': person_data.get('source', 'unknown')
            }
            
            # Add embedding if provided
            if embedding:
                query = query.replace("p.created_at = datetime()", 
                                    "p.embedding = $embedding, p.created_at = datetime()")
                params['embedding'] = embedding
            
            session.run(query, params)
    
    def create_repository_with_embedding(self, repo_data: Dict[str, Any], embedding: List[float]) -> None:
        """Create a repository node with its embedding"""
        with self.driver.session() as session:
            query = """
            MERGE (r:Repository {id: $id})
            SET r.name = $name,
                r.description = $description,
                r.language = $language,
                r.stars = $stars,
                r.url = $url,
                r.owner = $owner,
                r.topics = $topics,
                r.source = $source,
                r.embedding = $embedding,
                r.created_at = datetime()
            """
            
            session.run(query, {
                'id': repo_data.get('id'),
                'name': repo_data.get('name'),
                'description': repo_data.get('description', ''),
                'language': repo_data.get('language', ''),
                'stars': repo_data.get('stars', 0),
                'url': repo_data.get('url', ''),
                'owner': repo_data.get('owner', {}).get('login', ''),
                'topics': repo_data.get('topics', []),
                'source': repo_data.get('source', 'github'),
                'embedding': embedding
            })
    
    @retry_on_failure(max_retries=3, delay=1.0)
    def vector_search(
        self, 
        query_embedding: List[float], 
        node_type: str = None, 
        top_k: int = 10,
        min_score: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search across nodes
        
        Args:
            query_embedding: Query vector
            node_type: Type of node to search (Company, Person, Repository, Product)
            top_k: Number of results to return
            min_score: Minimum similarity score
        """
        # Add connectivity check
        try:
            print("Trying to verify connection")
            self.driver.verify_connectivity()
            print("Connection verified!")
        except Exception as e:
            print(f"Connection failed: {e}")
            logger.error(f"Neo4j connection failed: {e}")
            raise
        
        print("node_type")
        print(node_type)
        
        with self.driver.session() as session:
            # Build node pattern based on type
            if node_type:
                node_pattern = f"(n:{node_type})"
            else:
                node_pattern = "(n)"
            
            
            #query = f"""
            #MATCH {node_pattern}
            #WHERE n.embedding IS NOT NULL
            #WITH n, gds.similarity.cosine(n.embedding, $query_embedding) AS score
            #WHERE score >= $min_score
            #RETURN n, score, labels(n) as node_labels
            #ORDER BY score DESC
            #LIMIT $top_k
            #"""
            
            query = f"""
            MATCH (n:Company)
            WHERE n.embedding IS NOT NULL
            RETURN n
            LIMIT 5
            """
            
            print("node_pattern")
            print(node_pattern)
            
            print("query_embedding")
            print(query_embedding)
            
            print("Calling session.run")
            
            #results = session.run(query, {
            #    'query_embedding': query_embedding,
            #    'min_score': min_score,
            #    'top_k': top_k
            #})
            
            results = session.run(query)
            
            print("Out of session.run")          
            matches = []
                        
            # Convert to list to ensure all results are consumed
            records = list(results)
            
            
            for i, record in enumerate(records):
                print(f"record {i}: {dict(record)}")
                node = record['n']
                node_data = dict(node)
                node_data.pop('embedding', None)  # Remove embedding from response
                
                matches.append({
                    'id': node_data.get('id'),
                    'score': record['score'],
                    'type': record['node_labels'][0] if record['node_labels'] else 'Unknown',
                    'data': node_data
                })            
            return matches
    
    def hybrid_search(
        self,
        query_embedding: List[float],
        graph_pattern: Optional[str] = None,
        node_type: Optional[str] = None,
        top_k: int = 10,
        graph_depth: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining vector similarity and graph patterns
        
        Args:
            query_embedding: Query vector
            graph_pattern: Optional Cypher pattern to match
            node_type: Type of node to search
            top_k: Number of results
            graph_depth: Depth for graph expansion
        """
        # First, get vector search results
        vector_results = self.vector_search(query_embedding, node_type, top_k * 2)
        
        # Then expand using graph relationships
        expanded_results = []
        seen_ids = set()
        
        with self.driver.session() as session:
            for result in vector_results[:5]:  # Expand top 5
                node_id = result['id']
                seen_ids.add(node_id)
                
                # Get connected nodes
                expansion_query = """
                MATCH (start {id: $node_id})
                MATCH path = (start)-[*1..$depth]-(connected)
                WHERE connected.id <> start.id
                WITH connected, 
                     length(path) as distance,
                     [rel in relationships(path) | type(rel)] as rel_types
                RETURN DISTINCT connected, distance, rel_types
                ORDER BY distance
                LIMIT 20
                """
                
                expansion_results = session.run(expansion_query, {
                    'node_id': node_id,
                    'depth': graph_depth
                })
                
                for record in expansion_results:
                    conn_node = record['connected']
                    conn_id = conn_node.get('id')
                    
                    if conn_id not in seen_ids:
                        seen_ids.add(conn_id)
                        
                        # Calculate combined score
                        vector_score = result['score']
                        graph_score = 1.0 / (record['distance'] + 1)
                        combined_score = (vector_score * 0.7) + (graph_score * 0.3)
                        
                        expanded_results.append({
                            'id': conn_id,
                            'score': combined_score,
                            'type': list(conn_node.labels)[0] if conn_node.labels else 'Unknown',
                            'data': dict(conn_node),
                            'connection': {
                                'from_id': node_id,
                                'distance': record['distance'],
                                'path': record['rel_types']
                            }
                        })
        
        # Combine and sort all results
        all_results = vector_results + expanded_results
        all_results.sort(key=lambda x: x['score'], reverse=True)
        
        return all_results[:top_k]
    
    def create_relationship(self, from_id: str, to_id: str, rel_type: str, properties: Dict = None) -> None:
        """Create a relationship between two nodes"""
        with self.driver.session() as session:
            # Build property string if properties provided
            prop_string = ""
            if properties:
                props = [f"{k}: ${k}" for k in properties.keys()]
                prop_string = "{" + ", ".join(props) + "}"
            
            query = f"""
            MATCH (a {{id: $from_id}})
            MATCH (b {{id: $to_id}})
            MERGE (a)-[r:{rel_type} {prop_string}]->(b)
            """
            
            params = {
                'from_id': from_id,
                'to_id': to_id
            }
            if properties:
                params.update(properties)
            
            session.run(query, params)
    
    def find_similar_nodes(self, node_id: str, top_k: int = 5, min_score: float = 0.8) -> List[Dict[str, Any]]:
        """Find nodes similar to a given node based on embedding similarity"""
        with self.driver.session() as session:
            query = """
            MATCH (target {id: $node_id})
            WHERE target.embedding IS NOT NULL
            MATCH (similar)
            WHERE similar.id <> target.id 
              AND similar.embedding IS NOT NULL
              AND labels(similar) = labels(target)
            WITH similar, 
                 gds.similarity.cosine(target.embedding, similar.embedding) AS score
            WHERE score >= $min_score
            RETURN similar, score
            ORDER BY score DESC
            LIMIT $top_k
            """
            
            results = session.run(query, {
                'node_id': node_id,
                'min_score': min_score,
                'top_k': top_k
            })
            
            similar_nodes = []
            for record in results:
                node = record['similar']
                node_data = dict(node)
                node_data.pop('embedding', None)
                
                similar_nodes.append({
                    'id': node_data.get('id'),
                    'score': record['score'],
                    'data': node_data
                })
            
            return similar_nodes
    
    def get_node_with_connections(self, node_id: str, depth: int = 1) -> Dict[str, Any]:
        """Get a node and its connections for visualization"""
        with self.driver.session() as session:
            query = """
            MATCH (center {id: $node_id})
            OPTIONAL MATCH path = (center)-[*1..$depth]-(connected)
            WITH center, 
                 collect(DISTINCT connected) as connected_nodes,
                 collect(DISTINCT relationships(path)) as all_rels
            UNWIND all_rels as rels
            UNWIND rels as rel
            WITH center, connected_nodes, collect(DISTINCT rel) as relationships
            RETURN center,
                   connected_nodes,
                   [r in relationships | {
                       from: startNode(r).id,
                       to: endNode(r).id,
                       type: type(r)
                   }] as edges
            """
            
            result = session.run(query, node_id=node_id, depth=depth)
            record = result.single()
            
            if record:
                # Format response
                nodes = [self._node_to_dict(record['center'])]
                for node in record['connected_nodes']:
                    if node:
                        nodes.append(self._node_to_dict(node))
                
                return {
                    'nodes': nodes,
                    'edges': record['edges'] or []
                }
            
            return {'nodes': [], 'edges': []}
    
    def _node_to_dict(self, node) -> Dict[str, Any]:
        """Convert Neo4j node to dictionary"""
        node_dict = dict(node)
        node_dict.pop('embedding', None)  # Remove embedding from response
        
        return {
            'id': node_dict.get('id'),
            'name': node_dict.get('name'),
            'type': list(node.labels)[0] if node.labels else 'Unknown',
            'properties': node_dict
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        with self.driver.session() as session:
            stats = {}
            
            # Count nodes by type
            node_types = ['Company', 'Person', 'Repository', 'Product']
            for node_type in node_types:
                # Total count
                count_query = f"MATCH (n:{node_type}) RETURN count(n) as count"
                result = session.run(count_query)
                stats[f'{node_type.lower()}_count'] = result.single()['count']
                
                # Count with embeddings
                embedding_query = f"MATCH (n:{node_type}) WHERE n.embedding IS NOT NULL RETURN count(n) as count"
                result = session.run(embedding_query)
                stats[f'{node_type.lower()}_with_embeddings'] = result.single()['count']
            
            # Count relationships
            rel_query = "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count"
            result = session.run(rel_query)
            
            stats['relationships'] = {}
            for record in result:
                stats['relationships'][record['type']] = record['count']
            
            # Total counts
            total_nodes = session.run("MATCH (n) RETURN count(n) as count").single()['count']
            total_rels = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()['count']
            
            stats['total_nodes'] = total_nodes
            stats['total_relationships'] = total_rels
            
            return stats
    
    def close(self):
        """Close the database connection"""
        try:
            if hasattr(self, 'driver') and self.driver:
                self.driver.close()
                logger.info("Neo4j connection closed successfully")
        except Exception as e:
            logger.warning(f"Error closing Neo4j connection: {e}")