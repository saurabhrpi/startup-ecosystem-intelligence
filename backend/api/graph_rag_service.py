"""
Graph RAG Service V2 - Uses Neo4j for both vector search and graph relationships
"""
import os
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
import openai
from backend.utils.neo4j_store import Neo4jStore
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GraphRAGService:
    def __init__(self):
        # Initialize Neo4j store
        self.neo4j_store = Neo4jStore()
        
        # Initialize OpenAI
        openai.api_key = os.getenv('OPENAI_API_KEY')
        self.openai_client = openai
        
        # Location aliases are loaded dynamically at runtime from
        # 1) Neo4j Location nodes (if present), else
        # 2) LOCATION_ALIASES_JSON env var (JSON object), else
        # 3) empty map (no location filtering).
        self.location_aliases: Dict[str, List[str]] = self._load_location_aliases()
        # Known industries loaded lazily on first use
        self.known_industries: Optional[List[str]] = None
        # Industry aliases mapping canonical -> [aliases], loaded lazily
        self.industry_aliases: Optional[Dict[str, List[str]]] = None
    
    def _extract_numeric_filters(self, query: str) -> Tuple[Dict[str, int], str]:
        """
        Extract numeric filters from natural language query.
        Returns (filters_dict, cleaned_query)
        
        Examples:
        - "developer tools with >100 stars" -> ({'min_star': 100}, "developer tools")
        - "companies with >50 employees and <1000 stars" -> ({'min_employee': 50, 'max_star': 1000}, "companies")
        - "projects with more than 200 forks" -> ({'min_fork': 200}, "projects")
        """
        filters = {}
        cleaned_query = query
        
        # Define patterns for numeric comparisons
        # Each pattern captures: (comparison_phrase, number, metric)
        comparison_patterns = [
            # Symbolic operators
            (r'([><]=?)\s*(\d+)\s+(\w+)', lambda op, val, metric: ('min' if op in ['>', '>='] else 'max', val)),
            (r'(\d+)\+\s+(\w+)', lambda val, metric: ('min', val)),  # "100+ stars"
            
            # Natural language comparisons - captured as groups for operator detection
            (r'(more\s+than|greater\s+than|over|above)\s+(\d+)\s+(\w+)', lambda phrase, val, metric: ('min', val)),
            (r'(less\s+than|fewer\s+than|under|below)\s+(\d+)\s+(\w+)', lambda phrase, val, metric: ('max', val)),
            (r'(at\s+least|minimum\s+of?|no\s+less\s+than)\s+(\d+)\s+(\w+)', lambda phrase, val, metric: ('min', val)),
            (r'(at\s+most|maximum\s+of?|no\s+more\s+than)\s+(\d+)\s+(\w+)', lambda phrase, val, metric: ('max', val)),
        ]
        
        # Process all patterns
        all_matches = []
        for pattern, operator_func in comparison_patterns:
            for match in re.finditer(pattern, query, re.IGNORECASE):
                groups = match.groups()
                if len(groups) >= 2:
                    # Get the metric (last group) and value (second to last group)
                    metric = groups[-1].rstrip('s')  # Remove plural
                    value = int(groups[-2])
                    
                    # Determine min/max based on the operator/phrase
                    op_type, _ = operator_func(*groups)
                    filter_key = f'{op_type}_{metric}'
                    
                    all_matches.append((match.start(), match.end(), filter_key, value, match.group(0)))
        
        # Sort matches by position (to remove them in reverse order)
        all_matches.sort(key=lambda x: x[0], reverse=True)
        
        # Apply filters and remove matched text
        for start, end, filter_key, value, matched_text in all_matches:
            filters[filter_key] = value
            # Remove the matched portion from the query
            cleaned_query = cleaned_query[:start] + ' ' + cleaned_query[end:]
        
        # Only clean up extra whitespace, don't remove stopwords
        cleaned_query = ' '.join(cleaned_query.split())
        
        logger.info(f"Extracted numeric filters: {filters} from query: '{query}'")
        return filters, cleaned_query

    def _is_complex_query(self, q: str) -> bool:
        ql = (q or '').lower()
        score = 0
        # multi-entity mentions
        ents = sum(k in ql for k in ["founder","person","repo","repository","company","startup"])
        if ents >= 2: score += 2
        # boolean/combiner
        if re.search(r"\b(and|or|not|without|except|between)\b", ql): score += 2
        # comparators/aggregations
        if re.search(r"[<>]=?|\b(at least|at most|over|under|more than|less than|top \d+|best|most)\b", ql): score += 2
        # joins/relations
        if re.search(r"\b(who|that|which)\b", ql): score += 1
        # multiple filters: location + time/round
        if re.search(r"\b(in|near|from)\b", ql) and re.search(r"\b(20\d{2}|w\d{2}|s\d{2}|series [abc]|seed)\b", ql):
            score += 2
        # analytical verbs
        if re.search(r"\b(compare|rank|summarize|recommend|explain|why|how)\b", ql): score += 2
        # length
        if len(q.split()) > 12: score += 1
        return score >= 3

    def _plan_query(self, query: str) -> Dict[str, Any]:
        """Ask the LLM for a compact JSON execution plan. Fallback to heuristics on error."""
        try:
            prompt = (
                "You are a query planner. Read the user query and output a minimal JSON plan with fields: "
                "filter_type (one of: 'company','person','repository' or null), person_roles (array, e.g., ['founder']), "
                "min_repo_stars (int or null), location (string or null), query_focus (string to use for embedding). "
                "Only output JSON."
            )
            msg = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": query}
            ]
            resp = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=msg,
                temperature=0,
                max_tokens=200
            )
            content = resp.choices[0].message.content.strip()
            plan = json.loads(content)
            if isinstance(plan, dict):
                return plan
        except Exception:
            pass
        # heuristic fallback: founders, repositories, or companies
        ql = query.lower()
        plan: Dict[str, Any] = {}
        if any(k in ql for k in ["founder","founders","people","person","ceo","cto"]):
            plan["filter_type"] = "person"
            plan["person_roles"] = ["founder"]
        elif any(k in ql for k in ["repo","repository","github","code"]):
            plan["filter_type"] = "repository"
        else:
            plan["filter_type"] = "company"
        plan["query_focus"] = query
        return plan
    
    def _detect_entity_type(self, query: str) -> Optional[str]:
        """
        Detect what type of entity the user is searching for.
        Returns the detected filter_type or None.
        """
        query_lower = query.lower()
        
        # Repository/code related
        repo_terms = ['repository', 'repo', 'github', 'code', 'project', 'package',
                      'library', 'framework', 'sdk', 'cli', 'tool', 'toolkit', 
                      'utility', 'plugin', 'extension', 'module', 'api']
        
        # Company related
        company_terms = ['company', 'startup', 'business', 'firm', 'venture',
                        'enterprise', 'organization', 'corp']
        
        # Person related
        person_terms = ['founder', 'person', 'people', 'developer', 'engineer',
                       'ceo', 'cto', 'investor', 'employee', 'team']
        
        # Check for matches (prioritize more specific terms)
        if any(term in query_lower for term in repo_terms):
            return 'repository'
        elif any(term in query_lower for term in company_terms):
            return 'company'
        elif any(term in query_lower for term in person_terms):
            return 'person'
        
        return None
    
    def _derive_person_roles_from_query(self, query: str) -> Optional[List[str]]:
        """Infer person role filters directly from the free-text query.
        Returns a list like ['investor'] or ['founder'] when confidently detected, else None.
        """
        if not query:
            return None
        q = query.lower()
        # Investor-oriented terms
        investor_terms = [
            'investor', 'investors', 'vc', 'venture capital', 'venture-capital',
            'angel', 'lead investor', 'general partner', 'gp', 'partner', 'principal', 'associate'
        ]
        # Founder-oriented terms
        founder_terms = [
            'founder', 'founders', 'cofounder', 'co-founder', 'ceo', 'cto', 'cpo', 'head of'
        ]
        if any(t in q for t in investor_terms):
            return ['investor']
        if any(t in q for t in founder_terms):
            return ['founder']
        return None
    
    def search(
        self, 
        query: str, 
        top_k: int = 10,
        graph_depth: int = 2,
        filter_type: Optional[str] = None,
        min_score: float = 0.7,
        min_repo_stars: Optional[int] = None,
        person_role_filters: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Perform Graph RAG search using Neo4j's hybrid capabilities
        """
        used_planner = False
        # Extract numeric filters from query
        numeric_filters, cleaned_query = self._extract_numeric_filters(query)
        
        # Apply extracted star filter if not already specified
        if 'min_star' in numeric_filters and not min_repo_stars:
            min_repo_stars = numeric_filters['min_star']
        
        # Use cleaned query for embeddings to get better semantic matches
        embedding_query = cleaned_query if cleaned_query else query

        # Detect basic filters
        batch_filters = self._extract_batch_from_query(query)
        location_code = self._extract_location_from_query(query)
        industry_filters = self._extract_industries_from_query(query)
        if not filter_type:
            detected_type = self._detect_entity_type(query)
            if detected_type:
                filter_type = detected_type
                logger.info(f"Auto-detected entity type: {filter_type}")
        roles_from_query = self._derive_person_roles_from_query(query) if filter_type == 'person' and not person_role_filters else None
        if roles_from_query:
            person_role_filters = [r.lower() for r in roles_from_query]

        # General filter-only path: if filters present and no analytic terms
        ql = (query or '').lower()
        analytic_terms = ['why','how','explain','compare','similar','rank','best','top','most']
        is_analytic = any(t in ql for t in analytic_terms)
        has_filters = bool(batch_filters or location_code or industry_filters or person_role_filters or min_repo_stars)
        if has_filters and not is_analytic:
            # Expand industry filters with aliases (canonical + all aliases)
            expanded_industries = None
            if industry_filters:
                expanded: set[str] = set()
                if self.industry_aliases is None:
                    self.industry_aliases = self._load_industry_aliases()
                for canonical in industry_filters:
                    token = (canonical or '').strip().lower()
                    if not token:
                        continue
                    expanded.add(token)
                    for alias in (self.industry_aliases or {}).get(token, []) or []:
                        a = (alias or '').strip().lower()
                        if a:
                            expanded.add(a)
                expanded_industries = list(expanded) if expanded else None
            results = self.neo4j_store.filter_search(
                node_type=filter_type,
                batch_filters=batch_filters,
                location_filters=self._aliases_for_code(location_code) if location_code else None,
                industry_filters=expanded_industries,
                person_role_filters=person_role_filters,
                min_repo_stars=min_repo_stars,
            )
            response = self._generate_graph_aware_response(query, results)
            graph_data = self._build_visualization_data(results[:5])
            return {
                'query': query,
                'matches': results,
                'response': response,
                'graph': graph_data,
                'total_results': len(results),
                'search_params': {
                    'filter_only': True,
                    'filter_type': filter_type,
                    'applied_filters': {
                        'location': location_code,
                        'batch': batch_filters,
                        'min_repo_stars': min_repo_stars,
                        'person_roles': person_role_filters
                    }
                }
            }
        
        # Auto-detect entity type if not specified
        if not filter_type:
            detected_type = self._detect_entity_type(query)
            if detected_type:
                filter_type = detected_type
                logger.info(f"Auto-detected entity type: {filter_type}")
        
        # If searching for people but roles weren't provided, derive them from the query
        if (filter_type == 'person') and not person_role_filters:
            derived_roles = self._derive_person_roles_from_query(query)
            if derived_roles:
                person_role_filters = [r.lower() for r in derived_roles]
        
        # If complex, run planner to refine execution params
        if self._is_complex_query(query):
            plan = self._plan_query(query)
            used_planner = True
            if isinstance(plan.get("filter_type"), str):
                filter_type = plan["filter_type"]
            if isinstance(plan.get("person_roles"), list):
                person_role_filters = [r.lower() for r in plan["person_roles"] if isinstance(r, str)]
            if isinstance(plan.get("min_repo_stars"), int):
                min_repo_stars = plan["min_repo_stars"]
            if isinstance(plan.get("query_focus"), str) and plan["query_focus"].strip():
                embedding_query = plan["query_focus"].strip()
            # If planner didn't set roles for person queries, fall back to derivation
            if (filter_type == 'person') and not person_role_filters:
                derived_roles = self._derive_person_roles_from_query(query)
                if derived_roles:
                    person_role_filters = [r.lower() for r in derived_roles]
        
        # Check for special repository queries
        query_lower = query.lower()
        is_repo_query = filter_type == 'repository'
        is_max_query = any(term in query_lower for term in ['max', 'most', 'top', 'highest', 'best'])
        
        # Handle special query: repos with max stars
        if is_repo_query and is_max_query and 'star' in query_lower:
            results = self._get_top_starred_repos(top_k)
            response = self._generate_graph_aware_response(query, results)
            graph_data = self._build_visualization_data(results[:5])
            
            return {
                'query': query,
                'matches': results,
                'response': response,
                'graph': graph_data,
                'total_results': len(results),
                'search_params': {
                    'special_query': 'top_starred_repos',
                    'filter_type': 'repository'
                }
            }
        
        # Get embedding using possibly refined focus
        query_embedding = self._get_query_embedding(embedding_query)

        # Extract optional filters from the free-text query (already computed above)
        exclude_locations = self._derive_exclude_locations(location_code)
        
        # Log applied filters for debugging
        if min_repo_stars or numeric_filters:
            logger.info(f"Search filters - min_repo_stars: {min_repo_stars}, numeric_filters: {numeric_filters}, filter_type: {filter_type}")
        
        # Perform hybrid search (vector + graph)
        adjusted_top_k = top_k * 2 if location_code else top_k
        results = self.neo4j_store.hybrid_search(
            query_embedding=query_embedding,
            node_type=filter_type,
            top_k=adjusted_top_k,
            graph_depth=graph_depth,
            location_filters=self._aliases_for_code(location_code) if location_code else None,
            batch_filters=batch_filters,
            exclude_location_filters=exclude_locations,
            min_repo_stars=min_repo_stars,
            person_role_filters=person_role_filters
        )

        # Escalate to planner if nothing found yet
        if not results and not used_planner:
            plan = self._plan_query(query)
            used_planner = True
            if isinstance(plan.get("filter_type"), str):
                filter_type = plan["filter_type"]
            if isinstance(plan.get("person_roles"), list):
                person_role_filters = [r.lower() for r in plan["person_roles"] if isinstance(r, str)]
            if isinstance(plan.get("min_repo_stars"), int):
                min_repo_stars = plan["min_repo_stars"]
            if isinstance(plan.get("query_focus"), str) and plan["query_focus"].strip():
                embedding_query = plan["query_focus"].strip()
            if (filter_type == 'person') and not person_role_filters:
                derived_roles = self._derive_person_roles_from_query(query)
                if derived_roles:
                    person_role_filters = [r.lower() for r in derived_roles]
            # Re-run once with planned params
            query_embedding = self._get_query_embedding(embedding_query)
            results = self.neo4j_store.hybrid_search(
                query_embedding=query_embedding,
                node_type=filter_type,
                top_k=adjusted_top_k,
                graph_depth=graph_depth,
                location_filters=self._aliases_for_code(location_code) if location_code else None,
                batch_filters=batch_filters,
                exclude_location_filters=exclude_locations,
                min_repo_stars=min_repo_stars,
                person_role_filters=person_role_filters
            )

        # If repositories are in the results, enrich with associated company when available
        try:
            if any(r.get('type') == 'Repository' for r in results):
                results = self._enrich_repository_matches_with_company(results)
        except Exception as e:
            logger.warning(f"Failed to enrich repository matches with company: {e}")

        # If a location was detected in the query, enforce strict filtering in all cases
        if location_code:
            matching: List[Dict[str, Any]] = []
            for r in results:
                location_text = (r.get('metadata') or {}).get('location', '') or ''
                if self._location_matches(location_code, location_text):
                    matching.append(r)
            results = matching[:top_k]

        # If a batch intent was detected and no results, fall back to direct batch query
        if batch_filters and not results:
            results = self.neo4j_store.find_companies_by_batch(batch_filters, limit=top_k)
        
        # Generate intelligent response with graph context
        response = self._generate_graph_aware_response(query, results)
        
        # Build visualization data
        graph_data = self._build_visualization_data(results[:5])
        
        return {
            'query': query,
            'matches': results,  # Changed from 'results' to 'matches' to match frontend
            'response': response,
            'graph': graph_data,
            'total_results': len(results),
            'search_params': {
                'graph_depth': graph_depth,
                'min_score': min_score,
                'filter_type': filter_type,
                'applied_filters': {
                    'location': location_code,
                    'batch': batch_filters,
                    'exclude_locations': exclude_locations,
                    'min_repo_stars': min_repo_stars,
                    'person_roles': person_role_filters
                }
            }
        }

    def _enrich_repository_matches_with_company(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """For each repository match, attach the highest-confidence associated company if present."""
        from backend.utils.neo4j_store import clean_neo4j_data
        enriched: List[Dict[str, Any]] = []
        with self.neo4j_store.driver.session() as session:
            for r in results:
                if r.get('type') != 'Repository':
                    enriched.append(r)
                    continue
                meta = r.get('metadata') or {}
                # Skip if already has company
                if meta.get('company'):
                    enriched.append(r)
                    continue
                repo_id = meta.get('id') or r.get('id')
                if not repo_id:
                    enriched.append(r)
                    continue
                row = session.run(
                    """
                    MATCH (repo:Repository {id: $repo_id})
                    OPTIONAL MATCH (c:Company)-[rel:LIKELY_OWNS]->(repo)
                    WITH c, rel
                    ORDER BY coalesce(rel.confidence, 0) DESC
                    RETURN c, rel
                    LIMIT 1
                    """,
                    { 'repo_id': repo_id }
                ).single()
                if row and row.get('c'):
                    company_node = row.get('c')
                    rel = row.get('rel')
                    company_data = clean_neo4j_data(dict(company_node))
                    company_data.pop('embedding', None)
                    meta['company'] = company_data
                    if rel:
                        rel_data = clean_neo4j_data(dict(rel))
                        meta['company_relationship'] = {
                            'confidence': rel_data.get('confidence', 0),
                            'method': rel_data.get('method', 'unknown')
                        }
                    r['metadata'] = meta
                enriched.append(r)
        return enriched
    
    def find_similar_entities(self, entity_id: str, top_k: int = 5) -> Dict[str, Any]:
        """Find entities similar to a given entity"""
        similar = self.neo4j_store.find_similar_nodes(entity_id, top_k)
        
        return {
            'entity_id': entity_id,
            'similar_entities': similar,
            'count': len(similar)
        }
    
    def _extract_location_from_query(self, query: str) -> Optional[str]:
        """Extract a canonical location code from a free-text query using simple alias matching.
        Returns a key from self.location_aliases (e.g., 'nyc') when matched, else None.
        """
        q = (query or '').lower()
        for canonical, aliases in self.location_aliases.items():
            for alias in aliases:
                if alias in q:
                    return canonical
        return None
    
    def _location_matches(self, canonical_code: str, location_text: str) -> bool:
        """Check if a company location string matches a canonical location code using alias matching."""
        if not canonical_code or not location_text:
            return False
        loc = location_text.lower()
        aliases = self.location_aliases.get(canonical_code, [])
        return any(alias in loc for alias in aliases)

    def _aliases_for_code(self, canonical_code: Optional[str]) -> Optional[List[str]]:
        if not canonical_code:
            return None
        return [a.lower() for a in self.location_aliases.get(canonical_code, [])]

    def _load_location_aliases(self) -> Dict[str, List[str]]:
        """Load location aliases from Neo4j if available; fall back to env JSON; else empty.
        Expected Neo4j schema: (l:Location { canonical: 'nyc', aliases: ['nyc','new york', ...] })
        Expected ENV: LOCATION_ALIASES_JSON = '{"nyc":["nyc","new york"], ...}'
        """
        # Try Neo4j
        try:
            aliases: Dict[str, List[str]] = {}
            with self.neo4j_store.driver.session() as session:
                query = """
                MATCH (l:Location)
                RETURN l.canonical AS canonical, coalesce(l.aliases, []) AS aliases
                """
                rows = session.run(query)
                for row in rows:
                    canonical = (row.get('canonical') or '').strip().lower()
                    alias_list = [str(a).strip().lower() for a in (row.get('aliases') or []) if str(a).strip()]
                    if canonical:
                        aliases[canonical] = alias_list
            if aliases:
                return aliases
        except Exception as e:
            logger.warning(f"Failed to load Location aliases from Neo4j: {e}")
        # Try ENV
        try:
            import json
            raw = os.getenv('LOCATION_ALIASES_JSON')
            if raw:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    normalized: Dict[str, List[str]] = {}
                    for k, v in parsed.items():
                        if isinstance(v, list):
                            normalized[k.lower()] = [str(a).strip().lower() for a in v if str(a).strip()]
                    return normalized
        except Exception as e:
            logger.warning(f"Failed to load LOCATION_ALIASES_JSON: {e}")
        # Default
        return {}

    def _load_industry_names(self) -> List[str]:
        """Load known industries from Neo4j Industry nodes, fallback to an env-provided list, else empty.
        Industry names are normalized to lowercase.
        """
        # Try Neo4j
        try:
            names: List[str] = []
            with self.neo4j_store.driver.session() as session:
                rows = session.run("""
                    MATCH (i:Industry)
                    RETURN toLower(i.name) AS name
                """)
                for row in rows:
                    n = (row.get('name') or '').strip().lower()
                    if n:
                        names.append(n)
            if names:
                # Deduplicate while preserving order
                seen = set()
                ordered = []
                for n in names:
                    if n not in seen:
                        seen.add(n)
                        ordered.append(n)
                return ordered
        except Exception as e:
            logger.warning(f"Failed to load Industry names from Neo4j: {e}")
        # Try ENV list (comma-separated)
        try:
            raw = os.getenv('INDUSTRY_NAMES_CSV')
            if raw:
                parsed = [s.strip().lower() for s in raw.split(',') if s.strip()]
                return parsed
        except Exception as e:
            logger.warning(f"Failed to load INDUSTRY_NAMES_CSV: {e}")
        return []

    def _extract_industries_from_query(self, query: str) -> Optional[List[str]]:
        """Extract industry tokens using alias mapping if available; fallback to name list.
        Returns a list of canonical industry names (lowercased), or None.
        """
        if not query:
            return None
        q = query.lower()
        # Prefer alias mapping when present
        if self.industry_aliases is None:
            self.industry_aliases = self._load_industry_aliases()
        matched: List[str] = []
        if self.industry_aliases:
            for canonical, aliases in self.industry_aliases.items():
                if not canonical:
                    continue
                if canonical in q:
                    matched.append(canonical)
                    continue
                for alias in (aliases or []):
                    a = (alias or '').strip().lower()
                    if a and a in q:
                        matched.append(canonical)
                        break
            matched = list({m for m in matched})
            if matched:
                return matched
        # Fallback to simple name matching
        if self.known_industries is None:
            self.known_industries = self._load_industry_names()
        if not self.known_industries:
            return None
        for ind in self.known_industries:
            if ind and ind in q:
                matched.append(ind)
        matched = list({m for m in matched})
        return matched or None

    def _load_industry_aliases(self) -> Dict[str, List[str]]:
        """Load industry alias mapping from Neo4j Industry nodes (name + aliases) or
        INDUSTRY_ALIASES_JSON env var. Canonicals and aliases are normalized to lowercase.
        """
        # Try Neo4j
        try:
            mapping: Dict[str, List[str]] = {}
            with self.neo4j_store.driver.session() as session:
                rows = session.run(
                    """
                    MATCH (i:Industry)
                    RETURN toLower(i.name) AS canonical, coalesce(i.aliases, []) AS aliases
                    """
                )
                for row in rows:
                    canonical = (row.get('canonical') or '').strip().lower()
                    alias_list = [str(a).strip().lower() for a in (row.get('aliases') or []) if str(a).strip()]
                    if canonical:
                        mapping[canonical] = alias_list
            if mapping:
                return mapping
        except Exception as e:
            logger.warning(f"Failed to load Industry aliases from Neo4j: {e}")
        # Try ENV JSON
        try:
            raw = os.getenv('INDUSTRY_ALIASES_JSON')
            if raw:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    normalized: Dict[str, List[str]] = {}
                    for k, v in parsed.items():
                        if not isinstance(v, list):
                            continue
                        canonical = (str(k) or '').strip().lower()
                        aliases = [str(a).strip().lower() for a in v if str(a).strip()]
                        if canonical:
                            normalized[canonical] = aliases
                    if normalized:
                        return normalized
        except Exception as e:
            logger.warning(f"Failed to load INDUSTRY_ALIASES_JSON: {e}")
        return {}

    def _extract_batch_from_query(self, query: str) -> Optional[List[str]]:
        """Extract implied YC batch filters from natural text, e.g., 'YC W24', 'Winter 2024', 'S24'.
        Returns a list of lowercase substrings to match against c.batch.
        """
        if not query:
            return None
        q = query.lower()
        tokens: List[str] = []
        # Common patterns: W24, S24, W2024, Winter 2024, Summer 2024
        import re
        m = re.search(r"\b([ws])\s*'?\s*(20)?(\d{2})\b", q)
        if m:
            # Map 'w'/'s' to 'winter'/'summer', and normalize year to 20xx
            season = 'winter' if m.group(1) == 'w' else 'summer'
            year2 = m.group(3)
            year = f"20{year2}"
            # Include long form, year, and compact form (e.g., w24)
            tokens.extend([f"{season} {year}", f"{year}", f"{m.group(1)}{year2}"])
        m2 = re.search(r"\b(winter|summer)\s+20(\d{2})\b", q)
        if m2:
            tokens.append(f"{m2.group(1)} 20{m2.group(2)}")
        # Also handle explicit phrases like 'yc w24'
        m3 = re.search(r"yc\s+([ws])\s*(\d{2})\b", q)
        if m3:
            season = 'winter' if m3.group(1) == 'w' else 'summer'
            tokens.append(f"{season} 20{m3.group(2)}")
        # Deduplicate & return
        tokens = list({t for t in tokens if t})
        return tokens or None

    def _get_top_starred_repos(self, top_k: int = 10) -> List[Dict[str, Any]]:
        """Get repositories with the most stars, including their associated companies"""
        from backend.utils.neo4j_store import clean_neo4j_data
        
        with self.neo4j_store.driver.session() as session:
            query = """
            MATCH (r:Repository)
            WHERE r.stars IS NOT NULL
            OPTIONAL MATCH (c:Company)-[rel:OWNS|LIKELY_OWNS]->(r)
            WITH r, c, rel
            ORDER BY r.stars DESC
            LIMIT $top_k
            RETURN r, c, rel
            """
            
            results = session.run(query, {'top_k': top_k})
            
            matches = []
            for record in results:
                repo_node = record['r']
                company_node = record['c']
                rel = record['rel']
                
                # Build repo data and clean Neo4j types
                repo_data = clean_neo4j_data(dict(repo_node))
                repo_data.pop('embedding', None)  # Remove embedding from response
                
                # Add company info if available
                if company_node:
                    company_data = clean_neo4j_data(dict(company_node))
                    company_data.pop('embedding', None)
                    repo_data['company'] = company_data
                    if rel:
                        rel_data = clean_neo4j_data(dict(rel))
                        repo_data['company_relationship'] = {
                            'confidence': rel_data.get('confidence', 0),
                            'method': rel_data.get('method', 'unknown')
                        }
                
                matches.append({
                    'id': repo_data.get('id'),
                    'score': 1.0,  # Special query, not similarity-based
                    'type': 'Repository',
                    'metadata': repo_data
                })
            
            return matches
    
    def _derive_exclude_locations(self, canonical_code: Optional[str]) -> Optional[List[str]]:
        """Given a selected canonical location (e.g., 'sf'), derive alias lists for other major hubs to exclude (e.g., NYC, LA).
        This reduces far-off false positives like NYC when searching for SF.
        """
        if not canonical_code:
            return None
        hubs = set(self.location_aliases.keys())
        if canonical_code in hubs:
            hubs.remove(canonical_code)
        # Heuristic: only exclude well-known distant hubs that frequently collide
        candidates = [k for k in hubs if k in {'nyc', 'la', 'boston', 'london'}]
        exclude_aliases: List[str] = []
        for k in candidates:
            exclude_aliases.extend(self.location_aliases.get(k, []))
        return [a.lower() for a in exclude_aliases] or None
    
    def get_entity_network(self, entity_id: str, depth: int = 2) -> Dict[str, Any]:
        """Get the network around an entity"""
        network = self.neo4j_store.get_node_with_connections(entity_id, depth)
        
        # Add explanation of key connections
        if network['nodes']:
            explanation = self._explain_network(network)
            network['explanation'] = explanation
        
        return network
    
    def _get_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for the search query"""
        response = self.openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        return response.data[0].embedding
    
    def _generate_graph_aware_response(self, query: str, results: List[Dict[str, Any]]) -> str:
        """Generate response that includes graph relationship insights"""
        if not results:
            return "No relevant information found for your query."
        
        # Separate direct matches from graph-expanded results
        direct_matches = [r for r in results if 'connection' not in r]
        connected_matches = [r for r in results if 'connection' in r]
        
        # Build context
        context_parts = ["Based on my analysis of the startup ecosystem:\n"]
        
        # Direct matches
        if direct_matches:
            context_parts.append("**Direct Matches:**")
            for i, match in enumerate(direct_matches[:3], 1):
                data = match['metadata']  # Changed from 'data' to 'metadata'
                context_parts.append(
                    f"{i}. **{data.get('name', 'Unknown')}** ({match['type']})"
                )
                if 'description' in data and data['description']:
                    context_parts.append(f"   - {data['description'][:150]}...")
                context_parts.append(f"   - Relevance Score: {match['score']:.2f}")
        
        # Connected entities
        if connected_matches:
            context_parts.append("\n**Related Entities (discovered through connections):**")
            for match in connected_matches[:3]:
                data = match['metadata']  # Changed from 'data' to 'metadata'
                conn = match['connection']
                context_parts.append(
                    f"- **{data.get('name', 'Unknown')}** "
                    f"(connected via {' → '.join(conn['path'])})"
                )
                if 'description' in data and data['description']:
                    context_parts.append(f"  {data['description'][:100]}...")
        
        context = "\n".join(context_parts)
        
        # Generate intelligent response
        prompt = f"""Based on the following search results from our startup ecosystem knowledge graph, 
provide an insightful response to the user's query. Focus on:
1. Directly answering the query
2. Highlighting interesting connections between entities
3. Providing actionable insights
4. Mentioning specific names and relationships

User Query: {query}

Search Results:
{context}

Provide a comprehensive yet concise response (max 3-4 paragraphs)."""

        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": "You are an AI analyst specializing in startup ecosystems. "
                              "You excel at finding hidden connections and providing strategic insights. "
                              "Focus on being specific and actionable."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content
    
    def _build_visualization_data(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build graph data for visualization"""
        nodes = []
        edges = []
        seen_nodes = set()
        
        for result in results:
            # Add main node
            node_id = result['id']
            if node_id not in seen_nodes:
                seen_nodes.add(node_id)
                nodes.append({
                    'id': node_id,
                    'label': result['metadata'].get('name', 'Unknown'),
                    'type': result['type'],
                    'score': result.get('score', 0)
                })
        
            # Add connection edges
            if 'connection' in result:
                conn = result['connection']
                from_id = conn['from_id']
                
                # Ensure source node is in the graph
                if from_id not in seen_nodes:
                    # We need to get info about the source node
                    seen_nodes.add(from_id)
                    nodes.append({
                        'id': from_id,
                        'label': f"Entity {from_id[:8]}...",
                        'type': 'Unknown'
                    })
                
                edges.append({
                    'from': from_id,
                    'to': node_id,
                    'label': conn['path'][-1] if conn['path'] else 'connected'
                })
        
        return {
            'nodes': nodes,
            'edges': edges
        }
    
    def _explain_network(self, network: Dict[str, Any]) -> str:
        """Generate explanation of a network"""
        if not network['nodes']:
            return "No network found."
        
        center_node = network['nodes'][0]
        num_connections = len(network['nodes']) - 1
        
        explanation = (
            f"{center_node['name']} ({center_node['type']}) has "
            f"{num_connections} connected entities in the network."
        )
        
        # Analyze relationship types
        rel_types = {}
        for edge in network['edges']:
            rel_type = edge['type']
            rel_types[rel_type] = rel_types.get(rel_type, 0) + 1
        
        if rel_types:
            explanation += " Relationships include: "
            rel_parts = [f"{count} {rel_type}" for rel_type, count in rel_types.items()]
            explanation += ", ".join(rel_parts) + "."
        
        return explanation