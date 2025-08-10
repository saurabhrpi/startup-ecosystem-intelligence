"""
Graph RAG Service V2 - Uses Neo4j for both vector search and graph relationships
"""
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import openai
from backend.utils.neo4j_store import Neo4jStore
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GraphRAGService:
    def __init__(self):
        # Initialize Neo4j store
        self.neo4j_store = Neo4jStore()
        
        # Initialize OpenAI
        openai.api_key = os.getenv('OPENAI_API_KEY')
        self.openai_client = openai
        
        # Location aliases are loaded dynamically at runtime from
        # 1) Neo4j Location nodes (if present), else
        # 2) LOCATION_ALIASES_JSON env var (JSON object), else
        # 3) empty map (no location filtering).
        self.location_aliases: Dict[str, List[str]] = self._load_location_aliases()
    
    def search(
        self, 
        query: str, 
        top_k: int = 10,
        graph_depth: int = 2,
        filter_type: Optional[str] = None,
        min_score: float = 0.7
    ) -> Dict[str, Any]:
        """
        Perform Graph RAG search using Neo4j's hybrid capabilities
        """
        query_embedding = self._get_query_embedding(query)

        # Extract optional filters from the free-text query (e.g., location hints like "NYC")
        location_code = self._extract_location_from_query(query)
        batch_filters = self._extract_batch_from_query(query)
        exclude_locations = self._derive_exclude_locations(location_code)
        
        # Perform hybrid search (vector + graph)
        adjusted_top_k = top_k * 2 if location_code else top_k
        results = self.neo4j_store.hybrid_search(
            query_embedding=query_embedding,
            node_type=filter_type,
            top_k=adjusted_top_k,
            graph_depth=graph_depth,
            location_filters=self._aliases_for_code(location_code) if location_code else None,
            batch_filters=batch_filters,
            exclude_location_filters=exclude_locations
        )

        # If a location was detected in the query, enforce strict filtering in all cases
        if location_code:
            matching: List[Dict[str, Any]] = []
            for r in results:
                location_text = (r.get('metadata') or {}).get('location', '') or ''
                if self._location_matches(location_code, location_text):
                    matching.append(r)
            results = matching[:top_k]

        # If a batch intent was detected and no results, fall back to direct batch query
        if batch_filters and not results:
            results = self.neo4j_store.find_companies_by_batch(batch_filters, limit=top_k)
        
        # Generate intelligent response with graph context
        response = self._generate_graph_aware_response(query, results)
        
        # Build visualization data
        graph_data = self._build_visualization_data(results[:5])
        
        return {
            'query': query,
            'matches': results,  # Changed from 'results' to 'matches' to match frontend
            'response': response,
            'graph': graph_data,
            'total_results': len(results),
            'search_params': {
                'graph_depth': graph_depth,
                'min_score': min_score,
                'filter_type': filter_type,
                'applied_filters': {
                    'location': location_code,
                    'batch': batch_filters,
                    'exclude_locations': exclude_locations
                }
            }
        }
    
    def find_similar_entities(self, entity_id: str, top_k: int = 5) -> Dict[str, Any]:
        """Find entities similar to a given entity"""
        similar = self.neo4j_store.find_similar_nodes(entity_id, top_k)
        
        return {
            'entity_id': entity_id,
            'similar_entities': similar,
            'count': len(similar)
        }
    
    def _extract_location_from_query(self, query: str) -> Optional[str]:
        """Extract a canonical location code from a free-text query using simple alias matching.
        Returns a key from self.location_aliases (e.g., 'nyc') when matched, else None.
        """
        q = (query or '').lower()
        for canonical, aliases in self.location_aliases.items():
            for alias in aliases:
                if alias in q:
                    return canonical
        return None
    
    def _location_matches(self, canonical_code: str, location_text: str) -> bool:
        """Check if a company location string matches a canonical location code using alias matching."""
        if not canonical_code or not location_text:
            return False
        loc = location_text.lower()
        aliases = self.location_aliases.get(canonical_code, [])
        return any(alias in loc for alias in aliases)

    def _aliases_for_code(self, canonical_code: Optional[str]) -> Optional[List[str]]:
        if not canonical_code:
            return None
        return [a.lower() for a in self.location_aliases.get(canonical_code, [])]

    def _load_location_aliases(self) -> Dict[str, List[str]]:
        """Load location aliases from Neo4j if available; fall back to env JSON; else empty.
        Expected Neo4j schema: (l:Location { canonical: 'nyc', aliases: ['nyc','new york', ...] })
        Expected ENV: LOCATION_ALIASES_JSON = '{"nyc":["nyc","new york"], ...}'
        """
        # Try Neo4j
        try:
            aliases: Dict[str, List[str]] = {}
            with self.neo4j_store.driver.session() as session:
                query = """
                MATCH (l:Location)
                RETURN l.canonical AS canonical, coalesce(l.aliases, []) AS aliases
                """
                rows = session.run(query)
                for row in rows:
                    canonical = (row.get('canonical') or '').strip().lower()
                    alias_list = [str(a).strip().lower() for a in (row.get('aliases') or []) if str(a).strip()]
                    if canonical:
                        aliases[canonical] = alias_list
            if aliases:
                return aliases
        except Exception as e:
            logger.warning(f"Failed to load Location aliases from Neo4j: {e}")
        # Try ENV
        try:
            import json
            raw = os.getenv('LOCATION_ALIASES_JSON')
            if raw:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    normalized: Dict[str, List[str]] = {}
                    for k, v in parsed.items():
                        if isinstance(v, list):
                            normalized[k.lower()] = [str(a).strip().lower() for a in v if str(a).strip()]
                    return normalized
        except Exception as e:
            logger.warning(f"Failed to load LOCATION_ALIASES_JSON: {e}")
        # Default
        return {}

    def _extract_batch_from_query(self, query: str) -> Optional[List[str]]:
        """Extract implied YC batch filters from natural text, e.g., 'YC W24', 'Winter 2024', 'S24'.
        Returns a list of lowercase substrings to match against c.batch.
        """
        if not query:
            return None
        q = query.lower()
        tokens: List[str] = []
        # Common patterns: W24, S24, W2024, Winter 2024, Summer 2024
        import re
        m = re.search(r"\b([ws])\s*'?\s*(20)?(\d{2})\b", q)
        if m:
            # Map 'w'/'s' to 'winter'/'summer', and normalize year to 20xx
            season = 'winter' if m.group(1) == 'w' else 'summer'
            year2 = m.group(3)
            year = f"20{year2}"
            # Include long form, year, and compact form (e.g., w24)
            tokens.extend([f"{season} {year}", f"{year}", f"{m.group(1)}{year2}"])
        m2 = re.search(r"\b(winter|summer)\s+20(\d{2})\b", q)
        if m2:
            tokens.append(f"{m2.group(1)} 20{m2.group(2)}")
        # Also handle explicit phrases like 'yc w24'
        m3 = re.search(r"yc\s+([ws])\s*(\d{2})\b", q)
        if m3:
            season = 'winter' if m3.group(1) == 'w' else 'summer'
            tokens.append(f"{season} 20{m3.group(2)}")
        # Deduplicate & return
        tokens = list({t for t in tokens if t})
        return tokens or None

    def _derive_exclude_locations(self, canonical_code: Optional[str]) -> Optional[List[str]]:
        """Given a selected canonical location (e.g., 'sf'), derive alias lists for other major hubs to exclude (e.g., NYC, LA).
        This reduces far-off false positives like NYC when searching for SF.
        """
        if not canonical_code:
            return None
        hubs = set(self.location_aliases.keys())
        if canonical_code in hubs:
            hubs.remove(canonical_code)
        # Heuristic: only exclude well-known distant hubs that frequently collide
        candidates = [k for k in hubs if k in {'nyc', 'la', 'boston', 'london'}]
        exclude_aliases: List[str] = []
        for k in candidates:
            exclude_aliases.extend(self.location_aliases.get(k, []))
        return [a.lower() for a in exclude_aliases] or None
    
    def get_entity_network(self, entity_id: str, depth: int = 2) -> Dict[str, Any]:
        """Get the network around an entity"""
        network = self.neo4j_store.get_node_with_connections(entity_id, depth)
        
        # Add explanation of key connections
        if network['nodes']:
            explanation = self._explain_network(network)
            network['explanation'] = explanation
        
        return network
    
    def _get_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for the search query"""
        response = self.openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        return response.data[0].embedding
    
    def _generate_graph_aware_response(self, query: str, results: List[Dict[str, Any]]) -> str:
        """Generate response that includes graph relationship insights"""
        if not results:
            return "No relevant information found for your query."
        
        # Separate direct matches from graph-expanded results
        direct_matches = [r for r in results if 'connection' not in r]
        connected_matches = [r for r in results if 'connection' in r]
        
        # Build context
        context_parts = ["Based on my analysis of the startup ecosystem:\n"]
        
        # Direct matches
        if direct_matches:
            context_parts.append("**Direct Matches:**")
            for i, match in enumerate(direct_matches[:3], 1):
                data = match['metadata']  # Changed from 'data' to 'metadata'
                context_parts.append(
                    f"{i}. **{data.get('name', 'Unknown')}** ({match['type']})"
                )
                if 'description' in data and data['description']:
                    context_parts.append(f"   - {data['description'][:150]}...")
                context_parts.append(f"   - Relevance Score: {match['score']:.2f}")
        
        # Connected entities
        if connected_matches:
            context_parts.append("\n**Related Entities (discovered through connections):**")
            for match in connected_matches[:3]:
                data = match['metadata']  # Changed from 'data' to 'metadata'
                conn = match['connection']
                context_parts.append(
                    f"- **{data.get('name', 'Unknown')}** "
                    f"(connected via {' → '.join(conn['path'])})"
                )
                if 'description' in data and data['description']:
                    context_parts.append(f"  {data['description'][:100]}...")
        
        context = "\n".join(context_parts)
        
        # Generate intelligent response
        prompt = f"""Based on the following search results from our startup ecosystem knowledge graph, 
provide an insightful response to the user's query. Focus on:
1. Directly answering the query
2. Highlighting interesting connections between entities
3. Providing actionable insights
4. Mentioning specific names and relationships

User Query: {query}

Search Results:
{context}

Provide a comprehensive yet concise response (max 3-4 paragraphs)."""

        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": "You are an AI analyst specializing in startup ecosystems. "
                              "You excel at finding hidden connections and providing strategic insights. "
                              "Focus on being specific and actionable."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content
    
    def _build_visualization_data(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build graph data for visualization"""
        nodes = []
        edges = []
        seen_nodes = set()
        
        for result in results:
            # Add main node
            node_id = result['id']
            if node_id not in seen_nodes:
                seen_nodes.add(node_id)
                nodes.append({
                    'id': node_id,
                    'label': result['metadata'].get('name', 'Unknown'),
                    'type': result['type'],
                    'score': result.get('score', 0)
                })
            
            # Add connection edges
            if 'connection' in result:
                conn = result['connection']
                from_id = conn['from_id']
                
                # Ensure source node is in the graph
                if from_id not in seen_nodes:
                    # We need to get info about the source node
                    seen_nodes.add(from_id)
                    nodes.append({
                        'id': from_id,
                        'label': f"Entity {from_id[:8]}...",
                        'type': 'Unknown'
                    })
                
                edges.append({
                    'from': from_id,
                    'to': node_id,
                    'label': conn['path'][-1] if conn['path'] else 'connected'
                })
        
        return {
            'nodes': nodes,
            'edges': edges
        }
    
    def _explain_network(self, network: Dict[str, Any]) -> str:
        """Generate explanation of a network"""
        if not network['nodes']:
            return "No network found."
        
        center_node = network['nodes'][0]
        num_connections = len(network['nodes']) - 1
        
        explanation = (
            f"{center_node['name']} ({center_node['type']}) has "
            f"{num_connections} connected entities in the network."
        )
        
        # Analyze relationship types
        rel_types = {}
        for edge in network['edges']:
            rel_type = edge['type']
            rel_types[rel_type] = rel_types.get(rel_type, 0) + 1
        
        if rel_types:
            explanation += " Relationships include: "
            rel_parts = [f"{count} {rel_type}" for rel_type, count in rel_types.items()]
            explanation += ", ".join(rel_parts) + "."
        
        return explanation