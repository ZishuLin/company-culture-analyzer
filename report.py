"""
Generate HTML and terminal reports for company culture analysis.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from typing import Dict
import os

console = Console()


def score_bar(score: int, width: int = 20) -> str:
    """Generate ASCII progress bar."""
    filled = round(score / 10 * width)
    bar = "█" * filled + "░" * (width - filled)
    return bar


def score_color(score: int) -> str:
    if score >= 7:
        return "green"
    elif score >= 5:
        return "yellow"
    else:
        return "red"


DIMENSION_LABELS = {
    "work_life_balance": "Work-Life Balance",
    "management":        "Management Quality",
    "career_growth":     "Career Growth",
    "compensation":      "Compensation",
    "culture":           "Culture & Inclusion",
    "interview":         "Interview Process",
}


def print_terminal_report(company: str, analysis: Dict):
    """Print rich terminal report."""
    if "error" in analysis:
        console.print(f"[red]{analysis['error']}[/red]")
        return

    meta = analysis.get("metadata", {})

    console.print()
    console.print(Panel(
        f"[bold cyan]{company}[/bold cyan] Culture Report\n"
        f"[dim]Based on {meta.get('total_posts', 0)} posts · "
        f"{meta.get('total_text_samples', 0)} text samples · "
        f"Sources: {', '.join(meta.get('sources', {}).keys())}[/dim]",
        border_style="blue",
    ))

    # Scores table
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold blue")
    table.add_column("Dimension", style="white", width=22)
    table.add_column("Score", width=8)
    table.add_column("Rating", width=22)
    table.add_column("Summary", style="dim")

    for key, label in DIMENSION_LABELS.items():
        dim = analysis.get(key, {})
        if not dim:
            continue
        score = dim.get("score", 5)
        color = score_color(score)
        bar = score_bar(score, 15)
        table.add_row(
            label,
            f"[{color}]{score}/10[/{color}]",
            f"[{color}]{bar}[/{color}]",
            dim.get("summary", ""),
        )

    console.print(table)

    # Overall verdict
    verdict = analysis.get("overall_verdict", "")
    if verdict:
        console.print(Panel(verdict, title="Overall Verdict", border_style="cyan"))

    # Red/Green flags
    red_flags = analysis.get("red_flags", [])
    green_flags = analysis.get("green_flags", [])

    if red_flags:
        console.print("\n[bold red]Red Flags[/bold red]")
        for flag in red_flags:
            console.print(f"  [red]✗[/red] {flag}")

    if green_flags:
        console.print("\n[bold green]Green Flags[/bold green]")
        for flag in green_flags:
            console.print(f"  [green]✓[/green] {flag}")

    dq = analysis.get("data_quality", "unknown")
    dq_color = {"high": "green", "medium": "yellow", "low": "red"}.get(dq, "dim")
    console.print(f"\n[dim]Data quality: [{dq_color}]{dq}[/{dq_color}][/dim]")
    console.print()




def print_interview_questions(questions: list) -> None:
    """Print interview questions in a formatted terminal table."""
    from rich.console import Console
    from rich.table import Table
    from rich import box

    console = Console()

    if not questions:
        return

    console.print()
    console.print("[bold cyan]Interview Questions & Rounds[/bold cyan]")

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold magenta")
    table.add_column("Round", style="cyan", width=20)
    table.add_column("Question / Task", width=55)
    table.add_column("Type", width=14)
    table.add_column("Result", width=10)

    type_colors = {
        "coding": "green",
        "system_design": "blue",
        "behavioral": "yellow",
        "sql": "magenta",
        "ml": "cyan",
    }

    for q in questions:
        round_name = q.get("round", "Unknown")
        question = q.get("question", "")
        qtype = q.get("type", "coding").lower()
        difficulty = q.get("difficulty", "")
        result = q.get("result", "")

        color = type_colors.get(qtype, "white")
        type_display = f"[{color}]{qtype}[/{color}]"
        if difficulty:
            type_display += f" ({difficulty})"

        result_display = ""
        if result and result.lower() not in ("unknown", ""):
            result_display = f"[green]✓[/green]" if "pass" in result.lower() else f"[red]✗[/red]"

        table.add_row(round_name, question, type_display, result_display)

    console.print(table)
    console.print()

def generate_html_report(company: str, analysis: Dict, output_path: str, interview_questions: list = None):
    """Generate self-contained HTML report."""
    if "error" in analysis:
        return

    meta = analysis.get("metadata", {})

    # Build dimension rows
    dim_rows = ""
    for key, label in DIMENSION_LABELS.items():
        dim = analysis.get(key, {})
        if not dim:
            continue
        score = dim.get("score", 5)
        pct = score * 10
        color = "#22c55e" if score >= 7 else "#f59e0b" if score >= 5 else "#ef4444"
        evidence_html = ""
        for ev in dim.get("evidence", [])[:2]:
            evidence_html += f'<div class="evidence">"{ev}"</div>'
        dim_rows += f"""
        <div class="dim-card">
          <div class="dim-header">
            <span class="dim-label">{label}</span>
            <span class="dim-score" style="color:{color}">{score}/10</span>
          </div>
          <div class="dim-bar-bg">
            <div class="dim-bar-fill" style="width:{pct}%;background:{color}"></div>
          </div>
          <div class="dim-summary">{dim.get('summary', '')}</div>
          {evidence_html}
        </div>"""

    # Red/green flags
    red_html = "".join(f'<div class="flag flag-red">✗ {f}</div>' for f in analysis.get("red_flags", []))
    green_html = "".join(f'<div class="flag flag-green">✓ {f}</div>' for f in analysis.get("green_flags", []))

    dq = analysis.get("data_quality", "unknown")
    dq_color = {"high": "#22c55e", "medium": "#f59e0b", "low": "#ef4444"}.get(dq, "#94a3b8")
    sources_str = ", ".join(meta.get("sources", {}).keys())

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{company} Culture Report</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #080e1a; --surface: #0d1629; --border: #1a2540;
    --accent: #3b82f6; --text: #e2e8f0; --muted: #64748b;
    --mono: 'DM Mono', monospace; --sans: 'DM Sans', sans-serif;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: var(--sans); font-weight: 300; padding: 40px 24px; }}
  body::before {{
    content: ''; position: fixed; inset: 0; pointer-events: none;
    background-image: linear-gradient(rgba(59,130,246,.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(59,130,246,.03) 1px, transparent 1px);
    background-size: 48px 48px;
  }}
  .container {{ max-width: 860px; margin: 0 auto; position: relative; }}
  .header {{ margin-bottom: 48px; }}
  .tag {{ font-family: var(--mono); font-size: .72rem; letter-spacing: .15em; color: #06d6a0;
    border: 1px solid rgba(6,214,160,.3); padding: 4px 12px; border-radius: 20px; display: inline-block; margin-bottom: 16px; }}
  h1 {{ font-family: var(--mono); font-size: 2.4rem; font-weight: 400; margin-bottom: 8px; }}
  .meta {{ font-family: var(--mono); font-size: .78rem; color: var(--muted); }}
  .section {{ margin-bottom: 40px; }}
  .section-title {{ font-family: var(--mono); font-size: .72rem; letter-spacing: .12em;
    color: var(--accent); margin-bottom: 20px; text-transform: uppercase; }}
  .dim-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
    padding: 20px 24px; margin-bottom: 12px; transition: border-color .2s; }}
  .dim-card:hover {{ border-color: rgba(59,130,246,.4); }}
  .dim-header {{ display: flex; justify-content: space-between; margin-bottom: 10px; }}
  .dim-label {{ font-weight: 500; font-size: .95rem; }}
  .dim-score {{ font-family: var(--mono); font-size: 1.1rem; font-weight: 500; }}
  .dim-bar-bg {{ background: #1a2540; border-radius: 4px; height: 6px; margin-bottom: 12px; }}
  .dim-bar-fill {{ height: 6px; border-radius: 4px; transition: width .6s ease; }}
  .dim-summary {{ font-size: .85rem; color: var(--muted); margin-bottom: 8px; }}
  .evidence {{ font-size: .8rem; color: #475569; font-style: italic; padding: 6px 0;
    border-left: 2px solid #1e3a5f; padding-left: 10px; margin-top: 6px; }}
  .verdict-box {{ background: var(--surface); border: 1px solid rgba(59,130,246,.3);
    border-radius: 10px; padding: 24px; margin-bottom: 32px; font-size: .95rem; line-height: 1.7; color: #cbd5e1; }}
  .flags {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  .flags-col h3 {{ font-family: var(--mono); font-size: .75rem; letter-spacing: .1em; margin-bottom: 12px; text-transform: uppercase; }}
  .flag {{ font-size: .85rem; padding: 8px 12px; border-radius: 6px; margin-bottom: 8px; }}
  .flag-red {{ background: rgba(239,68,68,.1); color: #fca5a5; border: 1px solid rgba(239,68,68,.2); }}
  .flag-green {{ background: rgba(34,197,94,.1); color: #86efac; border: 1px solid rgba(34,197,94,.2); }}
  .footer {{ font-family: var(--mono); font-size: .72rem; color: var(--muted); margin-top: 48px;
    padding-top: 24px; border-top: 1px solid var(--border); }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="tag">culture report</div>
    <h1>{company}</h1>
    <div class="meta">{meta.get('total_posts', 0)} posts · {meta.get('total_text_samples', 0)} samples · {sources_str} · Data quality: <span style="color:{dq_color}">{dq}</span></div>
  </div>

  <div class="section">
    <div class="section-title">Overall Verdict</div>
    <div class="verdict-box">{analysis.get('overall_verdict', 'No verdict available.')}</div>
  </div>

  <div class="section">
    <div class="section-title">Dimension Scores</div>
    {dim_rows}
  </div>

  <div class="section">
    <div class="section-title">Flags</div>
    <div class="flags">
      <div class="flags-col">
        <h3 style="color:#ef4444">Red Flags</h3>
        {red_html if red_html else '<div class="flag flag-green">No major red flags found</div>'}
      </div>
      <div class="flags-col">
        <h3 style="color:#22c55e">Green Flags</h3>
        {green_html if green_html else '<div style="color:#475569;font-size:.85rem">No green flags extracted</div>'}
      </div>
    </div>
  </div>

  __INTERVIEW_SECTION__

  <div class="footer">
    Generated by company-culture-analyzer · Data from Reddit &amp; Glassdoor snippets ·
    AI analysis by Gemini · Results may not reflect current conditions
  </div>
</div>
</body>
</html>"""

    # Build interview questions section
    interview_section_html = ""
    if interview_questions:
        rows = ""
        for q in interview_questions:
            round_name = q.get("round", "")
            question = q.get("question", "")
            qtype = q.get("type", "coding").lower()
            difficulty = q.get("difficulty", "")
            result = q.get("result", "")
            diff_str = f" ({difficulty})" if difficulty else ""
            result_str = "✓ Passed" if "pass" in result.lower() else ("✗ Failed" if result and result.lower() not in ("unknown","") else "")
            result_color = "#4ade80" if "pass" in result.lower() else "#f87171"
            rows += f"""<tr>
                <td><strong>{round_name}</strong></td>
                <td>{question}</td>
                <td>{qtype}{diff_str}</td>
                <td style="color:{result_color}">{result_str}</td>
            </tr>"""
        interview_section_html = f"""<div class="section" style="margin-top:2rem">
    <h2 style="color:#c084fc;margin-bottom:1rem">🎯 Interview Questions &amp; Rounds</h2>
    <table style="width:100%;border-collapse:collapse;font-size:.9rem">
        <thead>
            <tr style="background:#1e1b4b;color:#a5b4fc">
                <th style="padding:.5rem 1rem;text-align:left">Round</th>
                <th style="padding:.5rem 1rem;text-align:left">Question / Task</th>
                <th style="padding:.5rem 1rem;text-align:left">Type</th>
                <th style="padding:.5rem 1rem;text-align:left">Result</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
</div>"""

    html = html.replace("__INTERVIEW_SECTION__", interview_section_html)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


def generate_comparison_html(companies: list, all_analyses: dict, output_path: str):
    """Generate side-by-side HTML comparison report."""

    COLORS = ["#3b82f6", "#06d6a0", "#f59e0b", "#f87171", "#a78bfa"]

    def score_color(score):
        if score >= 7: return "#22c55e"
        if score >= 5: return "#f59e0b"
        return "#ef4444"

    # Build dimension rows
    dim_rows = ""
    for key, label in DIMENSION_LABELS.items():
        dim_rows += f'<tr><td class="dim-name">{label}</td>'
        for i, company in enumerate(companies):
            analysis = all_analyses.get(company, {})
            dim = analysis.get(key, {})
            score = dim.get("score", 0) if isinstance(dim, dict) else 0
            summary = dim.get("summary", "") if isinstance(dim, dict) else ""
            color = score_color(score)
            pct = score * 10
            dim_rows += f'''<td class="score-cell">
              <div class="score-num" style="color:{color}">{score}/10</div>
              <div class="mini-bar-bg"><div class="mini-bar-fill" style="width:{pct}%;background:{color}"></div></div>
              <div class="score-summary">{summary}</div>
            </td>'''
        dim_rows += "</tr>"

    # Overall averages row
    dim_rows += '<tr class="avg-row"><td class="dim-name"><strong>Overall Avg</strong></td>'
    best_company = None
    best_avg = 0
    avgs = {}
    for company in companies:
        analysis = all_analyses.get(company, {})
        scores = [analysis.get(k, {}).get("score", 0) for k in DIMENSION_LABELS if isinstance(analysis.get(k, {}), dict)]
        avg = round(sum(scores) / len(scores), 1) if scores else 0
        avgs[company] = avg
        if avg > best_avg:
            best_avg = avg
            best_company = company

    for company in companies:
        avg = avgs[company]
        color = score_color(avg)
        crown = " 🏆" if company == best_company else ""
        dim_rows += f'<td class="score-cell"><div class="score-num" style="color:{color}"><strong>{avg}{crown}</strong></div></td>'
    dim_rows += "</tr>"

    # Verdicts
    verdict_cards = ""
    for i, company in enumerate(companies):
        analysis = all_analyses.get(company, {})
        verdict = analysis.get("overall_verdict", "No data available.")
        red = "".join(f'<div class="flag flag-red">✗ {f}</div>' for f in analysis.get("red_flags", []))
        green = "".join(f'<div class="flag flag-green">✓ {f}</div>' for f in analysis.get("green_flags", []))
        color = COLORS[i % len(COLORS)]
        verdict_cards += f'''
        <div class="verdict-card">
          <div class="verdict-company" style="color:{color}">{company}</div>
          <div class="verdict-text">{verdict}</div>
          <div class="flags-mini">{green}{red}</div>
        </div>'''

    # Company header columns
    company_headers = "".join(
        f'<th style="color:{COLORS[i % len(COLORS)]}">{c}</th>'
        for i, c in enumerate(companies)
    )


    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Culture Comparison: {' vs '.join(companies)}</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
  :root {{ --bg:#080e1a; --surface:#0d1629; --border:#1a2540; --text:#e2e8f0; --muted:#64748b; --mono:'DM Mono',monospace; --sans:'DM Sans',sans-serif; }}
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{background:var(--bg);color:var(--text);font-family:var(--sans);font-weight:300;padding:40px 24px;}}
  body::before{{content:'';position:fixed;inset:0;pointer-events:none;background-image:linear-gradient(rgba(59,130,246,.03) 1px,transparent 1px),linear-gradient(90deg,rgba(59,130,246,.03) 1px,transparent 1px);background-size:48px 48px;}}
  .container{{max-width:1100px;margin:0 auto;position:relative;}}
  .tag{{font-family:var(--mono);font-size:.72rem;letter-spacing:.15em;color:#06d6a0;border:1px solid rgba(6,214,160,.3);padding:4px 12px;border-radius:20px;display:inline-block;margin-bottom:16px;}}
  h1{{font-family:var(--mono);font-size:2rem;font-weight:400;margin-bottom:8px;}}
  .meta{{font-family:var(--mono);font-size:.78rem;color:var(--muted);margin-bottom:48px;}}
  .section-title{{font-family:var(--mono);font-size:.72rem;letter-spacing:.12em;color:#3b82f6;margin-bottom:20px;text-transform:uppercase;}}
  table{{width:100%;border-collapse:collapse;margin-bottom:48px;}}
  th{{font-family:var(--mono);font-size:.85rem;padding:14px 16px;text-align:center;border-bottom:2px solid var(--border);}}
  th:first-child{{text-align:left;color:var(--muted);}}
  td{{padding:12px 16px;border-bottom:1px solid var(--border);vertical-align:top;}}
  .dim-name{{font-size:.9rem;color:var(--text);white-space:nowrap;}}
  .score-cell{{text-align:center;}}
  .score-num{{font-family:var(--mono);font-size:1.1rem;margin-bottom:6px;}}
  .mini-bar-bg{{background:#1a2540;border-radius:3px;height:4px;margin:0 auto 6px;max-width:80px;}}
  .mini-bar-fill{{height:4px;border-radius:3px;}}
  .score-summary{{font-size:.72rem;color:var(--muted);line-height:1.4;max-width:180px;margin:0 auto;}}
  .avg-row td{{border-top:2px solid var(--border);padding-top:16px;}}
  .verdicts{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px;margin-bottom:48px;}}
  .verdict-card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:24px;}}
  .verdict-company{{font-family:var(--mono);font-size:1rem;font-weight:500;margin-bottom:12px;}}
  .verdict-text{{font-size:.85rem;color:#cbd5e1;line-height:1.7;margin-bottom:16px;}}
  .flags-mini{{display:flex;flex-direction:column;gap:6px;}}
  .flag{{font-size:.78rem;padding:5px 10px;border-radius:5px;}}
  .flag-red{{background:rgba(239,68,68,.1);color:#fca5a5;border:1px solid rgba(239,68,68,.2);}}
  .flag-green{{background:rgba(34,197,94,.1);color:#86efac;border:1px solid rgba(34,197,94,.2);}}
  .footer{{font-family:var(--mono);font-size:.72rem;color:var(--muted);margin-top:48px;padding-top:24px;border-top:1px solid var(--border);}}
</style>
</head>
<body>
<div class="container">
  <div class="tag">culture comparison</div>
  <h1>{' vs '.join(companies)}</h1>
  <div class="meta">Generated by company-culture-analyzer · Data from Reddit, Glassdoor &amp; Indeed</div>

  <div class="section-title">Score Comparison</div>
  <table>
    <thead><tr><th>Dimension</th>{company_headers}</tr></thead>
    <tbody>{dim_rows}</tbody>
  </table>

  <div class="section-title">Verdicts</div>
  <div class="verdicts">{verdict_cards}</div>

  <div class="footer">Results based on public employee discussions. May not reflect current conditions.</div>
</div>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)