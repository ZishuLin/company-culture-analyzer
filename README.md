# Company Culture Analyzer

A CLI tool that scrapes Reddit discussions and Glassdoor snippets about a company, then uses AI to generate an honest culture report — covering work-life balance, management quality, career growth, compensation, and more.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## Why

Job postings tell you what a company wants. Culture reports tell you what it's actually like to work there. This tool aggregates real employee discussions from Reddit and Glassdoor and uses Gemini AI to extract honest, structured insights.

## Features

- Searches multiple subreddits (`cscareerquestions`, `ExperiencedDevs`, `jobs`, and more)
- Checks the company's own subreddit if one exists
- Fetches Glassdoor and Indeed review snippets via search
- Uses Gemini AI (free) to score 6 culture dimensions with evidence
- Falls back to keyword analysis if no API key is set
- Outputs both a terminal report and a self-contained HTML file
- Interactive setup wizard for API keys

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

This will prompt you for:
- **Reddit API key** (free) — [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) → Create app → script
- **Gemini API key** (free) — [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

Or manually copy `.env.example` to `.env` and fill in your keys.

## Usage

```bash
# Analyze a company
python main.py analyze Shopify

# Analyze with custom output file
python main.py analyze "Google" --output google_report.html

# Terminal output only (no HTML)
python main.py analyze Microsoft --no-html

# Fetch more posts for a deeper analysis
python main.py analyze Amazon --limit 80
```

## Output

**Terminal:**
```
┌─────────────────────────────────────────────┐
│ Shopify Culture Report                       │
│ 47 posts · 112 samples · reddit, glassdoor  │
└─────────────────────────────────────────────┘

Dimension          Score   Rating
Work-Life Balance  8/10    ████████████░░░
Management         7/10    ███████████░░░░
Career Growth      7/10    ███████████░░░░
Compensation       8/10    ████████████░░░
Culture            8/10    ████████████░░░
Interview          5/10    ████████░░░░░░░

Overall Verdict: Shopify is generally well-regarded...

Green Flags
  ✓ Strong remote-first culture
  ✓ Competitive compensation with equity

Red Flags
  ✗ Interview process is lengthy (4-6 rounds)
  ✗ Fast pace may not suit everyone
```

**HTML:** A self-contained report file that works offline.

## Data Sources

| Source | Method | Auth |
|--------|--------|------|
| Reddit | Official PRAW API | Free API key |
| Glassdoor | Search engine snippets | None |
| Indeed | Search engine snippets | None |

## How It Works

1. Searches Reddit across 6+ subreddits for discussions mentioning the company
2. Checks for a company-specific subreddit
3. Fetches Glassdoor and Indeed snippets via DuckDuckGo search
4. Sends all collected text to Gemini AI for structured analysis
5. Generates a scored report across 6 dimensions with supporting evidence

## Notes

- Results reflect public online discussions and may not represent all employees
- Data quality varies by company size and online presence
- Gemini API key is optional but strongly recommended for meaningful analysis
- Reddit API key is required for Reddit data

## License

MIT
