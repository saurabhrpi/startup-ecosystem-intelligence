"""Configuration for different data sources"""

from typing import Dict, Any, List
import os

class DataSourceConfig:
    """Configuration for various data sources"""
    
    # YC Data Sources
    YC_SOURCES = {
        'algolia': {
            'enabled': False,  # Disabled due to API key issues
            'app_id': '45BWZJ1SGC',
            'index': 'YCCompany_production',
            'description': 'YC Algolia search API'
        },
        'web_scraping': {
            'enabled': True,
            'url': 'https://www.ycombinator.com/companies',
            'description': 'Direct web scraping of YC companies page'
        },
        'sample_data': {
            'enabled': True,
            'files': ['yc_companies_large.json', 'yc_companies.json'],
            'description': 'Local sample data for testing'
        }
    }
    
    # GitHub Data Sources
    GITHUB_SOURCES = {
        'api': {
            'enabled': True,
            'requires_token': True,
            'base_url': 'https://api.github.com',
            'description': 'GitHub REST API'
        },
        'sample_data': {
            'enabled': True,
            'files': ['github_repos.json'],
            'description': 'Local sample data for testing'
        }
    }
    
    # Alternative Data Sources (for future implementation)
    ALTERNATIVE_SOURCES = {
        'crunchbase': {
            'enabled': False,
            'requires_api_key': True,
            'description': 'Crunchbase API for startup data'
        },
        'angellist': {
            'enabled': False,
            'requires_api_key': True,
            'description': 'AngelList API for startup data'
        },
        'product_hunt': {
            'enabled': False,
            'requires_api_key': True,
            'description': 'Product Hunt API for new products'
        },
        'hacker_news': {
            'enabled': True,
            'api_url': 'https://hacker-news.firebaseio.com/v0',
            'description': 'Hacker News API for tech news and Show HN posts'
        }
    }
    
    @classmethod
    def get_active_sources(cls) -> Dict[str, List[str]]:
        """Get all active data sources"""
        active = {
            'yc': [k for k, v in cls.YC_SOURCES.items() if v.get('enabled', False)],
            'github': [k for k, v in cls.GITHUB_SOURCES.items() if v.get('enabled', False)],
            'alternative': [k for k, v in cls.ALTERNATIVE_SOURCES.items() if v.get('enabled', False)]
        }
        return active
    
    @classmethod
    def get_sample_data_path(cls, filename: str) -> str:
        """Get the full path to a sample data file"""
        return os.path.join('data', 'samples', filename)