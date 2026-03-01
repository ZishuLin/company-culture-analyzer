"""
Culture analyzer - uses Gemini API (with Groq fallback) to analyze sentiment
and extract themes from collected text data.
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
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

INTERVIEW_SOURCES = {
    "glassdoor_interview", "leetcode_discuss", "1point3acres_interview",
    "leetcode_discuss_full", "1point3acres_full"
}

TOPIC_KEYWORDS = {
    "work_life_balance": ["work life balance", "work-life", "overtime", "burnout", "flexible", "remote", "hours", "vacation", "pto"],
    "management": ["manager", "management", "leadership", "micromanage", "boss", "director", "trust", "autonomy"],
    "career_growth": ["promotion", "career growth", "learning", "mentorship", "advance", "stuck", "opportunity", "development"],
    "compensation": ["salary", "pay", "compensation", "bonus", "equity", "stock", "rsu", "underpaid", "raise", "benefits"],
    "culture": ["culture", "diverse", "inclusion", "toxic", "team", "collaborative", "friendly", "bureaucracy"],
    "interview": ["interview", "hiring", "leetcode", "onsite", "take home", "recruiter", "rounds", "oa", "online assessment"],
}

POSITIVE_WORDS = {"great", "excellent", "amazing", "good", "love", "best", "awesome", "fantastic", "positive", "happy", "recommend", "supportive", "flexible", "fair"}
NEGATIVE_WORDS = {"bad", "terrible", "awful", "worst", "hate", "toxic", "horrible", "avoid", "burnout", "overworked", "underpaid", "layoff", "micromanage", "stressful", "chaotic"}


def _get_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "").strip()


def _get_groq_key() -> str:
    return os.environ.get("GROQ_API_KEY", "").strip()


def _clean(text: str) -> str:
    return text.replace('"', "'").replace('\\', '').replace('\n', ' ').strip()


def _parse_json(text: str) -> Dict:
    """Parse JSON with multiple fallback strategies."""
    text = text.strip()
    # Strip markdown fences
    if "```" in text:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            text = m.group(1).strip()
    # Extract JSON object boundaries
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        text = text[start:end]
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fix unescaped control characters inside strings
    cleaned = ""
    in_string = False
    i = 0
    while i < len(text):
        c = text[i]
        if c == '"' and (i == 0 or text[i-1] != '\\'):
            in_string = not in_string
            cleaned += c
        elif in_string and c in '\n\r\t':
            cleaned += ' '
        else:
            cleaned += c
        i += 1
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {}


def _build_prompt(company: str, general_section: str, interview_section: str) -> str:
    return (
        f"Analyze employee reviews and interview experiences about {company}.\n\n"
        f"=== EMPLOYEE REVIEWS (work culture, compensation, management, career) ===\n"
        f"{general_section[:3500]}\n\n"
        f"=== INTERVIEW EXPERIENCES (LeetCode, Glassdoor, 1point3acres posts) ===\n"
        f"{interview_section[:2500]}\n\n"
        f"Based on ALL the above, return ONLY this JSON structure with no markdown:\n"
        f'{{"work_life_balance":{{"score":7,"summary":"one sentence based on reviews","evidence":["example1","example2"]}},'
        f'"management":{{"score":7,"summary":"one sentence","evidence":["example1","example2"]}},'
        f'"career_growth":{{"score":7,"summary":"one sentence","evidence":["example1","example2"]}},'
        f'"compensation":{{"score":7,"summary":"one sentence","evidence":["example1","example2"]}},'
        f'"culture":{{"score":7,"summary":"one sentence","evidence":["example1","example2"]}},'
        f'"interview":{{"score":7,"summary":"List specific rounds and question types. Include OA difficulty, pair programming details, system design topics if mentioned.","evidence":["specific round or question type","another detail"]}},'
        f'"overall_verdict":"2-3 sentence summary",'
        f'"red_flags":["concern1","concern2"],'
        f'"green_flags":["positive1","positive2"],'
        f'"data_quality":"medium"}}'
    )


def analyze_with_groq(company: str, general_section: str, interview_section: str) -> Dict:
    """Use Groq (Llama) as fallback when Gemini is unavailable."""
    key = _get_groq_key()
    if not key:
        return {}

    prompt = _build_prompt(company, general_section, interview_section)

    try:
        resp = requests.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 4096,
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        result = _parse_json(text)
        if result:
            print("[Groq] Analysis complete")
        return result
    except Exception as e:
        print(f"[Groq error] {e}")
        return {}


def analyze_with_gemini(company: str, texts: List[str], all_posts: List[Dict] = None) -> Dict:
    key = _get_key()
    if not key or not texts:
        return {}

    all_posts = all_posts or []

    # Separate general and interview posts
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

    prompt = _build_prompt(company, general_section, interview_section)

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
        result = _parse_json(text)
        return result
    except Exception as e:
        print(f"[Gemini error] {e}")
        if "429" in str(e):
            print("[Falling back to Groq...]")
            return analyze_with_groq(company, general_section, interview_section)
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




def extract_interview_questions(company: str, all_posts: List[Dict]) -> List[Dict]:
    """Use Groq/Gemini to extract specific interview questions from full posts."""
    interview_posts = [
        p for p in all_posts
        if p.get("source") in {"leetcode_discuss_full", "1point3acres_full", "glassdoor_interview"}
        and p.get("text")
    ]
    if not interview_posts:
        return []

    combined = "\n\n===POST===\n".join(
        f"Source: {p['source']}\n{p['text'][:1500]}" for p in interview_posts[:8]
    )

    prompt = (
        f"Extract specific interview questions and rounds from these {company} interview posts.\n\n"
        f"{combined}\n\n"
        f"Return ONLY a JSON array of objects, no markdown:\n"
        f'[{{"round":"Phone Screen","question":"implement shopping cart with discount strategies (strategy pattern)","type":"coding","difficulty":"easy","result":"passed"}},'
        f'{{"round":"Pair Programming","question":"TDD implementation of a feature with SQL","type":"coding","difficulty":"medium","result":"unknown"}}]\n'
        f"Rules:\n"
        f"- round: infer from context. Use: Phone Screen, OA, Pair Programming, Onsite, System Design, Behavioral, Life Story, Technical Screen, ML Design. If unclear use the most likely round based on the question type.\n"
        f"- question: copy the ACTUAL specific question from the text, not a generic description.\n"
        f"- type: coding / system_design / behavioral / sql / ml\n"
        f"- difficulty: easy/medium/hard if mentioned, else omit\n"
        f"- result: passed/failed/unknown\n"
        f"Only include entries with a real question description. Return [] if nothing specific found."
    )

    # Try Groq first (more reliable for structured output)
    groq_key = _get_groq_key()
    if groq_key:
        try:
            resp = requests.post(
                GROQ_API_URL,
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json={
                    "model": GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 2048,
                    "response_format": {"type": "json_object"},
                },
                timeout=20,
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
            # Groq json_object mode wraps in object, extract array
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parsed
            # Try to find array in the object
            for v in parsed.values():
                if isinstance(v, list):
                    return v
        except Exception as e:
            print(f"[Groq questions error] {e}")

    # Try Gemini
    gemini_key = _get_key()
    if gemini_key:
        try:
            resp = requests.post(
                f"{API_URL}?key={gemini_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048},
                },
                timeout=20,
            )
            resp.raise_for_status()
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            # Find JSON array
            start = text.find("[")
            end = text.rfind("]") + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
        except Exception as e:
            print(f"[Gemini questions error] {e}")

    return []

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
    groq_key = _get_groq_key()
    analysis = {}

    if key or groq_key:
        analysis = analyze_with_gemini(company, texts, all_posts=all_posts)
        if not analysis and groq_key:
            # Direct Groq if Gemini key missing
            all_posts_local = all_posts or []
            general_texts = [_clean(p.get("text","")) for p in all_posts_local if p.get("source") not in INTERVIEW_SOURCES and p.get("text")]
            interview_texts = [_clean(p.get("text","")) for p in all_posts_local if p.get("source") in INTERVIEW_SOURCES and p.get("text")]
            general_section = "\n---\n".join(general_texts[:30])
            interview_section = "\n---\n".join(interview_texts[:15]) if interview_texts else "No interview data."
            analysis = analyze_with_groq(company, general_section, interview_section)

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
        "used_ai": bool(analysis.get("data_quality") and analysis.get("data_quality") != "low"),
    }

    return analysis