import httpx
import re
from urllib.parse import urljoin
from typing import List


class WebsiteScraper:
    async def scrape_founders(self, base_url: str) -> List[str]:
        if not base_url:
            return []
        candidates = ['about', 'team', 'company', 'our-team', 'founders']
        urls = [base_url]
        for path in candidates:
            try:
                urls.append(urljoin(base_url.rstrip('/') + '/', path))
            except Exception:
                continue

        names = set()
        # Simple name + Founder proximity heuristic
        pattern = re.compile(r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)+).{0,60}(Founder|Co-?founder)', re.IGNORECASE)
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                for url in urls:
                    try:
                        resp = await client.get(url)
                        if resp.status_code != 200:
                            continue
                        html = resp.text
                        for m in pattern.finditer(html):
                            names.add(m.group(1).strip())
                    except Exception:
                        continue
        except Exception:
            pass
        return list(names)


