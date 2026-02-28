"""
Interview data scrapers - Glassdoor interview pages + LeetCode discussion board
"""

import os
import requests
import time
import random
from bs4 import BeautifulSoup
from typing import List, Dict
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env", override=True)
except ImportError:
    pass

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _serpapi_search(query: str, num: int = 8) -> List[Dict]:
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
    except Exception:
        return []


def scrape_glassdoor_interviews(company: str) -> List[Dict]:
    """Scrape Glassdoor interview pages for questions and experiences."""
    posts = []

    queries = [
        f'site:glassdoor.com/Interview "{company}" interview questions experience',
        f'glassdoor "{company}" interview process rounds difficulty',
        f'glassdoor "{company}" interview questions software engineer',
    ]

    for query in queries:
        results = _serpapi_search(query, num=6)
        for r in results:
            if company.lower() in (r["title"] + r["text"]).lower():
                posts.append({
                    "source": "glassdoor_interview",
                    "title": r["title"],
                    "text": r["text"],
                    "url": r["url"],
                    "score": 0,
                    "comments": [],
                })
        time.sleep(random.uniform(0.8, 1.5))

    return posts


def scrape_leetcode_discuss(company: str) -> List[Dict]:
    """Scrape LeetCode discussion board for interview experiences."""
    posts = []

    queries = [
        f'site:leetcode.com/discuss "{company}" interview experience',
        f'site:leetcode.com/discuss "{company}" OA online assessment',
        f'site:leetcode.com/discuss "{company}" interview questions',
    ]

    for query in queries:
        results = _serpapi_search(query, num=6)
        for r in results:
            if company.lower() in (r["title"] + r["text"]).lower():
                posts.append({
                    "source": "leetcode_discuss",
                    "title": r["title"],
                    "text": r["text"],
                    "url": r["url"],
                    "score": 0,
                    "comments": [],
                })
        time.sleep(random.uniform(0.8, 1.5))

    return posts


def scrape_interview_data(company: str) -> List[Dict]:
    """Combine Glassdoor interview pages + LeetCode discussion data."""
    posts = []

    gd = scrape_glassdoor_interviews(company)
    posts.extend(gd)

    lc = scrape_leetcode_discuss(company)
    posts.extend(lc)

    return posts
