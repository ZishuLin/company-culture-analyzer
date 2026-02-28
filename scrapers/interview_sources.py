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


def _fetch_leetcode_post(url: str) -> str:
    """Fetch full content of a LeetCode discuss post via GraphQL API."""
    import re
    try:
        match = re.search(r'/(\d+)/', url)
        if not match:
            return ""
        post_id = match.group(1)
        resp = requests.post(
            "https://leetcode.com/graphql",
            json={"query": "query { topic(id: " + post_id + ") { title post { content } } }"},
            headers={
                "Content-Type": "application/json",
                "Referer": "https://leetcode.com/discuss/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
            timeout=10,
        )
        if resp.status_code != 200:
            return ""
        data = resp.json()
        topic = data.get("data", {}).get("topic", {})
        title = topic.get("title", "")
        content_text = topic.get("post", {}).get("content", "")
        # Strip HTML tags
        import re as re2
        content_text = re2.sub(r"<[^>]+>", " ", content_text)
        return f"{title}. {content_text}"[:3000]
    except Exception:
        return ""


def _fetch_yimusan_post(url: str) -> str:
    """Fetch full content of a 1point3acres post."""
    try:
        resp = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://www.1point3acres.com/bbs/",
        }, timeout=10)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        # 1point3acres post content (first post / floor 1)
        post_el = soup.select_one(".t_f, .postmessage, #postmessage_")
        if not post_el:
            post_el = soup.select(".t_f")
            post_el = post_el[0] if post_el else None
        if post_el:
            return post_el.get_text(separator=" ", strip=True)[:2000]
        return ""
    except Exception:
        return ""


def scrape_leetcode_full_posts(company: str, limit: int = 10) -> List[Dict]:
    """Search LeetCode discuss and fetch full post content for detailed interview info."""
    key = os.environ.get("SERPAPI_KEY", "").strip()
    if not key:
        return []

    # Get URLs from SerpAPI
    urls = []
    for query in [
        f'site:leetcode.com/discuss "{company}" interview experience',
        f'site:leetcode.com/discuss "{company}" OA online assessment questions',
    ]:
        try:
            resp = requests.get(
                "https://serpapi.com/search",
                params={"q": query, "api_key": key, "num": 5, "engine": "google"},
                timeout=15,
            )
            resp.raise_for_status()
            for item in resp.json().get("organic_results", []):
                link = item.get("link", "")
                if "leetcode.com/discuss" in link and link not in urls:
                    urls.append(link)
            time.sleep(1)
        except Exception:
            continue

    # Fetch full content of each post
    posts = []
    for url in urls[:limit]:
        full_text = _fetch_leetcode_post(url)
        if full_text and company.lower() in full_text.lower():
            posts.append({
                "source": "leetcode_discuss_full",
                "title": f"LeetCode Interview Experience: {company}",
                "text": full_text,
                "url": url,
                "score": 0,
                "comments": [],
            })
        time.sleep(random.uniform(1.0, 2.0))

    return posts


def scrape_yimusan_full_posts(company: str, limit: int = 8) -> List[Dict]:
    """Search 1point3acres and fetch full post content for detailed interview info."""
    key = os.environ.get("SERPAPI_KEY", "").strip()
    if not key:
        return []

    # Company aliases for Chinese search
    from scrapers.yimusan import get_search_terms
    search_terms = get_search_terms(company)

    urls = []
    for term in search_terms[:2]:
        for query in [
            f'site:1point3acres.com "{term}" 面经',
            f'site:1point3acres.com "{term}" interview',
        ]:
            try:
                resp = requests.get(
                    "https://serpapi.com/search",
                    params={"q": query, "api_key": key, "num": 5, "engine": "google"},
                    timeout=15,
                )
                resp.raise_for_status()
                for item in resp.json().get("organic_results", []):
                    link = item.get("link", "")
                    if "1point3acres.com" in link and link not in urls:
                        urls.append(link)
                time.sleep(1)
            except Exception:
                continue

    # Fetch full content
    posts = []
    for url in urls[:limit]:
        full_text = _fetch_yimusan_post(url)
        if full_text:
            posts.append({
                "source": "1point3acres_full",
                "title": f"1point3acres Interview Experience: {company}",
                "text": full_text,
                "url": url,
                "score": 0,
                "comments": [],
            })
        time.sleep(random.uniform(1.5, 2.5))

    return posts


def scrape_full_interview_posts(company: str) -> List[Dict]:
    """Fetch full interview post content from LeetCode (1point3acres requires login)."""
    return scrape_leetcode_full_posts(company)