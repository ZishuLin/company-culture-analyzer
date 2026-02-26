"""
Glassdoor/Indeed scraper - uses SerpAPI for reliable search results.
Free tier: 100 searches/month at serpapi.com
"""

import os
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
            params={
                "q": query,
                "api_key": key,
                "num": num,
                "engine": "google",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("organic_results", []):
            snippet = item.get("snippet", "")
            title = item.get("title", "")
            if snippet:
                results.append({"title": title, "text": snippet})
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
                })
        time.sleep(random.uniform(1.0, 2.0))
    except Exception:
        pass
    return results


def _duckduckgo_search(query: str, num: int = 10) -> List[Dict]:
    """Fallback: scrape DuckDuckGo HTML results."""
    results = []
    url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        for item in soup.select(".result__body")[:num]:
            snippet_el = item.select_one(".result__snippet")
            title_el = item.select_one(".result__title")
            if snippet_el:
                results.append({
                    "title": title_el.get_text(strip=True) if title_el else "",
                    "text": snippet_el.get_text(strip=True),
                })
        time.sleep(random.uniform(1.0, 2.0))
    except Exception:
        pass
    return results


def _search(query: str, num: int = 10) -> List[Dict]:
    """Try SerpAPI first, then Bing, then DuckDuckGo."""
    results = _serpapi_search(query, num)
    if results:
        return results
    results = _bing_search(query, num)
    if results:
        return results
    return _duckduckgo_search(query, num)


def _filter_relevant(results: List[Dict], company: str) -> List[Dict]:
    return [
        r for r in results
        if company.lower() in (r["title"] + r["text"]).lower()
    ]


def scrape_glassdoor_snippets(company: str) -> List[Dict]:
    reviews = []
    queries = [
        f'site:glassdoor.com "{company}" reviews work life balance culture',
        f'glassdoor "{company}" employee reviews management compensation',
    ]
    for query in queries:
        raw = _search(query, num=8)
        for r in _filter_relevant(raw, company):
            reviews.append({
                "source": "glassdoor",
                "title": r["title"],
                "text": r["text"],
                "url": "",
                "score": 0,
                "comments": [],
            })
    return reviews


def scrape_indeed_reviews(company: str) -> List[Dict]:
    reviews = []
    queries = [
        f'site:indeed.com "{company}" company reviews',
        f'indeed "{company}" employee reviews work culture management',
    ]
    for query in queries:
        raw = _search(query, num=6)
        for r in _filter_relevant(raw, company):
            reviews.append({
                "source": "indeed_reviews",
                "title": r["title"],
                "text": r["text"],
                "url": "",
                "score": 0,
                "comments": [],
            })
    return reviews