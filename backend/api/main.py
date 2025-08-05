"""
Main FastAPI application for Startup Ecosystem Intelligence Platform
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from backend.api.graph_rag_service import GraphRAGService
from backend.agents.scoring_agent import ScoringAgent

# Initialize FastAPI app
app = FastAPI(
    title="Startup Ecosystem Intelligence API",
    description="AI-powered intelligence platform for startup ecosystem analysis",
    version="1.0.0"
)

# Configure CORS
import os

allowed_origins = ["*"]  # Default for development
if os.getenv("ENVIRONMENT") == "production":
    # Get allowed origins from environment variable
    origins_str = os.getenv("ALLOWED_ORIGINS", "")
    allowed_origins = [origin.strip() for origin in origins_str.split(",") if origin.strip()]
    if not allowed_origins:
        allowed_origins = ["*"]  # Fallback

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services  
graph_rag_service = GraphRAGService()
scoring_agent = ScoringAgent()

# Shutdown handler
@app.on_event("shutdown")
async def shutdown_event():
    """Properly close Neo4j connections on shutdown"""
    try:
        if hasattr(graph_rag_service, 'neo4j_store') and graph_rag_service.neo4j_store:
            graph_rag_service.neo4j_store.close()
        if hasattr(scoring_agent, 'neo4j_store') and scoring_agent.neo4j_store:
            scoring_agent.neo4j_store.close()
    except Exception as e:
        print(f"Error during shutdown: {e}")

# Request/Response models
class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 10
    filter_type: Optional[str] = None
    filter_source: Optional[str] = None

class SearchResponse(BaseModel):
    query: str
    matches: List[Dict[str, Any]]
    response: str
    total_results: int

class HealthResponse(BaseModel):
    status: str
    message: str

class ScoreRequest(BaseModel):
    company_ids: List[str]

class CompanyScore(BaseModel):
    company_id: str
    company_name: str
    total_score: float
    scores: Dict[str, float]
    investment_thesis: str
    scoring_date: str
    rank: Optional[int] = None

class ScoreResponse(BaseModel):
    scores: List[CompanyScore]
    methodology: Optional[Dict[str, Any]] = None

# Routes
@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint"""
    return {
        "status": "healthy",
        "message": "Startup Ecosystem Intelligence API is running"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "All systems operational"
    }

@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Search the startup ecosystem database
    
    Args:
        request: SearchRequest with query and optional filters
        
    Returns:
        SearchResponse with matches and AI-generated response
    """    
    try:
        
        result = graph_rag_service.search(
            query=request.query,
            top_k=request.top_k,
            filter_type=request.filter_type,
            graph_depth=2
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search", response_model=SearchResponse)
async def search_get(
    query: str = Query(..., description="Search query"),
    top_k: int = Query(10, description="Number of results to return"),
    filter_type: Optional[str] = Query(None, description="Filter by entity type"),
    filter_source: Optional[str] = Query(None, description="Filter by data source")
):
    """
    Search the startup ecosystem database (GET version)
    """
    try:
        result = graph_rag_service.search(
            query=query,
            top_k=top_k,
            filter_type=filter_type,
            graph_depth=2
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/similar/{entity_id}")
async def find_similar(
    entity_id: str,
    top_k: int = Query(5, description="Number of similar entities to return")
):
    """
    Find entities similar to the given entity
    
    Args:
        entity_id: ID of the entity to find similar ones for
        top_k: Number of similar entities to return
        
    Returns:
        List of similar entities with metadata
    """
    try:
        result = graph_rag_service.find_similar_entities(entity_id, top_k)
        if not result['similar_entities']:
            raise HTTPException(status_code=404, detail="Entity not found")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/network/{entity_id}")
async def get_entity_network(
    entity_id: str,
    depth: int = Query(2, description="Depth of network to retrieve")
):
    """
    Get the network graph around an entity
    
    Args:
        entity_id: ID of the entity
        depth: How many hops to traverse (default: 2)
        
    Returns:
        Network graph with nodes and edges
    """
    try:
        network = graph_rag_service.get_entity_network(entity_id, depth)
        if not network['nodes']:
            raise HTTPException(status_code=404, detail="Entity not found")
        return network
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test-search-detailed")
async def test_search_detailed(query: str = "AI"):
    """Test the actual search with detailed debug info"""
    try:
        # Step 1: Test embedding generation
        embedding = None
        embedding_success = False
        embedding_error = None
        embedding_length = 0
        search_error = None
        
        try:
            embedding = graph_rag_service._get_query_embedding(query)
            embedding_success = True
            embedding_length = len(embedding) if embedding else 0
        except Exception as e:
            embedding_success = False
            embedding_error = str(e)
        
        # Step 2: Test vector search if embedding worked
        search_results = []
        if embedding:
            try:
                search_results = graph_rag_service.neo4j_store.vector_search(
                    query_embedding=embedding,
                    node_type="company",
                    top_k=5,
                    min_score=0.5  # Lower threshold for testing
                )
            except Exception as e:
                search_error = str(e)
        
        return {
            "query": query,
            "embedding_generated": embedding_success,
            "embedding_length": embedding_length,
            "embedding_error": embedding_error,
            "search_results_count": len(search_results),
            "search_results": search_results[:2] if search_results else [],
            "search_error": search_error,
            "openai_configured": bool(os.getenv('OPENAI_API_KEY'))
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/test-search")
async def test_search():
    """Test search functionality with debug info"""
    try:
        # Test direct Neo4j query
        store = graph_rag_service.neo4j_store
        with store.driver.session() as session:
            # Simple query to get a few companies
            result = session.run("""
                MATCH (c:Company)
                WHERE c.embedding IS NOT NULL
                RETURN c.id as id, c.name as name, c.industries as industries
                LIMIT 5
            """)
            companies = [dict(record) for record in result]
        
        return {
            "message": "Test search endpoint",
            "neo4j_connected": True,
            "sample_companies": companies,
            "total_companies": len(companies)
        }
    except Exception as e:
        return {
            "error": str(e),
            "neo4j_connected": False
        }

@app.get("/stats")
async def get_stats():
    """
    Get statistics about the database
    """
    try:
        # Get stats from Neo4j
        stats = graph_rag_service.neo4j_store.get_statistics()
        
        return {
            "total_nodes": stats['total_nodes'],
            "total_relationships": stats['total_relationships'],
            "nodes_by_type": {
                "companies": stats.get('company_count', 0),
                "people": stats.get('person_count', 0),
                "repositories": stats.get('repository_count', 0),
                "products": stats.get('product_count', 0)
            },
            "nodes_with_embeddings": {
                "companies": stats.get('company_with_embeddings', 0),
                "people": stats.get('person_with_embeddings', 0),
                "repositories": stats.get('repository_with_embeddings', 0),
                "products": stats.get('product_with_embeddings', 0)
            },
            "relationships": stats.get('relationships', {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/score/{company_id}")
async def score_company(company_id: str):
    """
    Score a single company using the AI Scoring Agent
    
    Args:
        company_id: ID of the company to score
        
    Returns:
        Detailed scoring results with investment thesis
    """
    try:
        result = await scoring_agent.score_company(company_id)
        if 'error' in result:
            raise HTTPException(status_code=404, detail=result['error'])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/score/batch", response_model=ScoreResponse)
async def score_batch(request: ScoreRequest):
    """
    Score multiple companies and rank them
    
    Args:
        request: ScoreRequest with list of company IDs
        
    Returns:
        ScoreResponse with ranked companies and scoring methodology
    """
    try:
        if not request.company_ids:
            raise HTTPException(status_code=400, detail="No company IDs provided")
        
        if len(request.company_ids) > 50:
            raise HTTPException(status_code=400, detail="Maximum 50 companies per batch")
        
        scored_companies = await scoring_agent.score_multiple_companies(request.company_ids)
        methodology = scoring_agent.get_scoring_methodology()
        
        return ScoreResponse(
            scores=scored_companies,
            methodology=methodology
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/score/methodology")
async def get_scoring_methodology():
    """
    Get the scoring methodology used by the AI Scoring Agent
    
    Returns:
        Detailed explanation of scoring factors and weights
    """
    try:
        return scoring_agent.get_scoring_methodology()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/score/top", response_model=ScoreResponse)
async def get_top_scored_companies(
    limit: int = Query(10, description="Number of top companies to return", ge=1, le=50),
    batch: Optional[str] = Query(None, description="Filter by YC batch (e.g., 'S22', 'W23')"),
    industry: Optional[str] = Query(None, description="Filter by industry")
):
    """
    Get top-scored companies based on filters
    
    Args:
        limit: Number of companies to return (1-50)
        batch: Optional YC batch filter
        industry: Optional industry filter
        
    Returns:
        Top-scored companies with full scoring details
    """
    try:
        # Query Neo4j for companies matching filters
        with scoring_agent.neo4j_store.driver.session() as session:
            where_clauses = []
            params = {"limit": limit}
            
            if batch:
                where_clauses.append("c.batch = $batch")
                params["batch"] = batch
            
            if industry:
                where_clauses.append("$industry IN c.industries")
                params["industry"] = industry
            
            where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
            
            query = f"""
            MATCH (c:Company)
            {where_clause}
            RETURN c.id as id
            LIMIT $limit
            """
            
            result = session.run(query, params)
            company_ids = [record["id"] for record in result]
        
        if not company_ids:
            return ScoreResponse(scores=[], methodology=scoring_agent.get_scoring_methodology())
        
        # Score the companies
        scored_companies = await scoring_agent.score_multiple_companies(company_ids)
        
        return ScoreResponse(
            scores=scored_companies,
            methodology=scoring_agent.get_scoring_methodology()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)