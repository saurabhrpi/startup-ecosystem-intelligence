import httpx
import json
from typing import List, Dict, Any
import asyncio
from datetime import datetime

class YCCompaniesScraper:
    def __init__(self):
        self.base_url = "https://www.ycombinator.com"
        self.meta_url = "https://yc-oss.github.io/api/meta.json"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        
    async def fetch_all_companies(self) -> List[Dict[str, Any]]:
        """Fetch all YC companies from the yc-oss API"""
        print("Fetching YC companies from yc-oss API...")
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            try:
                # First, fetch the metadata to get the API endpoints
                meta_response = await client.get(self.meta_url, headers=self.headers)
                
                if meta_response.status_code != 200:
                    print(f"Error fetching metadata: Status {meta_response.status_code}")
                    return []
                
                meta_data = meta_response.json()
                
                # Get the URL for all companies
                companies_endpoints = meta_data.get('companies', {})
                all_companies_info = companies_endpoints.get('all', {})
                companies_url = all_companies_info.get('api')
                
                if not companies_url:
                    print("Could not find companies API URL in metadata")
                    return []
                
                print(f"Fetching companies from: {companies_url}")
                
                # Fetch the actual companies data
                companies_response = await client.get(companies_url, headers=self.headers)
                
                if companies_response.status_code != 200:
                    print(f"Error fetching companies: Status {companies_response.status_code}")
                    return []
                
                companies = companies_response.json()
                
                if companies:
                    print(f"Found {len(companies)} YC companies")
                    # Normalize the data to our format
                    normalized_companies = []
                    for company in companies:
                        normalized = self._normalize_company_data(company)
                        if normalized:
                            normalized_companies.append(normalized)
                    
                    return normalized_companies
                else:
                    print("No companies found in the API response")
                    return []
                
            except Exception as e:
                print(f"Error fetching companies: {e}")
                return []
    
    def _normalize_company_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize company data from yc-oss API to our standard format"""
        try:
            # Extract batch year and season
            batch = data.get('batch', '')
            batch_parts = batch.split(' ') if batch else ['', '']
            batch_season = batch_parts[0] if len(batch_parts) > 0 else ''
            batch_year = batch_parts[1] if len(batch_parts) > 1 else ''
            
            # Extract location parts
            location = data.get('all_locations', '')
            location_parts = [loc.strip() for loc in location.split(',') if loc.strip()]
            
            company = {
                'source': 'yc',
                'id': str(data.get('id', '')),
                'name': data.get('name', ''),
                'slug': data.get('slug', ''),
                'description': data.get('one_liner', ''),
                'long_description': data.get('long_description', ''),
                'batch': batch,
                'website': data.get('website', ''),
                'location': location,
                'industries': data.get('industries', []),
                'tags': data.get('tags', []),
                'status': data.get('status', 'active'),
                'founded': data.get('launched_at'),  # Unix timestamp
                'team_size': data.get('team_size', 0),
                'yc_url': data.get('url', ''),
                'logo_url': data.get('small_logo_thumb_url', ''),
                'top_company': data.get('top_company', False),
                'is_hiring': data.get('isHiring', False),
                'nonprofit': data.get('nonprofit', False),
                'batch_season': batch_season,
                'batch_year': batch_year,
                'stage': data.get('stage', ''),
                'subindustry': data.get('subindustry', ''),
                'regions': data.get('regions', []),
                'former_names': data.get('former_names', []),
                'scraped_at': datetime.now().isoformat()
            }
            
            # No founders data in this API, but we'll keep the field empty
            company['founders'] = []
            
            # Only return if we have at least a name
            if company['name']:
                return company
            
        except Exception as e:
            print(f"Error normalizing company data: {e}")
        
        return None
    
    def save_raw_data(self, companies: List[Dict[str, Any]]):
        """Save raw data for backup"""
        import os
        os.makedirs('data/raw', exist_ok=True)
        
        filename = f'data/raw/yc_companies_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(companies, f, indent=2, ensure_ascii=False)
        
        # Also save to the standard location
        with open('data/raw/yc_companies.json', 'w', encoding='utf-8') as f:
            json.dump(companies, f, indent=2, ensure_ascii=False)
            
        print(f"Saved {len(companies)} YC companies to data/raw/")

# Test the scraper
async def test_yc_scraper():
    scraper = YCCompaniesScraper()
    companies = await scraper.fetch_all_companies()
    
    if companies:
        print(f"\nSample company: {json.dumps(companies[0], indent=2)}")
        scraper.save_raw_data(companies)
        print(f"\nSuccessfully fetched {len(companies)} YC companies!")
    else:
        print("\nNo companies found.")
        print("The API might be temporarily unavailable.")
    
    return companies

if __name__ == "__main__":
    asyncio.run(test_yc_scraper())