"""
1point3acres scraper - searches for company interview experiences and work culture posts
Site: https://www.1point3acres.com/bbs/
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
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.1point3acres.com/bbs/",
}

BASE_URL = "https://www.1point3acres.com/bbs"

COMPANY_ALIASES = {
    "google": ["谷歌", "Google"],
    "meta": ["脸书", "Meta", "Facebook", "FB"],
    "facebook": ["脸书", "Meta", "Facebook", "FB"],
    "amazon": ["亚马逊", "Amazon", "AMZ"],
    "microsoft": ["微软", "Microsoft", "MS", "MSFT"],
    "apple": ["苹果", "Apple"],
    "netflix": ["奈飞", "Netflix"],
    "uber": ["优步", "Uber"],
    "airbnb": ["爱彼迎", "Airbnb"],
    "twitter": ["推特", "Twitter", "X"],
    "linkedin": ["领英", "LinkedIn"],
    "salesforce": ["Salesforce", "SF"],
    "shopify": ["Shopify"],
    "stripe": ["Stripe"],
    "openai": ["OpenAI"],
    "bytedance": ["字节跳动", "ByteDance", "字节"],
    "tiktok": ["TikTok", "字节跳动", "字节"],
    "alibaba": ["阿里巴巴", "阿里", "Alibaba"],
    "tencent": ["腾讯", "Tencent"],
    "baidu": ["百度", "Baidu"],
    "nvidia": ["英伟达", "NVIDIA", "NVDA"],
    "intel": ["英特尔", "Intel"],
    "qualcomm": ["高通", "Qualcomm"],
    "bloomberg": ["彭博", "Bloomberg"],
    "goldman sachs": ["高盛", "Goldman", "GS"],
    "jp morgan": ["摩根大通", "JPM", "JP Morgan"],
    "morgan stanley": ["摩根士丹利", "MS"],
    "two sigma": ["Two Sigma"],
    "citadel": ["城堡", "Citadel"],
    "jane street": ["Jane Street"],
    "de shaw": ["DE Shaw"],
    "palantir": ["Palantir"],
    "databricks": ["Databricks"],
    "snowflake": ["Snowflake"],
    "oracle": ["甲骨文", "Oracle"],
    "ibm": ["IBM"],
    "cisco": ["思科", "Cisco"],
    "adobe": ["Adobe"],
    "vmware": ["VMware"],
    "sap": ["SAP"],
}

# Interview-specific search keywords
INTERVIEW_KEYWORDS = ["面经", "interview", "OA", "onsite", "intern 面经", "SDE 面经"]


def get_search_terms(company: str) -> List[str]:
    key = company.lower().strip()
    aliases = COMPANY_ALIASES.get(key, [company])
    if company not in aliases:
        aliases = [company] + aliases
    return aliases


def translate_to_english(texts: List[str]) -> List[str]:
    """Use Gemini to translate Chinese text to English. Returns originals if no API key."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        return texts

    def has_chinese(text):
        return any('\u4e00' <= c <= '\u9fff' for c in text)

    indices_to_translate = [i for i, t in enumerate(texts) if has_chinese(t)]
    if not indices_to_translate:
        return texts

    result = list(texts)
    batch = [texts[i] for i in indices_to_translate]
    combined = "\n---\n".join(batch[:20])

    prompt = f"""Translate the following Chinese texts to English.
Return ONLY the translations separated by "---", in the same order.
Do not add any explanation or numbering.

{combined}"""

    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048},
            },
            timeout=20,
        )
        resp.raise_for_status()
        translated_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        translations = [t.strip() for t in translated_text.split("---")]
        for i, idx in enumerate(indices_to_translate[:len(translations)]):
            result[idx] = translations[i]
    except Exception:
        pass

    return result


def scrape_yimusan(company: str, limit: int = 20) -> List[Dict]:
    """Search 1point3acres for work culture posts about a company."""
    posts = []
    seen_urls = set()
    search_terms = get_search_terms(company)

    # Search general posts via SerpAPI
    serp_posts = _serpapi_yimusan(company, search_terms, interview_mode=False)
    for p in serp_posts:
        if p["url"] not in seen_urls:
            posts.append(p)
            seen_urls.add(p["url"])

    # Direct search as fallback
    if len(posts) < 5:
        for term in search_terms[:2]:
            direct = _direct_search(term, company, seen_urls)
            for p in direct:
                posts.append(p)
                seen_urls.add(p["url"])
            time.sleep(random.uniform(1.5, 2.5))

    # Translate Chinese content to English
    if posts:
        texts = [p["text"] for p in posts]
        translated = translate_to_english(texts)
        for i, post in enumerate(posts):
            post["text"] = translated[i]

    return posts[:limit]


def scrape_yimusan_interview(company: str, limit: int = 15) -> List[Dict]:
    """Search 1point3acres specifically for interview experience posts."""
    posts = []
    seen_urls = set()
    search_terms = get_search_terms(company)

    # Search using interview-specific keywords
    serp_posts = _serpapi_yimusan(company, search_terms, interview_mode=True)
    for p in serp_posts:
        if p["url"] not in seen_urls:
            p["source"] = "1point3acres_interview"
            posts.append(p)
            seen_urls.add(p["url"])

    # Direct search as fallback
    if len(posts) < 5:
        for term in search_terms[:1]:
            for kw in INTERVIEW_KEYWORDS[:2]:
                query = f"{term} {kw}"
                direct = _direct_search(query, company, seen_urls)
                for p in direct:
                    p["source"] = "1point3acres_interview"
                    posts.append(p)
                    seen_urls.add(p["url"])
                time.sleep(random.uniform(1.5, 2.0))

    # Translate Chinese content to English
    if posts:
        texts = [p["text"] for p in posts]
        translated = translate_to_english(texts)
        for i, post in enumerate(posts):
            post["text"] = translated[i]

    return posts[:limit]


def _serpapi_yimusan(company: str, search_terms: List[str], interview_mode: bool = False) -> List[Dict]:
    key = os.environ.get("SERPAPI_KEY", "").strip()
    if not key:
        return []

    results = []
    terms_to_search = search_terms[:2]

    for term in terms_to_search:
        if interview_mode:
            queries = [
                f'site:1point3acres.com "{term}" 面经',
                f'site:1point3acres.com "{term}" interview experience',
            ]
        else:
            queries = [f'site:1point3acres.com "{term}"']

        for query in queries:
            try:
                resp = requests.get(
                    "https://serpapi.com/search",
                    params={"q": query, "api_key": key, "num": 8, "engine": "google"},
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("organic_results", []):
                    snippet = item.get("snippet", "")
                    title = item.get("title", "")
                    link = item.get("link", "")
                    if snippet and link:
                        results.append({
                            "source": "1point3acres",
                            "title": title,
                            "text": f"{title}. {snippet}",
                            "url": link,
                            "score": 0,
                            "comments": [],
                        })
                time.sleep(1)
            except Exception:
                continue

    return results


def _direct_search(term: str, company: str, seen_urls: set) -> List[Dict]:
    posts = []
    try:
        search_url = f"{BASE_URL}/search.php?searchsubmit=yes&srchtxt={requests.utils.quote(term)}&srchtype=1"
        resp = requests.get(search_url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        for item in soup.select(".pbw, li.pbw, .srchres")[:10]:
            title_el = item.select_one("h3 a, .xst, a.s")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            url = title_el.get("href", "")
            if url and not url.startswith("http"):
                url = BASE_URL + "/" + url.lstrip("/")
            if not url or url in seen_urls:
                continue

            summary_el = item.select_one(".xg1, .xi1, p")
            summary = summary_el.get_text(strip=True)[:300] if summary_el else ""

            posts.append({
                "source": "1point3acres",
                "title": title,
                "text": f"{title}. {summary}",
                "url": url,
                "score": 0,
                "comments": [],
            })
    except Exception:
        pass
    return posts