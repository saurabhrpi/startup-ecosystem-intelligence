from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Required API Keys
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    pinecone_api_key: str = os.getenv("PINECONE_API_KEY", "")
    
    # Optional API Keys
    github_token: Optional[str] = os.getenv("GITHUB_TOKEN")
    producthunt_api_key: Optional[str] = os.getenv("PRODUCTHUNT_API_KEY")
    news_api_key: Optional[str] = os.getenv("NEWS_API_KEY")
    
    # Pinecone (Required)
    pinecone_environment: str = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")
    pinecone_index_name: str = os.getenv("PINECONE_INDEX_NAME", "startup-embeddings")
    
    # Databases (Optional for Week 1)
    postgres_url: Optional[str] = os.getenv("POSTGRES_URL")
    redis_url: Optional[str] = os.getenv("REDIS_URL")
    neo4j_uri: Optional[str] = os.getenv("NEO4J_URI")
    neo4j_user: Optional[str] = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: Optional[str] = os.getenv("NEO4J_PASSWORD", "password")
    
    # Embeddings
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # API security
    api_key: Optional[str] = os.getenv("API_KEY")
    rate_limit_rpm: int = int(os.getenv("RATE_LIMIT_RPM", "60"))
    
    class Config:
        env_file = ".env"

settings = Settings()