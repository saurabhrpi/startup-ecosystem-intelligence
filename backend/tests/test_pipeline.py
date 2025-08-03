import pytest
import asyncio
from backend.pipeline import DataPipeline
from backend.utils.vector_store import VectorStore

@pytest.mark.asyncio
async def test_data_collection():
    """Test that we can collect data from at least one source"""
    pipeline = DataPipeline()
    data = await pipeline.collect_all_data()
    
    # Check that we have at least some data
    total_items = sum(len(items) for items in data.values())
    assert total_items > 0, "No data collected from any source"
    
    # Check data structure
    for data_type, items in data.items():
        if items:
            assert isinstance(items, list)
            assert all(isinstance(item, dict) for item in items)

def test_embedding_generation():
    """Test embedding generation"""
    from backend.utils.embeddings import EmbeddingGenerator
    
    generator = EmbeddingGenerator()
    
    # Test with sample data
    sample_company = {
        'name': 'Test Startup',
        'description': 'A test startup for testing',
        'industries': ['AI', 'SaaS'],
        'source': 'test'
    }
    
    embeddings = generator.generate_embeddings([sample_company], 'company')
    
    assert len(embeddings) == 1
    assert 'embedding' in embeddings[0]
    assert len(embeddings[0]['embedding']) == 1536  # OpenAI embedding dimension
    assert embeddings[0]['metadata']['type'] == 'company'

def test_vector_store_connection():
    """Test connection to vector store"""
    try:
        store = VectorStore()
        assert store.index is not None
        print("✅ Vector store connection successful")
    except Exception as e:
        pytest.fail(f"Failed to connect to vector store: {e}")

# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])