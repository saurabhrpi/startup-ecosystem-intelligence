"""
Backfill missing investors for companies by querying Google Custom Search.

Behavior:
- Finds companies with zero incoming INVESTS_IN relationships
- Queries Google CSE for up to 3 investor names per company (cached; throttled)
- Creates Person nodes (role=investor) and INVESTS_IN edges
- Optionally generates embeddings for new Person nodes (default: true)

Run:
  python -m backend.scripts.backfill_investors --limit 500 --concurrency 5

Environment:
- GOOGLE_CSE_API_KEY, GOOGLE_CSE_CX must be set
- USE_CSE_FOR_FOUNDERS should be true (default) or ignored here
- EMBED_INVESTORS=true|false (default true)
- GOOGLE_CSE_CACHE_DIR, GOOGLE_CSE_MIN_DELAY_MS control caching/throttle
"""

import asyncio
import os
import hashlib
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from backend.utils.neo4j_store import Neo4jStore
from backend.collectors.google_cse import GoogleCSEClient
from backend.utils.name_guard import is_probable_person_name
from backend.config import settings


def _extract_domain(url: Optional[str]) -> str:
    try:
        if not url:
            return ''
        host = urlparse(url).netloc.lower()
        if host.startswith('www.'):
            host = host[4:]
        return host
    except Exception:
        return ''


def _generate_person_id(name: str, source: str = 'google_cse') -> str:
    """Deterministic person id compatible with pipeline's scheme."""
    content = f"person_{name}_{source}"
    return hashlib.md5(content.encode()).hexdigest()


async def _get_investors_for_company(cse: GoogleCSEClient, company_name: str, website: Optional[str]) -> List[str]:
    domain = _extract_domain(website or '')
    try:
        return await cse.search_investors(company_name or '', domain)
    except Exception:
        return []


async def backfill_investors(limit: int = 500, concurrency: int = 5, embed_investors: bool = True) -> None:
    if not (settings.google_cse_api_key and settings.google_cse_cx):
        print("[ERROR] Google CSE not configured. Set GOOGLE_CSE_API_KEY and GOOGLE_CSE_CX.")
        return

    store = Neo4jStore()
    cse = GoogleCSEClient()

    # Fetch candidate companies with zero investors
    print(f"[QUERY] Fetching up to {limit} companies lacking INVESTS_IN edges...")
    companies: List[Dict[str, Any]] = []
    with store.driver.session() as session:
        rows = session.run(
            """
            MATCH (c:Company)
            OPTIONAL MATCH (:Person)-[:INVESTS_IN]->(c)
            WITH c, count(*) AS investor_count
            WHERE investor_count = 0
            RETURN c.id AS id, c.name AS name, c.website AS website, c.location AS location, c.batch AS batch
            LIMIT $limit
            """,
            {"limit": limit},
        )
        for r in rows:
            companies.append({
                'id': r.get('id'),
                'name': r.get('name'),
                'website': r.get('website'),
                'location': r.get('location'),
                'batch': r.get('batch'),
            })

    if not companies:
        print("[INFO] No companies without investors found. Nothing to backfill.")
        return

    print(f"[INFO] Backfilling investors for {len(companies)} companies (concurrency={concurrency})")

    sem = asyncio.Semaphore(max(1, concurrency))

    async def process_company(company: Dict[str, Any]):
        async with sem:
            company_id = company.get('id')
            company_name = company.get('name') or ''
            website = company.get('website') or ''
            if not company_id or not company_name:
                return

            # Double-check no investors exist (race condition safe)
            with store.driver.session() as session:
                existing = session.run(
                    """
                    MATCH (:Person)-[:INVESTS_IN]->(c:Company {id: $company_id})
                    RETURN count(*) AS cnt
                    """,
                    {"company_id": company_id},
                ).single()
                if existing and (existing.get('cnt') or 0) > 0:
                    return

            names = await _get_investors_for_company(cse, company_name, website)
            if not names:
                return

            # Insert investors
            for nm in names:
                if not nm or not is_probable_person_name(nm):
                    continue
                person_id = _generate_person_id(nm, 'google_cse')
                # Prepare person payload
                person_data = {
                    'id': person_id,
                    'name': nm,
                    'role': 'investor',
                    'roles': ['investor'],
                    'company': company_name,
                    'source': 'google_cse',
                    'location': company.get('location') or '',
                    'location_code': '',
                    'batch': company.get('batch') or '',
                    'batch_code': '',
                }

                embedding = None
                if embed_investors:
                    try:
                        import openai
                        openai.api_key = settings.openai_api_key
                        text = f"Name: {nm}\nRole: Investor\nCompany: {company_name}"
                        resp = openai.embeddings.create(model=settings.embedding_model, input=text)
                        embedding = resp.data[0].embedding
                    except Exception as e:
                        print(f"[WARN] Embedding failed for {nm}: {e}")
                        embedding = None

                # Upsert person and relationship
                store.create_person_with_embedding(person_data, embedding)
                store.create_relationship(
                    from_id=person_id,
                    to_id=company_id,
                    rel_type='INVESTS_IN',
                    properties={'role': 'Investor'}
                )

    await asyncio.gather(*(process_company(c) for c in companies))
    print("[DONE] Investor backfill complete.")


def _parse_bool(val: Optional[str], default: bool) -> bool:
    if val is None:
        return default
    return str(val).lower() in ("1", "true", "yes", "y", "on")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Backfill investors for companies without INVESTS_IN edges")
    parser.add_argument("--limit", type=int, default=int(os.getenv("INVESTOR_BACKFILL_LIMIT", "500")), help="Max companies to process")
    parser.add_argument("--concurrency", type=int, default=int(os.getenv("INVESTOR_BACKFILL_CONCURRENCY", "5")), help="Concurrent companies to process")
    parser.add_argument("--no-embed", action="store_true", help="Do not generate embeddings for new investor persons")
    args = parser.parse_args()

    asyncio.run(backfill_investors(limit=args.limit, concurrency=args.concurrency, embed_investors=not args.no_embed))


