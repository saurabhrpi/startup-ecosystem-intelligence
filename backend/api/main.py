"""
Main FastAPI application for Startup Ecosystem Intelligence Platform
"""
from fastapi import FastAPI, HTTPException, Query, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from backend.api.graph_rag_service import GraphRAGService
from backend.agents.scoring_agent import ScoringAgent
from backend.config import settings
import time

# Simple in-memory rate limiter: key -> [window_start_ts, count]
rate_buckets: Dict[str, Dict[str, float]] = {}

def require_api_key(request: Request):
    expected = settings.api_key
    if not expected:
        # If no key configured, allow (useful for local dev)
        return True
    provided = request.headers.get('x-api-key') or request.headers.get('authorization', '').replace('Bearer ', '')
    if provided != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

def rate_limit(request: Request):
    # Build a key from API key (if present) and IP
    api_key = request.headers.get('x-api-key') or 'anon'
    ip = request.client.host if request.client else 'unknown'
    key = f"{api_key}:{ip}"
    now = time.time()
    window = 60.0
    limit = settings.rate_limit_rpm
    bucket = rate_buckets.get(key)
    if not bucket or now - bucket['ts'] >= window:
        rate_buckets[key] = {'ts': now, 'count': 1}
        return True
    if bucket['count'] >= limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    bucket['count'] += 1
    return True

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
    min_stars: Optional[int] = None
    person_roles: Optional[List[str]] = None

class SearchResponse(BaseModel):
    query: str
    matches: List[Dict[str, Any]]
    response: str
    total_results: int
    graph: Optional[Dict[str, Any]] = None
    search_params: Optional[Dict[str, Any]] = None

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

# Removed /company-count endpoint - use /ecosystem-stats instead

@app.get("/ecosystem-stats")
async def get_ecosystem_stats():
    """New endpoint for ecosystem statistics"""
    try:
        with graph_rag_service.neo4j_store.driver.session() as session:
            # Get company count
            result = session.run("MATCH (c:Company) RETURN count(c) as count")
            company_count = result.single()["count"]
            
            # Get embeddings count
            result_emb = session.run("MATCH (n) WHERE n.embedding IS NOT NULL RETURN count(n) as count")
            embeddings_count = result_emb.single()["count"]
            
            # Count distinct data sources actually present in the graph
            result_sources = session.run(
                "MATCH (n) WHERE n.source IS NOT NULL RETURN count(DISTINCT n.source) as count"
            )
            data_sources_count = result_sources.single()["count"] or 0
            
            return {
                "total_companies": company_count,
                "total_embeddings": embeddings_count,
                "data_sources": data_sources_count
            }
    except Exception as e:
        # Fallback to conservative defaults
        return {
            "total_companies": 0,
            "total_embeddings": 0,
            "data_sources": 2,
            "error": str(e)
        }

@app.post("/search", response_model=SearchResponse, dependencies=[Depends(require_api_key), Depends(rate_limit)])
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
            graph_depth=2,
            min_repo_stars=request.min_stars,
            person_role_filters=request.person_roles
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search", response_model=SearchResponse, dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def search_get(
    query: str = Query(..., description="Search query"),
    top_k: int = Query(10, description="Number of results to return"),
    filter_type: Optional[str] = Query(None, description="Filter by entity type"),
    filter_source: Optional[str] = Query(None, description="Filter by data source"),
    min_stars: Optional[int] = Query(None, description="Minimum stars for repositories"),
    person_roles: Optional[str] = Query(None, description="Comma-separated person roles to include (e.g., founder,investor)")
):
    """
    Search endpoint for GET requests
    """
    try:
        role_list = None
        if person_roles:
            role_list = [r.strip().lower() for r in person_roles.split(',') if r.strip()]
        result = graph_rag_service.search(
            query=query,
            top_k=top_k,
            filter_type=filter_type,
            graph_depth=2,
            min_repo_stars=min_stars,
            person_role_filters=role_list
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/similar/{entity_id}", dependencies=[Depends(require_api_key), Depends(rate_limit)])
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

@app.get("/network/{entity_id}", dependencies=[Depends(require_api_key), Depends(rate_limit)])
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

# Removed test endpoints - use main /search endpoint for testing


@app.get("/stats")
async def get_stats():
    """
    Get comprehensive statistics about the database
    Includes company count, embeddings, and graph metrics
    """
    try:
        with graph_rag_service.neo4j_store.driver.session() as session:
            # Get company count
            result = session.run("MATCH (c:Company) RETURN count(c) as count")
            company_count = result.single()["count"]
            
            # Get embeddings count
            result_emb = session.run("MATCH (n) WHERE n.embedding IS NOT NULL RETURN count(n) as count")
            embeddings_count = result_emb.single()["count"]
            
        # Get detailed stats from Neo4j
        stats = graph_rag_service.neo4j_store.get_statistics()
        
        return {
            "total_companies": company_count,
            "total_embeddings": embeddings_count,
            "data_sources": 6,
            "total_nodes": stats['total_nodes'],
            "total_relationships": stats['total_relationships'],
            "nodes_by_type": {
                "companies": stats.get('company_count', 0),
                "people": stats.get('person_count', 0),
                "repositories": stats.get('repository_count', 0),
                "products": stats.get('product_count', 0)
            }
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
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 
