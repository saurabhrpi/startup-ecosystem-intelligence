import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def read_text(rel_path: str) -> str:
    p = REPO_ROOT / rel_path
    if not p.exists():
        raise FileNotFoundError(rel_path)
    return p.read_text(encoding='utf-8', errors='ignore')


def check_exists(paths: list[str]) -> list[str]:
    errors = []
    for rel in paths:
        if not (REPO_ROOT / rel).exists():
            errors.append(f"Missing required path: {rel}")
    return errors


def check_frontend_signed_headers() -> list[str]:
    errors: list[str] = []
    # search route must send all signed headers
    s = read_text('frontend/app/api/search/route.ts')
    for header in ['x-user-id', 'x-user-email', 'x-user-ts', 'x-user-sig', 'x-api-key']:
        if header not in s:
            errors.append(f"frontend/app/api/search/route.ts missing header: {header}")
    if 'createHmac' not in s:
        errors.append("frontend/app/api/search/route.ts missing createHmac signer")

    # preferences route must send signed headers
    pr = read_text('frontend/app/api/user/preferences/route.ts')
    for header in ['x-user-id', 'x-user-email', 'x-user-ts', 'x-user-sig', 'x-api-key']:
        if header not in pr:
            errors.append(f"frontend/app/api/user/preferences/route.ts missing header: {header}")

    # follow route must send signed headers
    fr = read_text('frontend/app/api/user/follow/route.ts')
    for header in ['x-user-id', 'x-user-email', 'x-user-ts', 'x-user-sig', 'x-api-key']:
        if header not in fr:
            errors.append(f"frontend/app/api/user/follow/route.ts missing header: {header}")
    return errors


def check_no_direct_backend_calls() -> list[str]:
    """Disallow direct fetches to NEXT_PUBLIC_API_URL outside API proxy routes."""
    errors: list[str] = []
    for rel in [
        'frontend/app/page.tsx',
    ]:
        if not (REPO_ROOT / rel).exists():
            continue
        t = read_text(rel)
        if 'NEXT_PUBLIC_API_URL' in t or re.search(r"fetch\(\`\$\{apiUrl\}/", t):
            errors.append(f"Direct backend call detected in {rel}. Use Next.js API proxy route instead.")
    return errors


def check_backend_security_dependencies() -> list[str]:
    errors: list[str] = []
    m = read_text('backend/api/main.py')
    required_decorators = [
        ('/search", response_model', '@app.post("/search', 'require_user_sig'),
        ('/search", response_model', '@app.get("/search', 'require_user_sig'),
        ('/users/me/preferences"', '@app.get("/users/me/preferences', 'require_user_sig'),
        ('/users/me/preferences"', '@app.put("/users/me/preferences', 'require_user_sig'),
        ('/users/me/follow"', '@app.post("/users/me/follow', 'require_user_sig'),
    ]
    for needle, route_tag, dep in required_decorators:
        if needle.split(',')[0] not in m and route_tag not in m:
            errors.append(f"backend/api/main.py missing route for {needle}")
        # ensure require_user_sig appears in dependency list for route
    for route in [
        '@app.post("/search"', '@app.get("/search"',
        '@app.get("/users/me/preferences"', '@app.put("/users/me/preferences"', '@app.post("/users/me/follow"',
    ]:
        # extract decorator block line
        idx = m.find(route)
        if idx == -1:
            continue
        line = m[idx: idx + 200]
        if 'require_user_sig' not in line:
            errors.append(f"{route} missing require_user_sig dependency")
    # CORS tightening: ensure production path does not default to '*'
    if 'allowed_origins = []' not in m:
        errors.append("backend/api/main.py production CORS fallback should lock down (allowed_origins = [])")
    # Security headers present
    if 'Content-Security-Policy' not in m:
        errors.append("backend/api/main.py missing CSP header in SecurityHeadersMiddleware")
    return errors


def check_graph_rag_safety() -> list[str]:
    errors: list[str] = []
    g = read_text('backend/api/graph_rag_service.py')
    if 'blocked_terms' not in g or "'blocked': True" not in g:
        errors.append("graph_rag_service.search should block unsafe terms and mark search_params.blocked = True")
    if 'if top_k > 50' not in g and 'top_k = 50' not in g:
        errors.append("graph_rag_service.search should clamp top_k to 50")
    return errors


def check_neo4j_constraints() -> list[str]:
    errors: list[str] = []
    s = read_text('backend/utils/neo4j_store.py')
    needed = [
        'CREATE CONSTRAINT user_id IF NOT EXISTS',
        'CREATE CONSTRAINT company_id IF NOT EXISTS',
        'CREATE CONSTRAINT person_id IF NOT EXISTS',
        'CREATE CONSTRAINT repo_id IF NOT EXISTS',
    ]
    for n in needed:
        if n not in s:
            errors.append(f"neo4j_store missing uniqueness constraint: {n}")
    return errors


def check_frontend_policy_flags() -> list[str]:
    errors: list[str] = []
    # ResponseDisplay should accept filterOnly or HomeClient should pass it.
    hc = read_text('frontend/components/HomeClient.tsx')
    if 'filterOnly' not in hc:
        errors.append("HomeClient should pass filterOnly to ResponseDisplay and grids")
    # ensure no production console.log in next.config.js
    nx = read_text('frontend/next.config.js')
    if 'console.log' in nx:
        errors.append('next.config.js should not log in production')
    # TypeScript strict mode
    ts = read_text('frontend/tsconfig.json')
    if re.search(r'"strict"\s*:\s*true', ts) is None:
        errors.append('TypeScript strict mode should be enabled')
    return errors


def main():
    errors: list[str] = []

    errors += check_exists([
        'backend/api/main.py',
        'backend/api/graph_rag_service.py',
        'backend/utils/neo4j_store.py',
        'frontend/app/api/search/route.ts',
        'frontend/app/api/user/preferences/route.ts',
        'frontend/app/api/user/follow/route.ts',
    ])

    try:
        errors += check_frontend_signed_headers()
    except Exception as e:
        errors.append(f"frontend header validation failed: {e}")

    try:
        errors += check_no_direct_backend_calls()
    except Exception as e:
        errors.append(f"direct backend call validation failed: {e}")

    try:
        errors += check_backend_security_dependencies()
    except Exception as e:
        errors.append(f"backend security validation failed: {e}")

    try:
        errors += check_graph_rag_safety()
    except Exception as e:
        errors.append(f"graph rag validation failed: {e}")

    try:
        errors += check_neo4j_constraints()
    except Exception as e:
        errors.append(f"neo4j constraints validation failed: {e}")

    try:
        errors += check_frontend_policy_flags()
    except Exception as e:
        errors.append(f"frontend policy validation failed: {e}")

    if errors:
        print("Validation failed with the following issues:")
        for e in errors:
            print(f" - {e}")
        sys.exit(1)
    print("Validation OK")


if __name__ == '__main__':
    main()

import os
import sys

def main():
    # Basic guard: ensure critical env vars are wired in the repo (not values)
    required = [
        'NEXT_PUBLIC_API_URL',
    ]
    missing = []
    for name in required:
        if name not in os.environ and not os.getenv(name):
            # In CI, these may not be set; allow, but warn
            pass

    # Lightweight static checks: ensure key files exist
    required_paths = [
        'backend/api/main.py',
        'backend/api/graph_rag_service.py',
        'frontend/app/api/search/route.ts',
    ]
    for p in required_paths:
        if not os.path.exists(p):
            print(f"Missing required path: {p}")
            sys.exit(1)

    print("Validation OK")

if __name__ == '__main__':
    main()


