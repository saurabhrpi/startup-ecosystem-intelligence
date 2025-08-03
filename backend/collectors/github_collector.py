import httpx
from typing import List, Dict, Any
from backend.config import settings
import json

class GitHubCollector:
    def __init__(self):
        self.api_url = "https://api.github.com"
        self.headers = {
            'Authorization': f'token {settings.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
    async def fetch_startup_repos(self, queries: List[str] = None) -> List[Dict[str, Any]]:
        """Fetch repositories from startup-related searches"""
        if queries is None:
            queries = [
                "startup",
                "saas boilerplate",
                "mvp template",
                "YC W24", "YC S23",  # YC batches
                "launched on producthunt"
            ]
        
        print("🚀 Fetching GitHub repositories...")
        repos = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for query in queries:
                results = await self._search_repos(client, query)
                repos.extend(results)
                
        # Deduplicate
        unique_repos = {repo['id']: repo for repo in repos}
        repos = list(unique_repos.values())
        
        print(f"✅ Fetched {len(repos)} unique GitHub repositories")
        return repos
    
    async def _search_repos(self, client: httpx.AsyncClient, query: str) -> List[Dict[str, Any]]:
        """Search GitHub repositories"""
        search_url = f"{self.api_url}/search/repositories"
        params = {
            'q': f"{query} stars:>10",
            'sort': 'stars',
            'order': 'desc',
            'per_page': 100
        }
        
        try:
            response = await client.get(search_url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return [self._transform_repo(repo) for repo in data['items']]
            else:
                print(f"Error searching GitHub: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"Error fetching GitHub data: {e}")
            return []
    
    def _transform_repo(self, repo: Dict) -> Dict[str, Any]:
        """Transform GitHub repo data to our schema"""
        return {
            'source': 'github',
            'id': f"gh_{repo['id']}",
            'name': repo['name'],
            'full_name': repo['full_name'],
            'description': repo['description'],
            'url': repo['html_url'],
            'homepage': repo['homepage'],
            'stars': repo['stargazers_count'],
            'forks': repo['forks_count'],
            'language': repo['language'],
            'topics': repo.get('topics', []),
            'created_at': repo['created_at'],
            'updated_at': repo['updated_at'],
            'owner': {
                'login': repo['owner']['login'],
                'type': repo['owner']['type'],
                'url': repo['owner']['html_url']
            }
        }
    
    def save_raw_data(self, repos: List[Dict[str, Any]]):
        """Save raw data for backup"""
        with open('data/raw/github_repos.json', 'w') as f:
            json.dump(repos, f, indent=2)
        print(f"💾 Saved {len(repos)} GitHub repos to data/raw/")