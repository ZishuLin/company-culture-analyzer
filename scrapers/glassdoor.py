"""
Glassdoor/Indeed scraper - uses SerpAPI for reliable search results.
Free tier: 100 searches/month at serpapi.com
"""

import os
import re
import requests
import time
import random
from bs4 import BeautifulSoup
from pathlib import Path
from typing import List, Dict

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env", override=True)
except ImportError:
    pass

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def _serpapi_search(query: str, num: int = 10) -> List[Dict]:
    """Search via SerpAPI Google Search."""
    key = os.environ.get("SERPAPI_KEY", "").strip()
    if not key:
        return []
    try:
        resp = requests.get(
            "https://serpapi.com/search",
            params={"q": query, "api_key": key, "num": num, "engine": "google"},
            timeout=15,
        )
        resp.raise_for_status()
        results = []
        for item in resp.json().get("organic_results", []):
            snippet = item.get("snippet", "")
            title = item.get("title", "")
            link = item.get("link", "")
            if snippet:
                results.append({"title": title, "text": snippet, "url": link})
        return results
    except Exception as e:
        print(f"[SerpAPI error] {e}")
        return []


def _bing_search(query: str, num: int = 10) -> List[Dict]:
    """Fallback: scrape Bing search results."""
    results = []
    url = f"https://www.bing.com/search?q={requests.utils.quote(query)}&count={num}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        for item in soup.select(".b_algo")[:num]:
            snippet_el = item.select_one(".b_caption p")
            title_el = item.select_one("h2")
            if snippet_el:
                results.append({
                    "title": title_el.get_text(strip=True) if title_el else "",
                    "text": snippet_el.get_text(strip=True),
                    "url": "",
                })
        time.sleep(random.uniform(1.0, 2.0))
    except Exception:
        pass
    return results


def _search(query: str, num: int = 10) -> List[Dict]:
    """Try SerpAPI first, then Bing."""
    results = _serpapi_search(query, num)
    if results:
        return results
    return _bing_search(query, num)


def _filter_relevant(results: List[Dict], company: str) -> List[Dict]:
    return [r for r in results if company.lower() in (r["title"] + r["text"]).lower()]


def _fetch_glassdoor_page(url: str) -> str:
    """Fetch full Glassdoor review page content."""
    try:
        resp = requests.get(url, headers={
            **HEADERS,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }, timeout=12)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        # Remove scripts and nav
        for el in soup.select("script, style, nav, header, footer, .gdGrid"):
            el.decompose()
        # Try to get review text blocks
        reviews = []
        for el in soup.select("[data-test='review-text'], .reviewText, .v2__EIReviewDetailsV2__fullWidth, p"):
            text = el.get_text(separator=" ", strip=True)
            if len(text) > 50:
                reviews.append(text)
        if reviews:
            return " | ".join(reviews[:10])
        # Fallback to body text
        return soup.get_text(separator=" ", strip=True)[:3000]
    except Exception:
        return ""


def scrape_glassdoor_snippets(company: str) -> List[Dict]:
    """Scrape Glassdoor snippets via SerpAPI (multiple query angles)."""
    reviews = []
    seen = set()

    queries = [
        f'site:glassdoor.com "{company}" reviews work life balance culture',
        f'glassdoor "{company}" employee reviews management compensation',
        f'glassdoor "{company}" pros cons salary benefits',
        f'glassdoor "{company}" work culture career growth',
        f'"{company}" glassdoor review burnout stress remote',
    ]

    for query in queries:
        raw = _search(query, num=8)
        for r in _filter_relevant(raw, company):
            key = r["text"][:80]
            if key in seen:
                continue
            seen.add(key)
            reviews.append({
                "source": "glassdoor",
                "title": r["title"],
                "text": r["text"],
                "url": r.get("url", ""),
                "score": 0,
                "comments": [],
            })
        time.sleep(random.uniform(0.5, 1.0))

    return reviews


def scrape_glassdoor_full_reviews(company: str, limit: int = 5) -> List[Dict]:
    """Fetch full Glassdoor review pages for deeper analysis."""
    posts = []

    # Get URLs via SerpAPI
    query = f'site:glassdoor.com/Reviews "{company}" reviews'
    results = _serpapi_search(query, num=8)

    urls = []
    for r in results:
        url = r.get("url", "")
        if "glassdoor.com" in url and url not in urls:
            urls.append(url)

    for url in urls[:limit]:
        full_text = _fetch_glassdoor_page(url)
        if full_text and company.lower() in full_text.lower():
            posts.append({
                "source": "glassdoor_full",
                "title": f"Glassdoor Reviews: {company}",
                "text": full_text[:2000],
                "url": url,
                "score": 0,
                "comments": [],
            })
        time.sleep(random.uniform(1.5, 2.5))

    return posts


def scrape_indeed_reviews(company: str) -> List[Dict]:
    """Scrape Indeed snippets via SerpAPI (multiple query angles)."""
    reviews = []
    seen = set()

    queries = [
        f'site:indeed.com "{company}" company reviews',
        f'indeed "{company}" employee reviews work culture management',
        f'indeed "{company}" salary compensation benefits review',
        f'indeed "{company}" pros cons work environment',
    ]

    for query in queries:
        raw = _search(query, num=6)
        for r in _filter_relevant(raw, company):
            key = r["text"][:80]
            if key in seen:
                continue
            seen.add(key)
            reviews.append({
                "source": "indeed_reviews",
                "title": r["title"],
                "text": r["text"],
                "url": r.get("url", ""),
                "score": 0,
                "comments": [],
            })
        time.sleep(random.uniform(0.5, 1.0))

    return reviews