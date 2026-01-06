from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from readability import Document

import re
import time
import random

from playwright.sync_api import sync_playwright


DIAGRAM_HINTS = ["diagram", "architecture", "flow", "hld", "lld", "system design", "sequence"]
PAYWALL_HINTS = [
    "this post is for paid subscribers",
    "subscribe to continue",
    "sign in to read",
    "become a member",
    "purchase",
    "already a paid subscriber",
]


@dataclass
class ImageRef:
    src: str
    alt: Optional[str] = None
    caption: Optional[str] = None
    score: int = 0  # relevance score (higher = more likely diagram)


@dataclass
class PageContent:
    url: str
    title: Optional[str]
    text: str
    images: List[ImageRef]
    is_paywalled: bool
    diagram_score: int  # sum of image scores


def _clean_text(s: str) -> str:
    return " ".join(s.split())


def _extract_title(full_html: str) -> Optional[str]:
    try:
        soup = BeautifulSoup(full_html, "lxml")
        if soup.title and soup.title.string:
            return soup.title.string.strip()[:200]
    except Exception:
        return None
    return None


def _is_paywalled(text: str) -> bool:
    t = text.lower()
    return any(h in t for h in PAYWALL_HINTS)


def _image_relevance(img_src: str, alt: str, caption: str) -> int:
    score = 0
    blob = f"{img_src} {alt} {caption}".lower()

    # keyword signals
    for k in DIAGRAM_HINTS:
        if k in blob:
            score += 2

    # penalize obvious tiny/ui icons by filename hints
    if any(x in blob for x in ["sprite", "icon", "logo"]):
        score -= 2

    return score

def _get_img_src(img) -> str:
    # Try common lazy-load attributes first
    for attr in ["data-src", "data-lazy-src", "data-original", "data-url", "data-image", "data-img"]:
        v = (img.get(attr) or "").strip()
        if v:
            return v

    # srcset sometimes exists without src
    srcset = (img.get("srcset") or "").strip()
    if srcset:
        # take the first URL in srcset
        first = srcset.split(",")[0].strip().split(" ")[0]
        if first:
            return first

    # fallback to src
    return (img.get("src") or "").strip()

def normalize_medium_url(url: str) -> str:
    if "medium.com" in url and not url.endswith("/amp"):
        return url.rstrip("/") + "/amp"
    return url

def _via_jina_reader(url: str, headers: dict, timeout: int = 25) -> str:
    # Jina expects the original URL appended
    reader_url = "https://r.jina.ai/" + url
    r = requests.get(reader_url, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.text  # usually markdown-ish text


def _extract_image_urls_from_text(text: str, max_images: int = 12) -> list[str]:
    urls = set()

    # markdown image syntax: ![alt](url)
    for m in re.findall(r"!\[[^\]]*\]\((https?://[^)]+)\)", text):
        urls.add(m)

    # plain urls ending with image types
    for m in re.findall(r"(https?://[^\s)]+?\.(?:png|jpg|jpeg|webp|gif))", text, flags=re.IGNORECASE):
        urls.add(m)

    out = list(urls)
    return out[:max_images]

def _fetch_html_playwright(url: str, timeout_ms: int = 30000) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(1500)  # let content settle
        html = page.content()
        browser.close()
        return html


def scrape_url(url: str, max_text_chars: int = 12000, max_images: int = 12) -> PageContent:
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive",
    }

    session = requests.Session()
    used_browser = False
    #url = normalize_medium_url(url)
    #session = requests.Session()
    #used_jina = False

    last_err = None
    for attempt in range(3):
        try:
            # tiny jitter to avoid bot-pattern bursts
            time.sleep(0.5 + random.random())

            r = session.get(url, headers=headers, timeout=25)
            r.raise_for_status()
            full_html = r.text
            break
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    else:
        raise last_err



    title = _extract_title(full_html)
    
    # If we used Jina, we got reader-text not full HTML.
    # So we skip readability+BeautifulSoup path and return from here.
    """if used_jina:
        text = _clean_text(full_html)
        if len(text) > max_text_chars:
            text = text[:max_text_chars]

        paywalled = _is_paywalled(text)

        images: List[ImageRef] = []
        diagram_score = 0

        for img_url in _extract_image_urls_from_text(full_html, max_images=max_images):
            score = _image_relevance(img_url, "", "")
            images.append(ImageRef(src=img_url, alt=None, caption=None, score=score))
            diagram_score += max(score, 0)

        images.sort(key=lambda x: x.score, reverse=True)

        return PageContent(
            url=url,
            title=title,
            text=text,
            images=images,
            is_paywalled=paywalled,
            diagram_score=diagram_score,
        )
    """

    # OpenGraph image (often the main hero/diagram)
    og_img = None
    try:
        soup_full = BeautifulSoup(full_html, "lxml")
        meta = soup_full.find("meta", attrs={"property": "og:image"})
        if meta and meta.get("content"):
            og_img = meta["content"].strip()
    except Exception:
        pass

    # 1) readability isolates main article HTML
    doc = Document(full_html)
    main_html = doc.summary(html_partial=True)

    # 2) BeautifulSoup extracts clean text + images from the main content
    soup = BeautifulSoup(main_html, "lxml")

    # remove obvious noise
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = _clean_text(soup.get_text(" ", strip=True))

    # Fallback: if readability extracted junk (too short), use full page text
    if len(text) < 500:
        soup_full = BeautifulSoup(full_html, "lxml")
        for tag in soup_full(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()
        text = _clean_text(soup_full.get_text(" ", strip=True))

    if len(text) > max_text_chars:
        text = text[:max_text_chars]

    paywalled = _is_paywalled(text)

    images: List[ImageRef] = []
    diagram_score = 0

    # Add OpenGraph image (often the main hero/diagram)
    if og_img:
        images.append(ImageRef(src=urljoin(url, og_img), alt="og:image", caption=None, score=1))
        diagram_score += 1
    
    # Extract images from main article content
    for img in soup.find_all("img"):
        src = _get_img_src(img)

        if not src:
            continue

        full_src = urljoin(url, src)
        alt = (img.get("alt") or "").strip()[:300]

        caption = ""
        parent = img.parent
        if parent and parent.name == "figure":
            cap = parent.find("figcaption")
            if cap:
                caption = cap.get_text(" ", strip=True)[:300]

        score = _image_relevance(full_src, alt, caption)
        images.append(ImageRef(src=full_src, alt=alt or None, caption=caption or None, score=score))
        diagram_score += max(score, 0)

        if len(images) >= max_images:
            break

    # Sort images by relevance (most diagram-like first)
    images.sort(key=lambda x: x.score, reverse=True)

    return PageContent(
        url=url,
        title=title,
        text=text,
        images=images,
        is_paywalled=paywalled,
        diagram_score=diagram_score,
    )
