import openai
from typing import List, Dict, Any, Optional
import tiktoken
from tqdm import tqdm
import json
import hashlib
from backend.config import settings

class EmbeddingGenerator:
    def __init__(self):
        openai.api_key = settings.openai_api_key
        self.model = settings.embedding_model
        self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        
    def generate_embeddings(self, data: List[Dict[str, Any]], data_type: str) -> List[Dict[str, Any]]:
        """Generate embeddings for a list of items"""
        print(f"Generating embeddings for {len(data)} {data_type} items...")
        
        embeddings = []
        
        for item in tqdm(data, desc=f"Embedding {data_type}"):
            # Create text representation based on data type
            if data_type == 'company':
                text = self._create_company_text(item)
            elif data_type == 'product':
                text = self._create_product_text(item)
            elif data_type == 'person':
                text = self._create_person_text(item)
            elif data_type == 'filing':
                text = self._create_filing_text(item)
            elif data_type == 'repo':
                text = self._create_repo_text(item)
            else:
                text = json.dumps(item)
            
            # Generate embedding
            embedding = self._get_embedding(text)
            
            if embedding:
                embeddings.append({
                    'id': self._generate_id(item, data_type),
                    'embedding': embedding,
                    'metadata': {
                        'type': data_type,
                        'source': item.get('source', 'unknown'),
                        'name': item.get('name', 'Unknown'),
                        'text': text[:500],  # Store first 500 chars
                        **self._extract_metadata(item, data_type)
                    }
                })
        
        print(f"Generated {len(embeddings)} embeddings")
        return embeddings
    
    def _create_company_text(self, company: Dict) -> str:
        """Create text representation of a company"""
        parts = [
            f"Company: {company.get('name', '')}",
            f"Description: {company.get('description', '')}",
            f"Industries: {', '.join(company.get('industries', []))}",
            f"Location: {company.get('location', '')}",
            f"Batch: {company.get('batch', '')}",
        ]
        
        if 'founders' in company:
            if isinstance(company['founders'], list) and len(company['founders']) > 0:
                if isinstance(company['founders'][0], dict):
                    founder_names = [f.get('name', '') for f in company['founders']]
                else:
                    founder_names = company['founders']
                parts.append(f"Founders: {', '.join(founder_names)}")
        
        return '\n'.join(filter(None, parts))
    
    def _create_product_text(self, product: Dict) -> str:
        """Create text representation of a product"""
        parts = [
            f"Product: {product.get('name', '')}",
            f"Tagline: {product.get('tagline', '')}",
            f"Description: {product.get('description', '')}",
            f"Topics: {', '.join(product.get('topics', []))}",
        ]
        
        if 'makers' in product and product['makers']:
            maker_names = [m.get('name', '') for m in product['makers']]
            parts.append(f"Makers: {', '.join(maker_names)}")
        
        return '\n'.join(filter(None, parts))
    
    def _create_person_text(self, person: Dict) -> str:
        """Create text representation of a person"""
        parts = [
            f"Name: {person.get('name', '')}",
            f"Headline: {person.get('headline', '')}",
            f"Role: {person.get('role', '')}",
            f"Company: {person.get('company', '')}",
        ]
        return '\n'.join(filter(None, parts))
    
    def _create_filing_text(self, filing: Dict) -> str:
        """Create text representation of a filing"""
        return f"Company: {filing.get('company_name', '')}\nFiling: {filing.get('filing_type', '')}\nDescription: {filing.get('description', '')}"
    
    def _create_repo_text(self, repo: Dict) -> str:
        """Create text representation of a repo"""
        parts = [
            f"Repository: {repo.get('name', '')}",
            f"Description: {repo.get('description', '')}",
            f"Language: {repo.get('language', '')}",
            f"Topics: {', '.join(repo.get('topics', []))}",
            f"Stars: {repo.get('stars', 0)}",
            f"Owner: {repo.get('owner', {}).get('login', '')}",
        ]
        return '\n'.join(filter(None, parts))
    
    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding from OpenAI"""
        try:
            # Truncate if too long
            tokens = self.encoding.encode(text)
            if len(tokens) > 8000:
                text = self.encoding.decode(tokens[:8000])
            
            response = openai.embeddings.create(
                model=self.model,
                input=text
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None
    
    def _generate_id(self, item: Dict, data_type: str) -> str:
        """Generate unique ID for an item"""
        if 'id' in item:
            return str(item['id'])
        
        # Generate ID from content
        content = f"{data_type}_{item.get('name', '')}_{item.get('source', '')}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _extract_metadata(self, item: Dict, data_type: str) -> Dict:
        """Extract relevant metadata"""
        metadata = {}
        
        if data_type == 'company':
            metadata['industries'] = item.get('industries', [])
            metadata['location'] = item.get('location', '')
            metadata['website'] = item.get('website', '')
            metadata['batch'] = item.get('batch', '')
            
        elif data_type == 'product':
            metadata['votes'] = item.get('votes_count', 0)
            metadata['website'] = item.get('website', '')
            metadata['topics'] = item.get('topics', [])
            
        elif data_type == 'repo':
            metadata['stars'] = item.get('stars', 0)
            metadata['language'] = item.get('language', '')
            metadata['owner'] = item.get('owner', {}).get('login', '')
            
        return metadata