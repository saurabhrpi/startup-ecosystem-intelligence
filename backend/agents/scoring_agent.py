"""
Scoring Agent - Evaluates and scores companies based on multiple factors
"""
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from backend.utils.neo4j_store import Neo4jStore
import openai
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScoringAgent:
    """
    Intelligent agent that scores companies based on:
    - Founder quality
    - Market timing
    - Network strength
    - Technical indicators
    - Growth signals
    """
    
    def __init__(self):
        self.neo4j_store = Neo4jStore()
        openai.api_key = os.getenv('OPENAI_API_KEY')
        self.openai_client = openai
        
        # Scoring weights (configurable)
        self.weights = {
            'founder_score': 0.25,
            'network_score': 0.20,
            'market_score': 0.20,
            'technical_score': 0.20,
            'timing_score': 0.15
        }
    
    async def score_company(self, company_id: str) -> Dict[str, Any]:
        """
        Comprehensive scoring of a single company
        """
        # Get company data from Neo4j
        company_data = self._get_company_data(company_id)
        if not company_data:
            return {'error': 'Company not found'}
        
        # Calculate individual scores
        scores = {
            'founder_score': await self._score_founders(company_data),
            'network_score': self._score_network(company_data),
            'market_score': await self._score_market(company_data),
            'technical_score': self._score_technical(company_data),
            'timing_score': self._score_timing(company_data)
        }
        
        # Calculate weighted total score
        # Compute weighted total over available factors only (exclude N/A)
        available_factors = [(name, score) for name, score in scores.items() if isinstance(score, (int, float))]
        if available_factors:
            weight_sum = sum(self.weights[name] for name, _ in available_factors)
            weighted_sum = sum(score * self.weights[name] for name, score in available_factors)
            total_score = weighted_sum / weight_sum
        else:
            total_score = None
        
        # Persist last total score for thesis formatting
        self._last_total_score = total_score  # may be None
        # Generate investment thesis
        thesis = await self._generate_investment_thesis(company_data, scores)
        
        return {
            'company_id': company_id,
            'company_name': company_data['name'],
            'total_score': round(total_score, 2) if isinstance(total_score, (int, float)) else None,
            'scores': scores,
            'investment_thesis': thesis,
            'scoring_date': datetime.now().isoformat()
        }
    
    async def score_multiple_companies(self, company_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Score multiple companies and rank them
        """
        scored_companies = []
        
        for company_id in company_ids:
            score_result = await self.score_company(company_id)
            if 'error' not in score_result:
                scored_companies.append(score_result)
        
        # Sort by total score
        scored_companies.sort(key=lambda x: x['total_score'], reverse=True)
        
        # Add ranking
        for i, company in enumerate(scored_companies):
            company['rank'] = i + 1
        
        return scored_companies
    
    def _get_company_data(self, company_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch comprehensive company data from Neo4j
        """
        with self.neo4j_store.driver.session() as session:
            query = """
            MATCH (c:Company {id: $company_id})
            OPTIONAL MATCH (c)<-[:FOUNDED]-(founder:Person)
            WITH c, collect(DISTINCT founder) AS founders
            OPTIONAL MATCH (c)-[:IN_BATCH]->(b)<-[:IN_BATCH]-(batch_peer:Company)
            WHERE batch_peer.id <> c.id
            WITH c, founders, count(DISTINCT batch_peer) AS batch_peer_count
            OPTIONAL MATCH (c)-[:IN_INDUSTRY]->(i)<-[:IN_INDUSTRY]-(industry_peer:Company)
            WHERE industry_peer.id <> c.id
            WITH c, founders, batch_peer_count, count(DISTINCT industry_peer) AS industry_peer_count
            OPTIONAL MATCH (c)-[:OWNS|LIKELY_OWNS]->(repo:Repository)
            RETURN c,
                   founders,
                   batch_peer_count,
                   industry_peer_count,
                   collect(DISTINCT repo) as repositories
            """
            
            result = session.run(query, company_id=company_id)
            record = result.single()
            
            if not record:
                return None
            
            company = dict(record['c'])
            company['founders'] = [dict(f) for f in record['founders']]
            company['batch_peer_count'] = record['batch_peer_count']
            company['industry_peer_count'] = record['industry_peer_count']
            company['repositories'] = [dict(r) for r in record['repositories']]
            
            return company
    
    async def _score_founders(self, company_data: Dict[str, Any]) -> Optional[float]:
        """
        Score based on founder quality (0-10)
        Factors:
        - Previous experience
        - Educational background
        - Past successes
        """
        if not company_data.get('founders'):
            return None  # Not Available when no founder data
        
        # Use LLM to analyze founder quality
        founders_text = "\n".join([
            f"- {f.get('name', 'Unknown')}: {f.get('role', 'Founder')}"
            for f in company_data['founders']
        ])
        
        prompt = f"""
        Analyze the founder quality for this startup:
        Company: {company_data.get('name')}
        Founders:
        {founders_text}
        
        Score the founder quality from 0-10 based on:
        1. Team size and composition (2-3 founders is generally optimal)
        2. Role clarity (e.g., presence of CEO/CTO or clearly defined roles)
        3. Any prior leadership or domain-relevant signals if evident from roles
        
        Respond with ONLY a number between 0-10.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0
            )
            score = float(response.choices[0].message.content.strip())
            return min(max(score, 0), 10)  # Ensure 0-10 range
        except:
            return None  # Not Available on error
    
    def _score_network(self, company_data: Dict[str, Any]) -> float:
        """
        Score based on network strength (0-10)
        Factors:
        - Number of batch peers
        - Industry connections
        - Repository connections
        """
        # Define network purely as peer connectivity (batch / industry). Repositories are excluded.
        batch_score = min(company_data.get('batch_peer_count', 0) / 5, 1) * 5  # up to 5 points
        industry_score = min(company_data.get('industry_peer_count', 0) / 10, 1) * 5  # up to 5 points
        return batch_score + industry_score
    
    async def _score_market(self, company_data: Dict[str, Any]) -> float:
        """
        Score based on market opportunity (0-10)
        Analyzes industries and market timing
        """
        industries = company_data.get('industries', [])
        if not industries:
            return 5.0
        
        # Hot industries get higher scores
        hot_industries = {
            'AI': 9, 'Machine Learning': 9, 'Generative AI': 10,
            'Climate': 8, 'Fintech': 7, 'Healthcare': 7,
            'B2B': 6, 'SaaS': 7, 'Developer Tools': 8
        }
        
        # Calculate average score for company's industries
        scores = []
        for industry in industries:
            for hot_industry, score in hot_industries.items():
                if hot_industry.lower() in industry.lower():
                    scores.append(score)
                    break
            else:
                scores.append(5)  # Default score
        
        return sum(scores) / len(scores) if scores else 5.0
    
    def _score_technical(self, company_data: Dict[str, Any]) -> Optional[float]:
        """
        Score based on technical indicators (0-10)
        For companies with GitHub repos
        """
        repos = company_data.get('repositories', [])
        if not repos:
            return None  # Not Available when no repos
        
        # Average stars across repos
        total_stars = sum(r.get('stars', 0) for r in repos)
        
        # Score based on GitHub activity
        if total_stars >= 1000:
            return 10.0
        elif total_stars >= 100:
            return 8.0
        elif total_stars >= 10:
            return 6.0
        else:
            return 4.0
    
    def _score_timing(self, company_data: Dict[str, Any]) -> float:
        """
        Score based on timing factors (0-10)
        Batch recency, market timing
        """
        batch = company_data.get('batch', '')
        if not batch:
            return 5.0
        
        # Parse batch (e.g., "W23", "S22")
        try:
            if len(batch) >= 3:
                year = int('20' + batch[-2:])
                current_year = datetime.now().year
                years_old = current_year - year
                
                # Newer companies score higher (sweet spot: 1-3 years)
                if years_old <= 1:
                    return 9.0
                elif years_old <= 3:
                    return 8.0
                elif years_old <= 5:
                    return 6.0
                else:
                    return 4.0
        except:
            pass
        
        return 5.0
    
    async def _generate_investment_thesis(
        self, 
        company_data: Dict[str, Any], 
        scores: Dict[str, float]
    ) -> str:
        """
        Generate an investment thesis based on scores
        """
        def fmt(val: Optional[float]) -> str:
            return f"{val}/10" if isinstance(val, (int, float)) else "N/A"

        total_str = f"{self._last_total_score:.1f}/10" if isinstance(getattr(self, '_last_total_score', None), (int, float)) else "N/A"
        prompt = f"""
        Generate a concise investment thesis for:
        Company: {company_data.get('name')}
        Industries: {', '.join(company_data.get('industries', []))}
        
        Scores:
        - Founder Quality: {fmt(scores.get('founder_score'))}
        - Network Strength: {fmt(scores.get('network_score'))}
        - Market Opportunity: {fmt(scores.get('market_score'))}
        - Technical Indicators: {fmt(scores.get('technical_score'))}
        - Timing: {fmt(scores.get('timing_score'))}
        
        Total Score: {total_str}
        
        Provide a 2-3 sentence investment thesis highlighting the strongest factors
        and any concerns. Be specific and actionable.
        """
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a venture capital analyst providing concise investment recommendations."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    
    def get_scoring_methodology(self) -> Dict[str, Any]:
        """
        Return the scoring methodology for transparency
        """
        return {
            "factors": {
                "founder_score": {
                    "weight": self.weights['founder_score'],
                    "description": "Evaluates team size/composition (2–3 optimal) and role clarity (e.g., CEO/CTO). Returns N/A if founder data is missing."
                },
                "network_score": {
                    "weight": self.weights['network_score'],
                    "description": "Measures peer connectivity: up to 5 points from SAME_BATCH peers (cap at 5), and up to 5 points from SAME_INDUSTRY peers (cap at 10). Repositories are excluded."
                },
                "market_score": {
                    "weight": self.weights['market_score'],
                    "description": "Assesses market opportunity and industry trends"
                },
                "technical_score": {
                    "weight": self.weights['technical_score'],
                    "description": "Analyzes GitHub indicators (total stars thresholds). Returns N/A if no repos."
                },
                "timing_score": {
                    "weight": self.weights['timing_score'],
                    "description": "Evaluates market timing and company maturity"
                }
            },
            "scale": "0-10 for each factor",
            "interpretation": {
                "8-10": "Exceptional investment opportunity",
                "6-8": "Strong potential, worth deeper analysis",
                "4-6": "Average opportunity, depends on thesis",
                "0-4": "Weak opportunity, significant concerns"
            }
        }