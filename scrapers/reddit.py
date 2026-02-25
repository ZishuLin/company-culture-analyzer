"""
Reddit scraper - searches for company discussions across relevant subreddits.
Uses PRAW (official Reddit API wrapper). Free, no rate limit issues.
"""

import os
import re
import praw
from typing import List, Dict


SUBREDDITS = [
    "cscareerquestions",
    "ExperiencedDevs",
    "jobs",
    "careerguidance",
    "AskHR",
    "softwareengineering",
]

REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = "CompanyCultureAnalyzer/1.0"


def get_reddit_client():
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        raise ValueError(
            "Reddit API credentials not set.\n"
            "1. Go to https://www.reddit.com/prefs/apps\n"
            "2. Create a 'script' app\n"
            "3. Add REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET to your .env file"
        )
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )


def scrape_reddit(company_name: str, limit: int = 50) -> List[Dict]:
    """Search Reddit for discussions about a company."""
    reddit = get_reddit_client()
    posts = []

    queries = [
        f"{company_name} work culture",
        f"{company_name} working there",
        f"{company_name} employee experience",
        f"{company_name} interview",
        f"working at {company_name}",
    ]

    seen_ids = set()

    for subreddit_name in SUBREDDITS:
        try:
            subreddit = reddit.subreddit(subreddit_name)
            for query in queries[:2]:  # limit queries per subreddit
                for post in subreddit.search(query, limit=10, sort="relevance"):
                    if post.id in seen_ids:
                        continue
                    # Filter: must mention company name
                    combined = (post.title + " " + post.selftext).lower()
                    if company_name.lower() not in combined:
                        continue
                    seen_ids.add(post.id)

                    # Get top comments
                    post.comments.replace_more(limit=0)
                    comments = []
                    for comment in post.comments[:5]:
                        if len(comment.body) > 50:
                            comments.append({
                                "text": comment.body[:500],
                                "score": comment.score,
                            })

                    posts.append({
                        "source": "reddit",
                        "subreddit": subreddit_name,
                        "title": post.title,
                        "text": post.selftext[:800],
                        "score": post.score,
                        "url": f"https://reddit.com{post.permalink}",
                        "comments": comments,
                        "created_utc": post.created_utc,
                    })

                    if len(posts) >= limit:
                        return posts
        except Exception:
            continue

    return posts


def scrape_reddit_company_sub(company_name: str) -> List[Dict]:
    """Try to scrape the company's own subreddit if it exists."""
    reddit = get_reddit_client()
    slug = re.sub(r'[^a-z0-9]', '', company_name.lower())
    posts = []

    try:
        subreddit = reddit.subreddit(slug)
        # Check it exists
        _ = subreddit.description
        for post in subreddit.hot(limit=20):
            posts.append({
                "source": "reddit_company_sub",
                "subreddit": slug,
                "title": post.title,
                "text": post.selftext[:500],
                "score": post.score,
                "url": f"https://reddit.com{post.permalink}",
                "comments": [],
                "created_utc": post.created_utc,
            })
    except Exception:
        pass

    return posts
