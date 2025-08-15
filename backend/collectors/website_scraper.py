import httpx
import re
import json
from urllib.parse import urljoin
from typing import List


class WebsiteScraper:
    async def scrape_founders(self, base_url: str) -> List[str]:
        if not base_url:
            return []
        # Normalize URL: prefer https, strip trailing slashes
        url = base_url.strip()
        if url.startswith('http://'):
            url = 'https://' + url[len('http://'):]
        if not url.startswith('http'):
            url = 'https://' + url
        url = url.rstrip('/')

        candidates = ['about', 'team', 'company', 'our-team', 'founders']
        urls = [url]
        for path in candidates:
            try:
                urls.append(urljoin(url + '/', path))
            except Exception:
                continue

        # Collect candidate names with priority: JSON-LD, then regex
        collected: List[str] = []

        # Name validation: 2-3 capitalized tokens, optional hyphen/apostrophe within tokens
        name_token = r"[A-Z][a-z]+(?:[-'][A-Z][a-z]+)*"
        name_pattern_strict = re.compile(rf"^{name_token}(?:\s{name_token}){{1,2}}$")

        # Founder proximity regex (before/after keyword), limited window
        regex_before = re.compile(rf"({name_token}(?:\s{name_token}){{1,2}})\s*.{{0,30}}\b(Co-?founder|Founder)\b", re.IGNORECASE)
        regex_after = re.compile(rf"\b(Co-?founder|Founder)\b\s*.{{0,30}}({name_token}(?:\s{name_token}){{1,2}})", re.IGNORECASE)

        # Stopword filter to weed out partial sentences
        stopwords = {"and", "or", "of", "for", "from", "the", "to", "with", "as", "is", "at", "in", "by"}

        def is_valid_name(name: str) -> bool:
            n = (name or "").strip()
            if not n or not name_pattern_strict.match(n):
                return False
            tokens = n.split()
            if any(t.lower() in stopwords for t in tokens):
                return False
            # Disallow internal punctuation beyond hyphen/apostrophe already handled
            if any(any(ch in t for ch in ",.;:!?_$/\\[]{}()<>\"") for t in tokens):
                return False
            return True

        def append_unique(name: str):
            if name and name not in collected and is_valid_name(name):
                collected.append(name)

        def extract_jsonld_names(html: str):
            # Find <script type="application/ld+json"> blocks
            for script_content in re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, flags=re.IGNORECASE | re.DOTALL):
                try:
                    data = json.loads(script_content)
                except Exception:
                    # Some sites embed multiple JSON-LD objects concatenated; try to bracket common cases
                    try:
                        # Attempt to wrap in array if multiple objects are adjacent
                        fixed = f"[{script_content}]".replace('}\n{', '},{')
                        data = json.loads(fixed)
                    except Exception:
                        continue

                def walk(obj):
                    if isinstance(obj, dict):
                        typ = (obj.get('@type') or obj.get('type') or '').lower()
                        if typ == 'person':
                            nm = obj.get('name')
                            if isinstance(nm, str):
                                append_unique(nm.strip())
                            elif isinstance(nm, list):
                                for v in nm:
                                    if isinstance(v, str):
                                        append_unique(v.strip())
                        # Founders commonly under Organization
                        if typ in {'organization', 'corp', 'company'}:
                            founders = obj.get('founder') or obj.get('founders')
                            if isinstance(founders, list):
                                for f in founders:
                                    if isinstance(f, dict):
                                        nm = f.get('name')
                                        if isinstance(nm, str):
                                            append_unique(nm.strip())
                                    elif isinstance(f, str):
                                        append_unique(f.strip())
                            elif isinstance(founders, dict):
                                nm = founders.get('name')
                                if isinstance(nm, str):
                                    append_unique(nm.strip())
                        # Recurse
                        for v in obj.values():
                            walk(v)
                    elif isinstance(obj, list):
                        for it in obj:
                            walk(it)

                walk(data)
        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True, headers={'User-Agent': 'startup-ecosystem-intelligence', 'Accept': 'text/html,application/xhtml+xml;q=0.9,*/*;q=0.8'}) as client:
                for u in urls:
                    try:
                        resp = await client.get(u)
                        if resp.status_code != 200:
                            continue
                        ct = resp.headers.get('Content-Type', '')
                        if 'text/html' not in ct.lower():
                            continue
                        html = resp.text or ''
                        # JSON-LD first
                        extract_jsonld_names(html)
                        # Regex proximity matches (before/after)
                        for m in regex_before.finditer(html):
                            append_unique(m.group(1).strip())
                        for m in regex_after.finditer(html):
                            append_unique(m.group(2).strip())
                        # Cap to top 3 names per site
                        if len(collected) >= 3:
                            break
                    except Exception:
                        continue
        except Exception:
            pass
        # Return up to 3 deduped names
        return collected[:3]


