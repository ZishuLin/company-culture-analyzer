"""
Culture analyzer - uses Gemini API to analyze sentiment and extract themes
from collected text data. Falls back to keyword-based analysis if no API key.
"""

import os
import re
import json
import requests
from typing import List, Dict
from collections import defaultdict
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env", override=True)
except ImportError:
    pass

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

INTERVIEW_SOURCES = {"glassdoor_interview", "leetcode_discuss", "1point3acres_interview"}

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
        "technical screen", "system design", "oa", "online assessment",
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


def _get_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "").strip()


def _clean(text: str) -> str:
    return text.replace('"', "'").replace('\\', '').replace('\n', ' ').strip()


def analyze_with_gemini(company: str, texts: List[str], all_posts: List[Dict] = None) -> Dict:
    key = _get_key()
    if not key or not texts:
        return {}

    all_posts = all_posts or []

    # Build general reviews section
    general_texts = []
    interview_texts = []
    for post in all_posts:
        text = post.get("text", "")
        if not text:
            continue
        cleaned = _clean(text)
        if post.get("source") in INTERVIEW_SOURCES:
            interview_texts.append(cleaned)
        else:
            general_texts.append(cleaned)

    general_section = "\n---\n".join(general_texts[:30])
    interview_section = "\n---\n".join(interview_texts[:15]) if interview_texts else "No interview data found."

    prompt = f"""Analyze employee reviews and interview experiences about {company}.

=== EMPLOYEE REVIEWS (work culture, compensation, management, career) ===
{general_section[:3500]}

=== INTERVIEW EXPERIENCES (rounds, difficulty, OA, H1B, pair programming) ===
{interview_section[:2000]}

Based on ALL the above, return ONLY this JSON structure with no markdown:
{{"work_life_balance":{{"score":7,"summary":"one sentence based on reviews","evidence":["example1","example2"]}},"management":{{"score":7,"summary":"one sentence","evidence":["example1","example2"]}},"career_growth":{{"score":7,"summary":"one sentence","evidence":["example1","example2"]}},"compensation":{{"score":7,"summary":"one sentence","evidence":["example1","example2"]}},"culture":{{"score":7,"summary":"one sentence","evidence":["example1","example2"]}},"interview":{{"score":7,"summary":"describe rounds, difficulty, OA, H1B if available","evidence":["example1","example2"]}},"overall_verdict":"2-3 sentence summary","red_flags":["concern1","concern2"],"green_flags":["positive1","positive2"],"data_quality":"medium"}}"""

    try:
        resp = requests.post(
            f"{API_URL}?key={key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 4096,
                    "responseMimeType": "application/json",
                },
            },
            timeout=30,
        )
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        text = text.strip()
        if "```" in text:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
            if match:
                text = match.group(1).strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]
        return json.loads(text)
    except Exception as e:
        print(f"[Gemini error] {e}")
        return {}


def keyword_analysis(texts: List[str]) -> Dict:
    combined = " ".join(texts).lower()
    results = {}
    for topic, keywords in TOPIC_KEYWORDS.items():
        mentions = sum(1 for kw in keywords if kw in combined)
        pos = sum(1 for w in POSITIVE_WORDS if w in combined)
        neg = sum(1 for w in NEGATIVE_WORDS if w in combined)
        score = 5 if mentions == 0 else round(3 + (pos / max(pos + neg, 1)) * 6)
        results[topic] = {"score": score, "summary": f"Based on {mentions} keyword mentions.", "evidence": []}
    results["overall_verdict"] = "Analysis based on keyword frequency (no Gemini API key)."
    results["red_flags"] = []
    results["green_flags"] = []
    results["data_quality"] = "low"
    return results


def analyze_company(company: str, all_posts: List[Dict]) -> Dict:
    if not all_posts:
        return {"error": "No data found for this company.", "total_sources": 0}

    texts = []
    for post in all_posts:
        if post.get("text"):
            texts.append(post["text"])
        for comment in post.get("comments", []):
            if comment.get("text"):
                texts.append(comment["text"])

    key = _get_key()
    analysis = analyze_with_gemini(company, texts, all_posts=all_posts) if key else {}

    if not analysis:
        analysis = keyword_analysis(texts)

    source_counts = defaultdict(int)
    for post in all_posts:
        source_counts[post.get("source", "unknown")] += 1

    analysis["metadata"] = {
        "company": company,
        "total_posts": len(all_posts),
        "total_text_samples": len(texts),
        "sources": dict(source_counts),
        "used_ai": bool(key and analysis.get("data_quality") and analysis.get("data_quality") != "low"),
    }

    return analysis