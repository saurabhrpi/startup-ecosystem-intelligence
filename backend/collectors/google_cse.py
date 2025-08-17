import httpx
import re
import os
import json
import hashlib
import asyncio
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from backend.config import settings

NAME_TOKEN = r"[A-Z][a-z]+(?:[-'][A-Z][a-z]+)*"
NAME_2_3 = re.compile(rf"\b{NAME_TOKEN}(?:\s{NAME_TOKEN}){{1,2}}\b")
NEAR_FOUNDER_AFTER = re.compile(rf"\b(Co-?founder|Founder)\b\s*.{{0,40}}({NAME_TOKEN}(?:\s{NAME_TOKEN}){{1,2}})", re.IGNORECASE)
NEAR_INVESTOR_AFTER = re.compile(rf"\b(Investor|Angel|Lead investor|VC|Venture|Partner|General Partner|Managing Partner|Principal|Associate)\b\s*.{{0,60}}({NAME_TOKEN}(?:\s{NAME_TOKEN}){{1,2}})", re.IGNORECASE)

# Minimal validation: title-cased 2–3 tokens with allowed characters

def _is_valid_name(candidate: str) -> bool:
    n = (candidate or '').strip()
    if not n or not NAME_2_3.fullmatch(n):
        return False
    toks = n.split()
    return 1 < len(toks) <= 3 and all(re.fullmatch(NAME_TOKEN, t) for t in toks)

# Lazy NER loader
_ner_nlp = None

def _extract_persons_ner(text: str) -> List[str]:
    global _ner_nlp
    try:
        if _ner_nlp is None:
            import spacy
            try:
                _ner_nlp = spacy.load("en_core_web_sm")
            except Exception:
                return []
        doc = _ner_nlp(text or "")
        names: List[str] = []
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                name = ent.text.strip()
                if _is_valid_name(name):
                    names.append(name)
        # dedupe preserve order, cap 3
        return list(dict.fromkeys(names))[:3]
    except Exception:
        return []


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
        # QPS throttle (min delay between requests)
        self.min_delay_sec = max(0.0, float(os.getenv('GOOGLE_CSE_MIN_DELAY_MS', '300')) / 1000.0)

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
                    data = json.load(f)
                    print(f"[CSE] Cache hit for query: {q}")
                    return data
            except Exception:
                pass
        if self._used >= self.max_run:
            return {"items": []}

        # Throttle QPS
        if self.min_delay_sec > 0:
            await asyncio.sleep(self.min_delay_sec)

        params = {"key": self.api_key, "cx": self.cx, "q": q, "num": min(max(num, 1), 10), "safe": "active"}

        # Retry with backoff on 429
        attempts = 0
        backoff = 1.0
        max_attempts = 5
        while attempts < max_attempts:
            resp = await client.get(self.base_url, params=params)
            self._used += 1
            if resp.status_code == 200:
                data = resp.json() or {"items": []}
                # Persist to cache permanently
                try:
                    with open(cache_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    print(f"[CSE] Network call; cached to: {cache_path}")
                except Exception:
                    print("[CSE] Network call; failed to write cache")
                return data
            if resp.status_code == 429:
                # Honor Retry-After if present, else exponential backoff
                retry_after = resp.headers.get('Retry-After')
                try:
                    wait = float(retry_after) if retry_after else backoff
                except Exception:
                    wait = backoff
                wait = min(max(wait, self.min_delay_sec), 10.0)
                print(f"[CSE] 429 Too Many Requests. Waiting {wait:.2f}s before retry...")
                await asyncio.sleep(wait)
                attempts += 1
                backoff = min(backoff * 2, 8.0)
                continue
            break
        return {"items": []}

    def _extract_from_items(self, items: List[Dict[str, Any]], company_domain: Optional[str]) -> List[str]:
        out: List[str] = []
        seen = set()

        def add(name: str):
            if name and name not in seen and _is_valid_name(name):
                out.append(name)
                seen.add(name)

        for it in items or []:
            snippet = it.get('snippet', '') or ''
            if not snippet:
                continue
            # Primary: NER
            ner_names = _extract_persons_ner(snippet)
            for nm in ner_names:
                add(nm)
            if len(out) >= 3:
                break
            # Fallback: regex after "Founder"
            for m in NEAR_FOUNDER_AFTER.finditer(snippet):
                add(m.group(2).strip())
                if len(out) >= 3:
                    break
            if len(out) >= 3:
                break
        return out[:3]

    def _extract_investors_from_items(self, items: List[Dict[str, Any]], company_domain: Optional[str]) -> List[str]:
        out: List[str] = []
        seen = set()

        def add(name: str):
            if name and name not in seen and _is_valid_name(name):
                out.append(name)
                seen.add(name)

        for it in items or []:
            snippet = it.get('snippet', '') or ''
            if not snippet:
                continue
            # Primary: NER
            ner_names = _extract_persons_ner(snippet)
            for nm in ner_names:
                add(nm)
            if len(out) >= 3:
                break
            # Fallback: regex after investor-related keywords
            for m in NEAR_INVESTOR_AFTER.finditer(snippet):
                add(m.group(2).strip())
                if len(out) >= 3:
                    break
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
                results = list(dict.fromkeys(results))
                if len(results) >= 3:
                    break
        return results[:3]

    async def search_investors(self, company_name: str, company_domain: Optional[str]) -> List[str]:
        if not company_name:
            return []
        queries = [f'"{company_name}" investors', f'"{company_name}" funding investors']
        if company_domain:
            queries.append(f"site:{company_domain} (investor OR investors OR partners OR team)")

        results: List[str] = []
        async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "startup-ecosystem-intelligence"}) as client:
            for idx, q in enumerate(queries):
                if idx >= self.max_per_company:
                    break
                data = await self._query(client, q, num=10)
                results.extend(self._extract_investors_from_items(data.get("items", []), company_domain))
                results = list(dict.fromkeys(results))
                if len(results) >= 3:
                    break
        return results[:3]

    async def search_founders_and_investors(self, company_name: str, company_domain: Optional[str]) -> Dict[str, List[str]]:
        founders = await self.search_founders(company_name, company_domain)
        investors = await self.search_investors(company_name, company_domain)
        return {"founders": founders, "investors": investors}
