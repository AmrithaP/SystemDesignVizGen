from ddgs import DDGS
from urllib.parse import urlparse
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


def _topic_terms(topic: str) -> list[str]:
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


def _score(title: str, body: str, level: str, url: str) -> int:
    txt = f"{title} {body}".lower()
    level = level.upper()
    score = 0

    # Strong relevance
    if "system design" in txt:
        score += 8
    if "architecture" in txt:
        score += 4

    # Level hints
    if "high level" in txt or "hld" in txt:
        score += (4 if level == "HLD" else 1)
    if "low level" in txt or "lld" in txt:
        score += (4 if level == "LLD" else 1)

    # Signals of components/relationships/connectivity
    for kw in [
        "components", "data flow", "request flow", "sequence",
        "cache", "database", "queue", "load balancer", "api gateway",
        "microservice", "services", "scalability"
    ]:
        if kw in txt:
            score += 2

    # URL-quality boosts/penalties
    score += _url_quality_score(url)

    return score


def _build_queries(topic: str, level: str) -> list[str]:
    level = level.upper().strip()
    level_terms = "high level design HLD" if level == "HLD" else "low level design LLD"

    # Quote the topic to reduce drift (especially multi-word topics)
    t = f"\"{topic}\"" if " " in topic.strip() else topic.strip()

    return [
        f'{t} "system design" {level_terms} architecture components relationships data flow{NEGATIVE}',
        f'{t} "system design" {level_terms} "request flow" "data flow"{NEGATIVE}',
        f'{t} {level_terms} backend architecture "load balancer" "api gateway" cache database queue{NEGATIVE}',
    ]


def discover_links(
    topic: str,
    level: str,
    max_links: int = 5,
    max_results_per_query: int = 12,
    allow_paywall: bool = True,
) -> list[str]:

    topic_terms = _topic_terms(topic)
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
                if not _contains_topic(topic_terms, url, title, body):
                    continue

                s = _score(title, body, level, url)
                candidates.append((s, url))

    candidates.sort(key=lambda x: x[0], reverse=True)

    out: list[str] = []
    seen = set()
    for s, url in candidates:
        if url in seen:
            continue
        seen.add(url)
        out.append(url)
        if len(out) >= max_links:
            break

    return out
