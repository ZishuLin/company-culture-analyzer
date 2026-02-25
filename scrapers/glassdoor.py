"""
Glassdoor scraper - uses Google search snippets to extract review text.
No direct Glassdoor scraping (they block it), but search engine caches work.
"""

import requests
import time
import random
import re
from bs4 import BeautifulSoup
from typing import List, Dict


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def scrape_glassdoor_snippets(company_name: str) -> List[Dict]:
    """
    Search for Glassdoor reviews via DuckDuckGo HTML search.
    Extracts snippets without hitting Glassdoor directly.
    """
    reviews = []
    query = f'site:glassdoor.com "{company_name}" reviews'
    url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        for result in soup.select(".result__body")[:15]:
            snippet_el = result.select_one(".result__snippet")
            title_el = result.select_one(".result__title")
            link_el = result.select_one(".result__url")

            if not snippet_el:
                continue

            snippet = snippet_el.get_text(strip=True)
            title = title_el.get_text(strip=True) if title_el else ""
            link = link_el.get_text(strip=True) if link_el else ""

            if company_name.lower() not in (snippet + title).lower():
                continue

            reviews.append({
                "source": "glassdoor",
                "title": title,
                "text": snippet,
                "url": link,
                "score": 0,
            })

        time.sleep(random.uniform(1, 2))
    except Exception:
        pass

    return reviews


def scrape_indeed_reviews(company_name: str) -> List[Dict]:
    """Search for Indeed company reviews via DuckDuckGo."""
    reviews = []
    query = f'site:indeed.com "{company_name}" reviews "work-life balance"'
    url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        for result in soup.select(".result__body")[:10]:
            snippet_el = result.select_one(".result__snippet")
            if not snippet_el:
                continue
            snippet = snippet_el.get_text(strip=True)
            if company_name.lower() not in snippet.lower():
                continue
            reviews.append({
                "source": "indeed_reviews",
                "title": "",
                "text": snippet,
                "url": "",
                "score": 0,
            })

        time.sleep(random.uniform(1, 2))
    except Exception:
        pass

    return reviews
