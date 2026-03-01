"""
Company Culture Analyzer
Scrapes Reddit and Glassdoor to give you an honest picture of what it's like to work somewhere.
"""

import os
import sys
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env", override=True)
except ImportError:
    pass

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich import box

console = Console()
sys.path.insert(0, str(Path(__file__).parent))

DIMENSIONS = {
    "work_life_balance": "Work-Life Balance",
    "management":        "Management",
    "career_growth":     "Career Growth",
    "compensation":      "Compensation",
    "culture":           "Culture",
    "interview":         "Interview",
}


@click.group()
def cli():
    pass


@cli.command()
@click.argument("company")
@click.option("--output", "-o", default=None)
@click.option("--limit", "-n", default=40)
@click.option("--no-html", is_flag=True)
@click.option("--no-reddit", is_flag=True)
def analyze(company, output, limit, no_html, no_reddit):
    """Analyze company culture from Reddit and Glassdoor.

    Example: python main.py analyze Shopify
    """
    from scrapers.reddit import scrape_reddit, scrape_reddit_company_sub
    from scrapers.glassdoor import scrape_glassdoor_snippets, scrape_indeed_reviews, scrape_glassdoor_full_reviews
    from scrapers.yimusan import scrape_yimusan, scrape_yimusan_interview
    from scrapers.interview_sources import scrape_interview_data, scrape_full_interview_posts
    from analyzer.sentiment import analyze_company, extract_interview_questions
    from report import print_terminal_report, print_interview_questions, generate_html_report

    console.print(f"\n[bold cyan]Company Culture Analyzer[/bold cyan]")
    console.print(f"Target: [yellow]{company}[/yellow]\n")

    all_posts = []

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:

        task = progress.add_task("Searching Reddit...", total=None)
        if no_reddit:
            progress.update(task, description="[dim]Reddit skipped (--no-reddit)[/dim]")
            progress.stop_task(task)
        else:
            try:
                posts = scrape_reddit(company, limit=limit)
                all_posts.extend(posts)
                progress.update(task, description=f"[green]✓ Reddit: {len(posts)} posts[/green]")
            except ValueError as e:
                progress.update(task, description=f"[yellow]⚠ Reddit: {str(e).split(chr(10))[0]}[/yellow]")
            except Exception as e:
                progress.update(task, description=f"[red]✗ Reddit error: {e}[/red]")
            progress.stop_task(task)

        task = progress.add_task(f"Checking r/{company.lower()}...", total=None)
        if no_reddit:
            progress.update(task, description="[dim]Skipped[/dim]")
            progress.stop_task(task)
        else:
            try:
                sub_posts = scrape_reddit_company_sub(company)
                all_posts.extend(sub_posts)
                progress.update(task, description=f"[green]✓ r/{company.lower()}: {len(sub_posts)} posts[/green]")
            except Exception:
                progress.update(task, description=f"[dim]No company subreddit found[/dim]")
            progress.stop_task(task)

        task = progress.add_task("Fetching Glassdoor snippets...", total=None)
        try:
            gd_reviews = scrape_glassdoor_snippets(company)
            all_posts.extend(gd_reviews)
            progress.update(task, description=f"[green]✓ Glassdoor: {len(gd_reviews)} snippets[/green]")
        except Exception as e:
            progress.update(task, description=f"[red]✗ Glassdoor error: {e}[/red]")
        progress.stop_task(task)

        task = progress.add_task("Fetching Glassdoor full reviews...", total=None)
        try:
            gd_full = scrape_glassdoor_full_reviews(company)
            all_posts.extend(gd_full)
            progress.update(task, description=f"[green]✓ Glassdoor full: {len(gd_full)} pages[/green]")
        except Exception as e:
            progress.update(task, description=f"[red]✗ Glassdoor full: {e}[/red]")
        progress.stop_task(task)

        task = progress.add_task("Fetching Indeed reviews...", total=None)
        try:
            indeed = scrape_indeed_reviews(company)
            all_posts.extend(indeed)
            progress.update(task, description=f"[green]✓ Indeed: {len(indeed)} snippets[/green]")
        except Exception as e:
            progress.update(task, description=f"[red]✗ Indeed error: {e}[/red]")
        progress.stop_task(task)

        task = progress.add_task("Fetching 一亩三分地...", total=None)
        try:
            yms = scrape_yimusan(company)
            all_posts.extend(yms)
            progress.update(task, description=f"[green]✓ 一亩三分地: {len(yms)} posts[/green]")
        except Exception as e:
            progress.update(task, description=f"[red]✗ 一亩三分地 error: {e}[/red]")
        progress.stop_task(task)

        task = progress.add_task("Fetching 一亩三分地面经...", total=None)
        try:
            yms_iv = scrape_yimusan_interview(company)
            all_posts.extend(yms_iv)
            progress.update(task, description=f"[green]✓ 面经: {len(yms_iv)} posts[/green]")
        except Exception as e:
            progress.update(task, description=f"[red]✗ 面经 error: {e}[/red]")
        progress.stop_task(task)

        task = progress.add_task("Fetching Glassdoor interviews + LeetCode...", total=None)
        try:
            iv_data = scrape_interview_data(company)
            all_posts.extend(iv_data)
            gd_iv = sum(1 for p in iv_data if p["source"] == "glassdoor_interview")
            lc_iv = sum(1 for p in iv_data if p["source"] == "leetcode_discuss")
            progress.update(task, description=f"[green]✓ Glassdoor interviews: {gd_iv} · LeetCode: {lc_iv}[/green]")
        except Exception as e:
            progress.update(task, description=f"[red]✗ Interview data error: {e}[/red]")
        progress.stop_task(task)

        task = progress.add_task("Fetching full interview posts (detailed questions)...", total=None)
        try:
            full_posts = scrape_full_interview_posts(company)
            all_posts.extend(full_posts)
            lc_full = sum(1 for p in full_posts if p["source"] == "leetcode_discuss_full")
            progress.update(task, description=f"[green]✓ LeetCode full posts: {lc_full}[/green]")
        except Exception as e:
            progress.update(task, description=f"[red]✗ Full posts error: {e}[/red]")
        progress.stop_task(task)

        task = progress.add_task("Analyzing with AI...", total=None)
        analysis = analyze_company(company, all_posts)
        ai_used = analysis.get("metadata", {}).get("used_ai", False)
        label = "Gemini AI" if ai_used else "keyword analysis (no Gemini key)"
        progress.update(task, description=f"[green]✓ Analysis complete ({label})[/green]")
        progress.stop_task(task)

        task = progress.add_task("Extracting interview questions...", total=None)
        interview_questions = extract_interview_questions(company, all_posts)
        progress.update(task, description=f"[green]✓ Interview questions: {len(interview_questions)} found[/green]")
        progress.stop_task(task)

        if not no_html:
            output_path = output or f"{company.lower().replace(' ', '_')}_culture.html"
            task = progress.add_task("Generating HTML report...", total=None)
            generate_html_report(company, analysis, output_path, interview_questions=interview_questions)
            progress.update(task, description=f"[green]✓ Report: {output_path}[/green]")
            progress.stop_task(task)

    print_interview_questions(interview_questions)
    print_terminal_report(company, analysis)

    if not no_html:
        console.print(f"[bold]HTML Report:[/bold] {output_path}")


@cli.command()
@click.argument("companies", nargs=-1, required=True)
@click.option("--no-reddit", is_flag=True)
@click.option("--output", "-o", default=None)
def compare(companies, no_reddit, output):
    """Compare culture across multiple companies.

    Example: python main.py compare Shopify Stripe Airbnb
    """
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env", override=True)
    from scrapers.reddit import scrape_reddit, scrape_reddit_company_sub
    from scrapers.glassdoor import scrape_glassdoor_snippets, scrape_indeed_reviews, scrape_glassdoor_full_reviews
    from scrapers.yimusan import scrape_yimusan, scrape_yimusan_interview
    from scrapers.interview_sources import scrape_interview_data, scrape_full_interview_posts
    from analyzer.sentiment import analyze_company
    from report import print_terminal_report, generate_comparison_html

    if len(companies) < 2:
        console.print("[red]Please provide at least 2 companies to compare.[/red]")
        return

    console.print(f"\n[bold cyan]Company Culture Comparison[/bold cyan]")
    console.print(f"Comparing: [yellow]{' vs '.join(companies)}[/yellow]\n")

    all_analyses = {}

    for i, company in enumerate(companies):
        console.print(f"[bold]Analyzing {company}...[/bold]")
        all_posts = []

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            if not no_reddit:
                task = progress.add_task("Reddit...", total=None)
                try:
                    posts = scrape_reddit(company, limit=30)
                    all_posts.extend(posts)
                    progress.update(task, description=f"[green]✓ Reddit: {len(posts)} posts[/green]")
                except Exception:
                    progress.update(task, description="[yellow]⚠ Reddit: skipped[/yellow]")
                progress.stop_task(task)

            task = progress.add_task("Glassdoor + Indeed...", total=None)
            try:
                gd_full = scrape_glassdoor_full_reviews(company)
                all_posts.extend(gd_full)
                all_posts.extend(scrape_glassdoor_snippets(company))
                all_posts.extend(scrape_indeed_reviews(company))
                progress.update(task, description=f"[green]✓ {len(all_posts)} total sources[/green]")
            except Exception as e:
                progress.update(task, description=f"[red]✗ {e}[/red]")
            progress.stop_task(task)

            task = progress.add_task("Fetching 一亩三分地...", total=None)
            try:
                yms = scrape_yimusan(company)
                all_posts.extend(yms)
                progress.update(task, description=f"[green]✓ 一亩三分地: {len(yms)} posts[/green]")
            except Exception as e:
                progress.update(task, description=f"[red]✗ 一亩三分地: {e}[/red]")
            progress.stop_task(task)

            task = progress.add_task("Fetching 面经...", total=None)
            try:
                yms_iv = scrape_yimusan_interview(company)
                all_posts.extend(yms_iv)
                progress.update(task, description=f"[green]✓ 面经: {len(yms_iv)} posts[/green]")
            except Exception as e:
                progress.update(task, description=f"[red]✗ 面经: {e}[/red]")
            progress.stop_task(task)

            task = progress.add_task("Glassdoor interviews + LeetCode...", total=None)
            try:
                iv_data = scrape_interview_data(company)
                all_posts.extend(iv_data)
                progress.update(task, description=f"[green]✓ Interview data: {len(iv_data)} posts[/green]")
            except Exception as e:
                progress.update(task, description=f"[red]✗ Interview data: {e}[/red]")
            progress.stop_task(task)

            task = progress.add_task("Full interview posts...", total=None)
            try:
                full_posts = scrape_full_interview_posts(company)
                all_posts.extend(full_posts)
                progress.update(task, description=f"[green]✓ Full posts: {len(full_posts)}[/green]")
            except Exception as e:
                progress.update(task, description=f"[red]✗ Full posts: {e}[/red]")
            progress.stop_task(task)

            task = progress.add_task("Analyzing...", total=None)
            analysis = analyze_company(company, all_posts)
            all_analyses[company] = analysis
            progress.update(task, description="[green]✓ Done[/green]")
            progress.stop_task(task)

        # Rate limit protection between companies
        if i < len(companies) - 1:
            console.print("[dim]Waiting 5s to avoid rate limits...[/dim]")
            time.sleep(5)

    _print_comparison(list(companies), all_analyses)

    output_path = output or f"comparison_{'_vs_'.join(c.lower() for c in companies)}.html"
    generate_comparison_html(list(companies), all_analyses, output_path)
    console.print(f"\n[bold]HTML Report:[/bold] {output_path}")


@cli.command()
def setup():
    """Interactive setup - create .env file with API keys."""
    console.print("\n[bold cyan]Setup[/bold cyan]\n")

    env_path = Path(__file__).parent / ".env"
    values = {}

    console.print("[bold]Reddit API[/bold] (required for Reddit scraping - free)")
    console.print("  1. Go to https://www.reddit.com/prefs/apps")
    console.print("  2. Click 'Create app' → select 'script'")
    console.print("  3. Copy the client ID and secret\n")

    values["REDDIT_CLIENT_ID"] = click.prompt("Reddit Client ID (or Enter to skip)", default="")
    values["REDDIT_CLIENT_SECRET"] = click.prompt("Reddit Client Secret (or Enter to skip)", default="")

    console.print("\n[bold]Gemini API[/bold] (free)")
    console.print("  Get at https://aistudio.google.com/app/apikey\n")
    values["GEMINI_API_KEY"] = click.prompt("Gemini API Key (or Enter to skip)", default="")

    console.print("\n[bold]SerpAPI[/bold] (free 100/month, for Glassdoor/Indeed)")
    console.print("  Get at https://serpapi.com\n")
    values["SERPAPI_KEY"] = click.prompt("SerpAPI Key (or Enter to skip)", default="")

    with open(env_path, "w") as f:
        for k, v in values.items():
            if v:
                f.write(f"{k}={v}\n")

    console.print(f"\n[green]✓ Saved to {env_path}[/green]")
    console.print("\nRun: [cyan]python main.py analyze Shopify[/cyan]")


@cli.command()
@click.argument("company")
@click.argument("text")
@click.option("--output", "-o", default=None)
def test_analyze(company, text, output):
    """Test AI analysis with manually provided text.

    Example: python main.py test-analyze Shopify "great wlb, slow promotions"
    """
    from analyzer.sentiment import analyze_company, extract_interview_questions
    from report import print_terminal_report, print_interview_questions, generate_html_report

    fake_posts = [{"source": "manual", "text": text, "comments": []}]
    analysis = analyze_company(company, fake_posts)
    interview_questions = []
    print_terminal_report(company, analysis)

    output_path = output or f"{company.lower()}_culture.html"
    generate_html_report(company, analysis, output_path, interview_questions=interview_questions)
    console.print(f"[bold]HTML Report:[/bold] {output_path}")


def _print_comparison(companies, all_analyses):
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold blue")
    table.add_column("Dimension", style="white", width=22)

    for company in companies:
        table.add_column(company, width=12, justify="center")

    scores_per_company = {c: [] for c in companies}

    for key, label in DIMENSIONS.items():
        row = [label]
        for company in companies:
            analysis = all_analyses.get(company, {})
            dim = analysis.get(key, {})
            score = dim.get("score", 0) if isinstance(dim, dict) else 0
            scores_per_company[company].append(score)
            color = "green" if score >= 7 else "yellow" if score >= 5 else "red"
            row.append(f"[{color}]{score}/10[/{color}]")
        table.add_row(*row)

    avg_row = ["[bold]Overall Avg[/bold]"]
    best_company = None
    best_avg = 0
    for company in companies:
        scores = scores_per_company[company]
        avg = round(sum(scores) / len(scores), 1) if scores else 0
        if avg > best_avg:
            best_avg = avg
            best_company = company
        color = "green" if avg >= 7 else "yellow" if avg >= 5 else "red"
        avg_row.append(f"[{color}][bold]{avg}[/bold][/{color}]")

    table.add_row(*avg_row)

    console.print()
    console.print(table)
    if best_company:
        console.print(f"\n[bold green]🏆 Best overall: {best_company} ({best_avg}/10)[/bold green]")
    console.print()


if __name__ == "__main__":
    cli()