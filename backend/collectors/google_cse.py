import httpx
import re
import os
import json
import hashlib
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from backend.config import settings

NAME_TOKEN = r"[A-Z][a-z]+(?:[-'][A-Z][a-z]+)*"
NAME_2_3 = re.compile(rf"\b{NAME_TOKEN}(?:\s{NAME_TOKEN}){{1,2}}\b")
NEAR_FOUNDER_BEFORE = re.compile(rf"({NAME_TOKEN}(?:\s{NAME_TOKEN}){{1,2}})\s*.{{0,40}}\b(Co-?founder|Founder)\b", re.IGNORECASE)
NEAR_FOUNDER_AFTER = re.compile(rf"\b(Co-?founder|Founder)\b\s*.{{0,40}}({NAME_TOKEN}(?:\s{NAME_TOKEN}){{1,2}})", re.IGNORECASE)

# Token blacklist to filter generic words that are not person names
MONTHS = {m.lower() for m in [
    'Jan','January','Feb','February','Mar','March','Apr','April','May','Jun','June','Jul','July','Aug','August','Sep','Sept','September','Oct','October','Nov','November','Dec','December']}
GENERIC_TOKENS = {w.lower() for w in [
    'about','us','closing','opening','remarks','business','insider','press','news','careers','team','leadership',
    'privacy','terms','contact','faq','help','docs','developer','platform','agenda','panel','speakers','webinar',
    'quants','blog','events','jobs','apply','join','company','people','story','stories','mission','values']}


def _is_valid_name(candidate: str) -> bool:
    n = (candidate or '').strip()
    if not n or not NAME_2_3.fullmatch(n):
        return False
    tokens = n.split()
    # Exclude tokens that are months or generic non-person words
    for t in tokens:
        tl = t.lower()
        if tl in MONTHS or tl in GENERIC_TOKENS:
            return False
        # Exclude tokens with disallowed punctuation beyond hyphen/apostrophe
        if re.search(r"[.,;:!?_$/\\\[\]{}()<>\"]", t):
            return False
    return True


class GoogleCSEClient:
    def __init__(self):
        if not (settings.google_cse_api_key and settings.google_cse_cx):
            raise RuntimeError("Google CSE not configured. Set GOOGLE_CSE_API_KEY and GOOGLE_CSE_CX.")
        self.api_key = settings.google_cse_api_key
        self.cx = settings.google_cse_cx
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        self.max_run = settings.max_cse_queries_per_run
        self.max_per_company = settings.max_cse_queries_per_company
        self._used = 0
        # Permanent cache
        self.cache_dir = os.getenv('GOOGLE_CSE_CACHE_DIR', 'data/cache/google_cse')
        self.force_refresh = os.getenv('GOOGLE_CSE_FORCE_REFRESH', 'false').lower() == 'true'
        os.makedirs(self.cache_dir, exist_ok=True)

    def _cache_path(self, q: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", (q or '').lower()).strip('-')[:64]
        h = hashlib.sha1(q.encode('utf-8')).hexdigest()[:10]
        fname = f"{slug}-{h}.json" if slug else f"q-{h}.json"
        return os.path.join(self.cache_dir, fname)

    async def _query(self, client: httpx.AsyncClient, q: str, num: int = 10) -> Dict[str, Any]:
        # Serve from cache unless forced to refresh
        cache_path = self._cache_path(q)
        if not self.force_refresh and os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        if self._used >= self.max_run:
            return {"items": []}
        params = {"key": self.api_key, "cx": self.cx, "q": q, "num": min(max(num, 1), 10), "safe": "active"}
        resp = await client.get(self.base_url, params=params)
        self._used += 1
        if resp.status_code != 200:
            return {"items": []}
        data = resp.json() or {"items": []}
        # Persist to cache permanently
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return data

    def _extract_from_items(self, items: List[Dict[str, Any]], company_domain: Optional[str]) -> List[str]:
        out: List[str] = []
        seen = set()

        def add(name: str):
            if name and name not in seen and _is_valid_name(name):
                out.append(name)
                seen.add(name)

        for it in items or []:
            # Only analyze the snippet for proximity to avoid title noise like "About Us"
            text = it.get('snippet', '') or ''
            if not text:
                continue

            for m in NEAR_FOUNDER_BEFORE.finditer(text):
                cand = m.group(1).strip()
                add(cand)
            for m in NEAR_FOUNDER_AFTER.finditer(text):
                cand = m.group(2).strip()
                add(cand)
            if len(out) >= 3:
                break
        return out[:3]

    async def search_founders(self, company_name: str, company_domain: Optional[str]) -> List[str]:
        if not company_name:
            return []
        queries = [f'"{company_name}" founders']
        if company_domain:
            queries.append(f"site:{company_domain} (founder OR cofounder)")

        results: List[str] = []
        async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "startup-ecosystem-intelligence"}) as client:
            for idx, q in enumerate(queries):
                if idx >= self.max_per_company:
                    break
                data = await self._query(client, q, num=10)
                results.extend(self._extract_from_items(data.get("items", []), company_domain))
                # Deduplicate while preserving order
                results = list(dict.fromkeys(results))
                if len(results) >= 3:
                    break
        return results[:3]
