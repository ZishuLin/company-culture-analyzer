"""
Company Culture Analyzer
Scrapes Reddit and Glassdoor to give you an honest picture of what it's like to work somewhere.
"""

import os
import sys
from pathlib import Path

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

sys.path.insert(0, str(Path(__file__).parent))


@click.group()
def cli():
    pass


@cli.command()
@click.argument("company")
@click.option("--output", "-o", default=None, help="Output HTML file (default: <company>_culture.html)")
@click.option("--limit", "-n", default=40, help="Max Reddit posts to fetch")
@click.option("--no-html", is_flag=True, help="Skip HTML report, terminal only")
@click.option("--no-reddit", is_flag=True, help="Skip Reddit scraping (use if no Reddit API key yet)")
def analyze(company, output, limit, no_html, no_reddit):
    """Analyze company culture from Reddit and Glassdoor.

    Example: python main.py analyze Shopify
    """
    from scrapers.reddit import scrape_reddit, scrape_reddit_company_sub
    from scrapers.glassdoor import scrape_glassdoor_snippets, scrape_indeed_reviews
    from analyzer.sentiment import analyze_company
    from report import print_terminal_report, generate_html_report

    console.print(f"\n[bold cyan]Company Culture Analyzer[/bold cyan]")
    console.print(f"Target: [yellow]{company}[/yellow]\n")

    all_posts = []

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:

        # Reddit main search
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

        # Reddit company subreddit
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

        # Glassdoor snippets
        task = progress.add_task("Fetching Glassdoor snippets...", total=None)
        try:
            gd_reviews = scrape_glassdoor_snippets(company)
            all_posts.extend(gd_reviews)
            progress.update(task, description=f"[green]✓ Glassdoor: {len(gd_reviews)} snippets[/green]")
        except Exception as e:
            progress.update(task, description=f"[red]✗ Glassdoor error: {e}[/red]")
        progress.stop_task(task)

        # Indeed reviews
        task = progress.add_task("Fetching Indeed reviews...", total=None)
        try:
            indeed = scrape_indeed_reviews(company)
            all_posts.extend(indeed)
            progress.update(task, description=f"[green]✓ Indeed: {len(indeed)} snippets[/green]")
        except Exception as e:
            progress.update(task, description=f"[red]✗ Indeed error: {e}[/red]")
        progress.stop_task(task)

        # Analyze
        task = progress.add_task("Analyzing with AI...", total=None)
        analysis = analyze_company(company, all_posts)
        ai_used = analysis.get("metadata", {}).get("used_ai", False)
        label = "Gemini AI" if ai_used else "keyword analysis (no Gemini key)"
        progress.update(task, description=f"[green]✓ Analysis complete ({label})[/green]")
        progress.stop_task(task)

        # HTML report
        if not no_html:
            output_path = output or f"{company.lower().replace(' ', '_')}_culture.html"
            task = progress.add_task("Generating HTML report...", total=None)
            generate_html_report(company, analysis, output_path)
            progress.update(task, description=f"[green]✓ Report: {output_path}[/green]")
            progress.stop_task(task)

    # Terminal report
    print_terminal_report(company, analysis)

    if not no_html:
        console.print(f"[bold]HTML Report:[/bold] {output_path}")


@cli.command()
def setup():
    """Interactive setup - create .env file with API keys."""
    console.print("\n[bold cyan]Setup[/bold cyan]\n")

    env_path = Path(__file__).parent / ".env"
    values = {}

    console.print("[bold]Reddit API[/bold] (required for Reddit scraping)")
    console.print("  1. Go to https://www.reddit.com/prefs/apps")
    console.print("  2. Click 'Create app' → select 'script'")
    console.print("  3. Copy the client ID (under the app name) and secret\n")

    values["REDDIT_CLIENT_ID"] = click.prompt("Reddit Client ID (or press Enter to skip)", default="")
    values["REDDIT_CLIENT_SECRET"] = click.prompt("Reddit Client Secret (or press Enter to skip)", default="")

    console.print("\n[bold]Gemini API[/bold] (free, used for AI analysis)")
    console.print("  Get a free key at https://aistudio.google.com/app/apikey\n")
    values["GEMINI_API_KEY"] = click.prompt("Gemini API Key (or press Enter to skip)", default="")

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

    Example: python main.py test-analyze Shopify "great work life balance but slow promotions"
    """
    from analyzer.sentiment import analyze_company
    from report import print_terminal_report, generate_html_report

    fake_posts = [{"source": "manual", "text": text, "comments": []}]
    analysis = analyze_company(company, fake_posts)
    print_terminal_report(company, analysis)

    output_path = output or f"{company.lower()}_culture.html"
    generate_html_report(company, analysis, output_path)
    console.print(f"[bold]HTML Report:[/bold] {output_path}")
if __name__ == "__main__":
    cli()