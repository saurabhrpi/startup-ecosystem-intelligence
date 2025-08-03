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
        # Generate query embedding
        query_embedding = self._get_query_embedding(query)
        
        # Perform hybrid search (vector + graph)
        results = self.neo4j_store.hybrid_search(
            query_embedding=query_embedding,
            node_type=filter_type,
            top_k=top_k,
            graph_depth=graph_depth
        )
        
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
                'filter_type': filter_type
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
                data = match['data']
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
                data = match['data']
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
                    'label': result['data'].get('name', 'Unknown'),
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