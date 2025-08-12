import httpx
import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple
from backend.config import settings
import json
from datetime import datetime, timedelta

class GitHubCollector:
    def __init__(self):
        self.api_url = "https://api.github.com"
        # Store token for external checks
        self.token = settings.github_token
        self.headers = {
            'Authorization': f'token {settings.github_token}' if settings.github_token else '',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'startup-ecosystem-intelligence'
        }
        # Rate limit tracking
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = time.time()
        # Cache for org lookups (org_name -> exists)
        self.org_cache = {}
        
    async def fetch_all_company_repos(self, companies: List[Dict[str, Any]], max_companies: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch GitHub repositories for all companies using company-first approach.
        Returns all discovered repos with confidence scores.
        """
        if not (self.token and isinstance(self.token, str) and self.token.strip()):
            raise RuntimeError("GITHUB_TOKEN is required for GitHub API calls. Set env var GITHUB_TOKEN and re-run.")
        
        print("🚀 Starting company-first GitHub repository discovery...")
        all_repos = []
        repo_company_map = []  # Track (repo_id, company_id, confidence, method)
        
        # Limit companies if specified
        companies_to_process = companies[:max_companies] if max_companies else companies
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for idx, company in enumerate(companies_to_process):
                if idx > 0 and idx % 10 == 0:
                    print(f"  Progress: {idx}/{len(companies_to_process)} companies processed")
                    # Rate limit pause every 10 companies
                    await self._check_rate_limit(client)
                
                company_repos = await self._discover_company_repos(client, company)
                
                # Add repos with relationship metadata
                for repo, confidence, method in company_repos:
                    all_repos.append(repo)
                    repo_company_map.append({
                        'repo_id': repo['id'],
                        'company_id': self._generate_company_id(company),
                        'confidence': confidence,
                        'method': method
                    })
        
        # Deduplicate repos while keeping the highest confidence mapping
        unique_repos = {}
        repo_mappings = {}
        
        for repo in all_repos:
            repo_id = repo['id']
            if repo_id not in unique_repos:
                unique_repos[repo_id] = repo
        
        for mapping in repo_company_map:
            key = (mapping['repo_id'], mapping['company_id'])
            if key not in repo_mappings or mapping['confidence'] > repo_mappings[key]['confidence']:
                repo_mappings[key] = mapping
        
        print(f"✅ Discovered {len(unique_repos)} unique repositories from {len(companies_to_process)} companies")
        
        # Store the mappings for later use in relationship creation
        self.repo_company_mappings = list(repo_mappings.values())
        
        return list(unique_repos.values())
    
    async def fetch_startup_repos(self, queries: List[str] = None) -> List[Dict[str, Any]]:
        """Legacy method - kept for compatibility but now returns empty list since we use company-first approach"""
        print("⚠️ fetch_startup_repos is deprecated. Using company-first approach instead.")
        return []
    
    async def _search_repos(self, client: httpx.AsyncClient, query: str) -> List[Dict[str, Any]]:
        """Search GitHub repositories"""
        search_url = f"{self.api_url}/search/repositories"
        # Avoid duplicating stars filter if already present in query
        q_has_stars = 'stars:' in (query or '')
        params = {
            'q': f"{query}" if q_has_stars else f"{query} stars:>10",
            'sort': 'stars',
            'order': 'desc',
            'per_page': 100
        }
        
        response = await self._get_with_rate_limit(client, search_url, params)
        data = response.json()
        return [self._transform_repo(repo) for repo in data.get('items', [])]

    async def _discover_company_repos(self, client: httpx.AsyncClient, company: Dict[str, Any]) -> List[Tuple[Dict[str, Any], float, str]]:
        """
        Discover repositories for a company using multiple methods.
        Returns list of (repo, confidence_score, method) tuples.
        """
        discovered_repos = []
        company_name = company.get('name', '')
        company_website = company.get('website', '')
        
        if not company_name:
            return []
        
        # Method 1: Direct GitHub Organization Search (highest confidence)
        org_repos = await self._search_by_organization(client, company_name)
        for repo in org_repos:
            discovered_repos.append((repo, 1.0, 'direct_org'))
        
        # Method 2: Website-to-GitHub Mapping
        if company_website:
            domain = self._extract_domain(company_website)
            if domain:
                domain_repos = await self._search_by_homepage_domain(client, domain)
                for repo in domain_repos:
                    discovered_repos.append((repo, 0.95, 'homepage_domain'))
        
        return discovered_repos
    
    async def _search_by_organization(self, client: httpx.AsyncClient, company_name: str) -> List[Dict[str, Any]]:
        """Search for GitHub organization and get its repos"""
        repos = []
        
        # Generate org name variants
        org_variants = self._generate_org_variants(company_name)
        
        for org_name in org_variants:
            # Check cache first
            if org_name in self.org_cache:
                if not self.org_cache[org_name]:
                    continue
            
            try:
                # Try to get org directly
                org_url = f"{self.api_url}/orgs/{org_name}"
                response = await client.get(org_url, headers=self.headers)
                
                if response.status_code == 200:
                    # Org exists, get its repos
                    self.org_cache[org_name] = True
                    repos_url = f"{self.api_url}/orgs/{org_name}/repos"
                    params = {'per_page': 100, 'sort': 'updated', 'type': 'sources'}
                    
                    repos_response = await self._get_with_rate_limit(client, repos_url, params)
                    if repos_response.status_code == 200:
                        org_repos = [self._transform_repo(r) for r in repos_response.json()]
                        repos.extend(org_repos)
                        break  # Found the org, no need to try other variants
                else:
                    self.org_cache[org_name] = False
                    
            except Exception:
                self.org_cache[org_name] = False
                continue
        
        return repos
    
    async def _search_by_homepage_domain(self, client: httpx.AsyncClient, domain: str) -> List[Dict[str, Any]]:
        """Search repos by homepage domain"""
        # GitHub search supports in:homepage
        query = f'"{domain}" in:homepage'
        return await self._search_repos(client, query)
    
    def _generate_org_variants(self, company_name: str) -> List[str]:
        """Generate possible GitHub org name variants"""
        base = company_name.lower().strip()
        variants = [
            base.replace(' ', ''),      # stripe
            base.replace(' ', '-'),      # stripe-inc
            base.replace(' ', '_'),      # stripe_inc
            base + 'hq',                 # stripehq
            base.replace(' ', '') + 'hq',
            base + '-inc',               # stripe-inc
            base.replace(' ', '') + 'inc',
            base + 'labs',               # stripelabs
            base.replace(' ', '') + 'labs',
        ]
        # Remove duplicates while preserving order
        seen = set()
        unique_variants = []
        for v in variants:
            if v not in seen:
                seen.add(v)
                unique_variants.append(v)
        return unique_variants[:5]  # Limit to top 5 variants
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        from urllib.parse import urlparse
        try:
            if not url:
                return ''
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception:
            return ''
    
    def _generate_company_id(self, company: Dict[str, Any]) -> str:
        """Generate consistent company ID"""
        import hashlib
        if 'id' in company:
            return str(company['id'])
        content = f"company_{company.get('name', '')}_{company.get('source', 'yc')}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def _check_rate_limit(self, client: httpx.AsyncClient):
        """Check and handle GitHub rate limits proactively"""
        if self.rate_limit_remaining < 100:
            # Check actual rate limit status
            rate_url = f"{self.api_url}/rate_limit"
            response = await client.get(rate_url, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                core = data.get('resources', {}).get('core', {})
                self.rate_limit_remaining = core.get('remaining', 0)
                self.rate_limit_reset = core.get('reset', time.time())
                
                if self.rate_limit_remaining < 50:
                    wait_time = max(self.rate_limit_reset - time.time(), 0) + 1
                    print(f"⏳ Approaching rate limit. Waiting {wait_time:.0f}s...")
                    await asyncio.sleep(wait_time)
    
    async def _get_with_rate_limit(self, client: httpx.AsyncClient, url: str, params: Dict[str, Any] | None = None) -> httpx.Response:
        """GET with simple GitHub rate-limit handling. Retries after reset when necessary."""
        max_attempts = 3
        for attempt in range(max_attempts):
            response = await client.get(url, headers=self.headers, params=params)
            # Success
            if response.status_code == 200:
                return response
            # Unauthorized
            if response.status_code == 401:
                raise RuntimeError("GitHub API 401 Unauthorized. Verify GITHUB_TOKEN is valid and has necessary scopes.")
            # Rate limit exceeded
            body_text = ''
            try:
                body_text = response.text or ''
            except Exception:
                body_text = ''
            if response.status_code == 403 and 'rate limit' in body_text.lower():
                reset_header = response.headers.get('X-RateLimit-Reset') or '0'
                try:
                    reset_ts = int(reset_header)
                except ValueError:
                    reset_ts = 0
                sleep_seconds = max(int(reset_ts - time.time()) + 1, 60)
                if attempt < max_attempts - 1:
                    print(f"GitHub rate limit exceeded. Waiting ~{sleep_seconds}s for reset... (attempt {attempt+1}/{max_attempts})")
                    await asyncio.sleep(sleep_seconds)
                    continue
                raise RuntimeError(f"GitHub rate limit exceeded and retries exhausted. Try later. Last response: {body_text[:200]}")
            # Other errors
            raise RuntimeError(f"GitHub API error {response.status_code}: {body_text[:200]}")
    
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
    
    async def fetch_company_repos(self, name: str, domains: List[str] = None) -> List[Dict[str, Any]]:
        """Discover repos likely owned by a specific company using name/org/domain cues."""
        if not name:
            return []
        domains = domains or []
        repos: List[Dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                # 1) Search by name in name/description/readme
                name_query = f"{name} in:name,description,readme stars:>0"
                repos += await self._search_repos(client, name_query)

                # 2) Search by domains appearing in readme/description/topics
                for d in domains:
                    if not d:
                        continue
                    domain_query = f'"{d}" in:readme,description,topics stars:>0'
                    repos += await self._search_repos(client, domain_query)

                # 3) Try to find an organization by slug and list its repos
                slug_variants = set()
                base = name.lower().strip()
                slug_variants.add(base.replace(' ', ''))
                slug_variants.add(base.replace(' ', '-'))

                # Search users (orgs)
                for slug in slug_variants:
                    search_users_url = f"{self.api_url}/search/users"
                    resp = await client.get(search_users_url, headers=self.headers, params={'q': f'{slug} type:org', 'per_page': 3})
                    if resp.status_code == 200 and resp.json().get('items'):
                        org_login = resp.json()['items'][0]['login']
                        # List org repos
                        org_repos_url = f"{self.api_url}/orgs/{org_login}/repos"
                        r = await client.get(org_repos_url, headers=self.headers, params={'per_page': 100, 'sort': 'updated'})
                        if r.status_code == 200:
                            repos.extend([self._transform_repo(rr) for rr in r.json()])
                        break
        except Exception as e:
            print(f"Error in fetch_company_repos: {e}")
        # Deduplicate
        return list({repo['id']: repo for repo in repos}.values())
    
    def save_raw_data(self, repos: List[Dict[str, Any]]):
        """Save raw data for backup"""
        with open('data/raw/github_repos.json', 'w') as f:
            json.dump(repos, f, indent=2)
        print(f"💾 Saved {len(repos)} GitHub repos to data/raw/")