from ddgs import DDGS
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import requests
import re


BLOCKED_DOMAINS = {
    # video/social
    "youtube.com", "www.youtube.com", "youtu.be",
    "vimeo.com", "www.vimeo.com",
    "tiktok.com", "www.tiktok.com",
    "instagram.com", "www.instagram.com",

    # ad/redirect engines
    "bing.com", "www.bing.com",

    # template / generic diagram sites
    "mural.co", "www.mural.co",
    "lucidchart.com", "www.lucidchart.com",
    "canva.com", "www.canva.com",
    
}

# Hard paywalls / course sites (we can expand later)
PAYWALL_DOMAINS = {
    "educative.io", "www.educative.io",
    "medium.com", "www.medium.com",
    "leetcode.com", "www.leetcode.com",
    "dzone.com", "www.dzone.com",
    #v"algomaster.io", "www.algomaster.io", "blog.algomaster.io",
    # "substack.com", "www.substack.com",
    # medium.com is NOT included (good content; handle paywall at scrape time)
}

NEGATIVE = " -youtube -video -ppt -slides -course -udemy -pdf -template"

# URL patterns we never want (tracking / redirects)
BAD_URL_SUBSTRINGS = [
    "bing.com/aclick", "aclick?", "msclkid=", "utm_", "gclid=", "fbclid=",
]

TRACKING_KEYS_PREFIX = ("utm_",)
TRACKING_KEYS_EXACT = {"gclid", "fbclid", "msclkid", "yclid", "mc_cid", "mc_eid"}

def _canonical_url(url: str) -> str:
    """
    Remove tracking query params and normalize scheme/host/path.
    """
    try:
        p = urlparse(url)
        # drop fragment
        fragment = ""

        # clean query params
        q = []
        for k, v in parse_qsl(p.query, keep_blank_values=True):
            lk = k.lower()
            if lk in TRACKING_KEYS_EXACT:
                continue
            if any(lk.startswith(pref) for pref in TRACKING_KEYS_PREFIX):
                continue
            q.append((k, v))
        query = urlencode(q, doseq=True)

        # normalize: lowercase hostname, strip trailing slash
        netloc = (p.hostname or "").lower()
        if p.port:
            netloc = f"{netloc}:{p.port}"

        path = p.path or ""
        if path != "/":
            path = path.rstrip("/")

        clean = urlunparse((p.scheme or "https", netloc, path, p.params, query, fragment))
        return clean
    except Exception:
        return url

def _filter_by_domain(urls: list[str], max_per_domain: int = 1) -> list[str]:
    out = []
    counts: dict[str, int] = {}
    for u in urls:
        h = _host(u)
        if not h:
            continue
        c = counts.get(h, 0)
        if c >= max_per_domain:
            continue
        counts[h] = c + 1
        out.append(u)
    return out

LIGHT_SIGNALS = [
    "system design", "system architecture", "high level", "low level",
    "architecture diagram", "data flow", "request flow", "components",
    "api gateway", "load balancer", "cache", "database", "queue",
    "microservice", "latency", "throughput", "scalability", "tradeoff"
]

def _light_score_url(url: str, headers: dict, timeout: int = 12) -> int:
    """
    Quick fetch and score based on presence of system design signals in title/h tags/first text.
    Returns -inf-ish score on failure.
    """
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code >= 400:
            return -999

        html = r.text.lower()
        score = 0
        for kw in LIGHT_SIGNALS:
            if kw in html:
                score += 1

        # small bonus if it likely contains diagrams/images
        if "<img" in html:
            score += 2
        if "diagram" in html or "architecture" in html:
            score += 2

        return score
    except Exception:
        return -999

def _rerank_with_light_scrape(
    urls: list[str],
    headers: dict,
    top_n: int = 10,
) -> list[str]:
    scored = []
    for u in urls[:top_n]:
        s = _light_score_url(u, headers=headers)
        scored.append((s, u))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [u for s, u in scored if s > -999]


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def _is_bad_url(url: str) -> bool:
    u = url.lower()
    return any(b in u for b in BAD_URL_SUBSTRINGS)


def _is_allowed(url: str, allow_paywall: bool = True) -> bool:
    if _is_bad_url(url):
        return False
    h = _host(url)
    if not h:
        return False
    if h in BLOCKED_DOMAINS:
        return False
    if not allow_paywall and h in PAYWALL_DOMAINS:
        return False
    return True

def _is_acronym(topic: str) -> bool:
    t = topic.strip()
    return t.isupper() and 2 <= len(t) <= 6 and t.isalpha()

def _topic_signals(topic: str) -> list[str]:
    t = topic.strip().lower()
    signals = []

    # Always include the raw topic tokens
    signals.extend(re.findall(r"[a-z0-9]+", t))

    # If the topic is multi-word, also include the exact phrase
    if " " in t:
        signals.append(t)

    # If it's an acronym, include lowercase acronym + spaced acronym ("d n s")
    # (helps match some pages that write it weirdly)
    if _is_acronym(topic):
        signals.append(t)  # dns
        signals.append(" ".join(list(t)))  # d n s

    # unique
    out = []
    seen = set()
    for s in signals:
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out

def _topic_match_score(topic: str, url: str, title: str, body: str) -> int:
    hay = f"{url} {title} {body}".lower()
    sigs = _topic_signals(topic)

    score = 0
    for s in sigs:
        if not s:
            continue
        if s in hay:
            # strong boost if in url/title
            if s in f"{url} {title}".lower():
                score += 6
            else:
                score += 3
    return score


"""def _topic_terms(topic: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", topic.lower())
    return [w for w in words if len(w) >= 3]


def _contains_topic(topic_terms: list[str], url: str, title: str, body: str) -> bool:
    # require at least one topic term in url+title (stricter, reduces drift)
    hay_strict = f"{url} {title}".lower()
    if any(t in hay_strict for t in topic_terms):
        return True
    # fallback: allow in snippet/body for rare cases
    hay = f"{url} {title} {body}".lower()
    return any(t in hay for t in topic_terms)
"""

def _url_quality_score(url: str) -> int:
    u = url.lower()
    score = 0
    # Good “article-ish” hints
    for good in ["/blog", "/post", "/p/", "/guides", "system-design", "architecture", "interview"]:
        if good in u:
            score += 2
    # Bad hints
    for bad in ["template", "download", "tool", "generator", "pricing", "login", "signup"]:
        if bad in u:
            score -= 3
    return score


def _score(title: str, body: str, level: str, url: str, topic: str) -> int:
    txt = f"{title} {body}".lower()
    level = level.upper()
    score = 0

    # Topic relevance (generic)
    score += _topic_match_score(topic, url, title, body)

    # Strong system design relevance
    if "system design" in txt:
        score += 8
    if "architecture" in txt:
        score += 4

    # Level hints
    if "high level" in txt or "hld" in txt:
        score += (4 if level == "HLD" else 1)
    if "low level" in txt or "lld" in txt:
        score += (4 if level == "LLD" else 1)

    # Signals
    for kw in [
        "components", "data flow", "request flow", "sequence",
        "cache", "database", "queue", "load balancer", "api gateway",
        "microservice", "services", "scalability", "consistency", "latency"
    ]:
        if kw in txt:
            score += 2

    score += _url_quality_score(url)

    return score



def _build_queries(topic: str, level: str) -> list[str]:
    level = level.upper().strip()
    level_terms = "high level design HLD" if level == "HLD" else "low level design LLD"

    t = f"\"{topic}\"" if " " in topic.strip() else topic.strip()

    queries = [
        f'{t} "system design" {level_terms} architecture components relationships data flow{NEGATIVE}',
        f'{t} "system design" {level_terms} "request flow" "data flow"{NEGATIVE}',
        f'{t} {level_terms} backend architecture "load balancer" "api gateway" cache database queue{NEGATIVE}',
    ]

    # Generic help for acronyms/topics that have few system-design posts
    queries.append(f'{t} "how it works" architecture diagram components{NEGATIVE}')

    return queries



def discover_links(
    topic: str,
    level: str,
    max_links: int = 5,
    max_results_per_query: int = 12,
    allow_paywall: bool = True,
) -> list[str]:

    queries = _build_queries(topic, level)
    candidates: list[tuple[int, str]] = []

    with DDGS() as ddgs:
        for q in queries:
            for r in ddgs.text(q, max_results=max_results_per_query):
                url = (r.get("href") or r.get("link") or "").strip()
                title = (r.get("title") or "").strip()
                body = (r.get("body") or r.get("snippet") or "").strip()

                if not url:
                    continue
                if not _is_allowed(url, allow_paywall=allow_paywall):
                    continue

                url = _canonical_url(url)
                s = _score(title, body, level, url, topic)
                candidates.append((s, url))

    candidates.sort(key=lambda x: x[0], reverse=True)

    # 1) dedupe (after canonicalization)
    ranked_urls = []
    seen = set()
    for s, url in candidates:
        if url in seen:
            continue
        seen.add(url)
        ranked_urls.append(url)

    # 2) domain diversity
    ranked_urls = _filter_by_domain(ranked_urls, max_per_domain=1)

    # 3) optional: light scrape rerank
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive",
    }

    ranked_urls = _rerank_with_light_scrape(
        ranked_urls, headers=headers, top_n=min(10, len(ranked_urls))
    )

    return ranked_urls[:max_links]
