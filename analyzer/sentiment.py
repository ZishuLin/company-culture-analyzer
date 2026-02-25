"""
Culture analyzer - uses Gemini API to analyze sentiment and extract themes
from collected text data. Falls back to keyword-based analysis if no API key.
"""

import os
import json
import re
import requests
from typing import List, Dict
from collections import defaultdict

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

# Keyword lists for fallback analysis
TOPIC_KEYWORDS = {
    "work_life_balance": [
        "work life balance", "work-life", "overtime", "crunch", "long hours",
        "weekend", "burnout", "flexible", "remote", "wfh", "hours", "overworked",
        "time off", "vacation", "pto", "always on",
    ],
    "management": [
        "manager", "management", "leadership", "micromanage", "cto", "vp",
        "director", "boss", "supervisor", "exec", "senior leadership",
        "top down", "trust", "autonomy", "empowered",
    ],
    "career_growth": [
        "promotion", "career growth", "learning", "mentorship", "skill",
        "advance", "stuck", "plateau", "opportunity", "development",
        "training", "conference", "education", "path",
    ],
    "compensation": [
        "salary", "pay", "compensation", "bonus", "equity", "stock",
        "rsu", "underpaid", "raise", "offer", "benefits", "package",
    ],
    "culture": [
        "culture", "diverse", "inclusion", "toxic", "politics", "drama",
        "team", "collaborative", "friendly", "supportive", "cold",
        "bureaucracy", "startup", "corporate", "flat",
    ],
    "interview": [
        "interview", "hiring", "leetcode", "onsite", "take home",
        "recruiter", "process", "rounds", "offer", "rejection",
        "technical screen", "system design",
    ],
}

POSITIVE_WORDS = {
    "great", "excellent", "amazing", "good", "love", "best", "awesome",
    "fantastic", "wonderful", "positive", "happy", "recommend", "supportive",
    "collaborative", "flexible", "transparent", "fair", "respect",
}

NEGATIVE_WORDS = {
    "bad", "terrible", "awful", "worst", "hate", "toxic", "horrible",
    "avoid", "nightmare", "burnout", "overworked", "underpaid", "layoff",
    "fired", "micromanage", "political", "stressful", "chaotic", "poor",
}


def analyze_with_gemini(company: str, texts: List[str]) -> Dict:
    """Use Gemini to do deep analysis of collected text."""
    if not GEMINI_API_KEY or not texts:
        return {}

    combined = "\n---\n".join(texts[:30])  # limit tokens

    prompt = f"""Analyze these employee reviews and discussions about {company}.

<texts>
{combined[:6000]}
</texts>

Return a JSON object with this exact structure:
{{
  "work_life_balance": {{
    "score": <1-10>,
    "summary": "<one sentence>",
    "evidence": ["<quote or paraphrase>", "<quote or paraphrase>"]
  }},
  "management": {{
    "score": <1-10>,
    "summary": "<one sentence>",
    "evidence": ["<quote or paraphrase>", "<quote or paraphrase>"]
  }},
  "career_growth": {{
    "score": <1-10>,
    "summary": "<one sentence>",
    "evidence": ["<quote or paraphrase>", "<quote or paraphrase>"]
  }},
  "compensation": {{
    "score": <1-10>,
    "summary": "<one sentence>",
    "evidence": ["<quote or paraphrase>", "<quote or paraphrase>"]
  }},
  "culture": {{
    "score": <1-10>,
    "summary": "<one sentence>",
    "evidence": ["<quote or paraphrase>", "<quote or paraphrase>"]
  }},
  "interview": {{
    "score": <1-10>,
    "summary": "<one sentence>",
    "evidence": ["<quote or paraphrase>", "<quote or paraphrase>"]
  }},
  "overall_verdict": "<2-3 sentence honest summary of what it's really like to work there>",
  "red_flags": ["<specific concern>", "<specific concern>"],
  "green_flags": ["<specific positive>", "<specific positive>"],
  "data_quality": "<low|medium|high> - based on how much relevant data was found"
}}

Be honest and specific. If data is insufficient, say so in data_quality.
Return valid JSON only, no markdown."""

    try:
        resp = requests.post(
            f"{API_URL}?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048},
            },
            timeout=30,
        )
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])
        return json.loads(text.strip())
    except Exception:
        return {}


def keyword_analysis(texts: List[str]) -> Dict:
    """Fallback: keyword-based analysis when no Gemini key."""
    combined = " ".join(texts).lower()
    results = {}

    for topic, keywords in TOPIC_KEYWORDS.items():
        mentions = sum(1 for kw in keywords if kw in combined)
        # Count positive/negative context around topic keywords
        pos = sum(1 for w in POSITIVE_WORDS if w in combined)
        neg = sum(1 for w in NEGATIVE_WORDS if w in combined)

        if mentions == 0:
            score = 5  # neutral if not mentioned
        else:
            ratio = pos / max(pos + neg, 1)
            score = round(3 + ratio * 6)  # 3-9 range

        results[topic] = {
            "score": score,
            "summary": f"Based on {mentions} keyword mentions.",
            "evidence": [],
        }

    results["overall_verdict"] = "Analysis based on keyword frequency (no Gemini API key)."
    results["red_flags"] = []
    results["green_flags"] = []
    results["data_quality"] = "low"
    return results


def analyze_company(company: str, all_posts: List[Dict]) -> Dict:
    """Main analysis function."""
    if not all_posts:
        return {
            "error": "No data found for this company.",
            "total_sources": 0,
        }

    texts = []
    for post in all_posts:
        if post.get("text"):
            texts.append(post["text"])
        for comment in post.get("comments", []):
            if comment.get("text"):
                texts.append(comment["text"])

    # Try Gemini first, fall back to keywords
    if GEMINI_API_KEY:
        analysis = analyze_with_gemini(company, texts)
    else:
        analysis = {}

    if not analysis:
        analysis = keyword_analysis(texts)

    # Add metadata
    source_counts = defaultdict(int)
    for post in all_posts:
        source_counts[post.get("source", "unknown")] += 1

    analysis["metadata"] = {
        "company": company,
        "total_posts": len(all_posts),
        "total_text_samples": len(texts),
        "sources": dict(source_counts),
        "used_ai": bool(GEMINI_API_KEY and analysis.get("data_quality")),
    }

    return analysis
