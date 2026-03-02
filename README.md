# Company Culture Analyzer

An AI-powered CLI tool that automatically scrapes multiple data sources and generates honest, structured culture reports for any company — covering work-life balance, management quality, compensation, interview process, and more.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![AI](https://img.shields.io/badge/AI-Gemini%202.5%20Flash-purple)

## Why

Job postings tell you what a company wants you to hear. This tool aggregates real employee discussions from 7+ sources and uses Gemini AI to extract honest, structured insights — including actual interview questions people reported.

## Features

- **Multi-source scraping** — Glassdoor, Indeed, Reddit, LeetCode Discuss, and 1point3acres
- **AI analysis** — Gemini 2.5 Flash (with Groq/Llama fallback) scores 6 culture dimensions with real evidence
- **Interview question extraction** — Pulls specific questions and round details from LeetCode posts
- **Multi-company comparison** — Compare culture across multiple companies side by side
- **HTML report** — Self-contained report file that works offline
- **Keyword fallback** — Works without an API key using basic keyword analysis
- **Chinese community data** — Scrapes 1point3acres for Chinese tech worker insights (translated to English)

## Data Sources

| Source | What It Provides | Auth Required |
|--------|-----------------|---------------|
| Glassdoor | Employee reviews, ratings, compensation data | None (via search) |
| Indeed | Employee reviews, work environment feedback | None (via search) |
| Reddit | Candid discussions across tech subreddits | Free API key |
| LeetCode Discuss | Full interview experience posts with specific questions | None (GraphQL API) |
| 1point3acres | Chinese tech worker interview experiences and reviews | None (snippets) |

> **Note on Reddit:** Reddit API approval currently takes 2–7 days. The tool works fully without Reddit — all other sources are available immediately. Reddit data will be added automatically once the API key is approved.

## Installation

```bash
git clone https://github.com/ZishuLin/company-culture-analyzer.git
cd company-culture-analyzer
pip install -r requirements.txt
```

## Setup

```bash
python main.py setup
```

This prompts you for:
- **SerpAPI key** (free tier: 100 searches/month) — [serpapi.com](https://serpapi.com)
- **Gemini API key** (free) — [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
- **Groq API key** (free, Gemini fallback) — [console.groq.com](https://console.groq.com)
- **Reddit API key** (free, optional) — [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)

Or manually copy `.env.example` to `.env` and fill in your keys.

## Usage

```bash
# Analyze a company
python main.py analyze Shopify

# Skip Reddit (faster, no Reddit key needed)
python main.py analyze Shopify --no-reddit

# Compare multiple companies
python main.py compare Shopify Stripe Airbnb

# Terminal output only (no HTML)
python main.py analyze Microsoft --no-html
```

## Sample Output

```
Shopify Culture Report
Based on 101 posts · Sources: glassdoor, indeed, 1point3acres, leetcode

Dimension            Score   Summary
Work-Life Balance    6/10    High stress reported in fast-paced teams
Management Quality   4/10    Frequent reorgs, inconsistent leadership
Career Growth        4/10    Limited promotion paths, many leaving
Compensation         3/10    20-30% below market, known to underpay
Culture & Inclusion  4/10    Culture has deteriorated, per reviews
Interview Process    8/10    OA → Phone Screen → Pair Programming → Onsite

Overall Verdict: Shopify has smart colleagues and interesting work, but
compensation and career growth are significant concerns.

Red Flags
  ✗ Compensation 20-30% below market
  ✗ Frequent reorgs and culture deterioration
  ✗ Low career opportunities rating (3.0/5)

Green Flags
  ✓ Smart and kind colleagues
  ✓ Supportive interviewers during pair programming
  ✓ Challenging, meaningful work

Interview Questions & Rounds
  Phone Screen    | Implement shopping cart with discount strategies (strategy pattern) | coding · easy
  Pair Programming| TDD implementation of a feature with SQL                           | coding · medium
  Onsite          | ML system design: design a recommendation engine                   | system_design · hard
  Behavioral      | Tell me about a time you disagreed with a technical decision        | behavioral
```

## How It Works

1. Scrapes 7 sources in parallel for employee reviews and interview posts
2. Fetches full LeetCode interview posts via GraphQL API (no auth required)
3. Translates Chinese content from 1point3acres to English via AI
4. Sends all data to Gemini AI for structured analysis across 6 dimensions
5. Extracts specific interview questions and round details from interview posts
6. Generates terminal report + self-contained HTML file

## Tech Stack

- **Python 3.8+** — CLI with Click
- **SerpAPI** — Reliable Glassdoor/Indeed search results
- **PRAW** — Reddit API (optional)
- **LeetCode GraphQL API** — Full interview post content
- **BeautifulSoup** — HTML parsing
- **Gemini 2.5 Flash** — AI analysis and translation
- **Groq (Llama 3.3 70B)** — Fallback when Gemini quota is exceeded
- **Rich** — Terminal formatting

## License

MIT
