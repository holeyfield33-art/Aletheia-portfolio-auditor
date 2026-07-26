import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
import json
import os
from pathlib import Path

from .client import GitHubClient
from .analyzer import PortfolioAnalyzer
from .providers import build_summary_client
from .report import render_report

app = typer.Typer()
console = Console()

@app.command()
def scan(
    token: str = typer.Option(..., envvar="GITHUB_TOKEN", help="GitHub PAT"),
    username: str = typer.Option(None, help="GitHub username (defaults to token owner)"),
    output: str = typer.Option("reports", help="Output directory"),
    incremental: bool = typer.Option(False, help="Incremental scan using cache"),
):
    """Phase 1: Discovery - Scan GitHub portfolio and generate reports."""
    console.print(f"[bold green]Starting Portfolio Discovery for {username or 'authenticated user'}[/]")

    try:
        client = GitHubClient(token)
    except Exception as e:
        console.print(f"[bold red]Failed to authenticate with GitHub: {e}[/]")
        raise typer.Exit(code=1)

    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Fetching repositories...", total=None)

        try:
            repos = client.get_repositories(username)
        except Exception as e:
            console.print(f"[bold red]Failed to fetch repositories: {e}[/]")
            raise typer.Exit(code=1)
        progress.update(task, completed=True)
    
    console.print(f"Found {len(repos)} repositories.")
    
    metadata = []
    with Progress() as progress:
        task = progress.add_task("Collecting metadata...", total=len(repos))
        for repo in repos:
            try:
                meta = client.get_repo_metadata(repo)
                metadata.append(meta)
                progress.advance(task)
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to fetch {repo.full_name}: {e}[/]")
    
    # Save raw data
    report_file = output_dir / "portfolio.json"
    with open(report_file, "w") as f:
        json.dump({"repositories": metadata}, f, indent=2, default=str)
    
    console.print(f"[bold green]✅ Phase 1 Discovery complete![/] Reports saved to {output_dir}")
    console.print(f"Key file: {report_file}")

@app.command()
def analyze(
    input: str = typer.Option("reports/portfolio.json", help="Path to portfolio.json from `gha scan`"),
    output: str = typer.Option("reports", help="Output directory"),
    provider: str = typer.Option("anthropic", help="LLM provider for AI summaries: anthropic or openai"),
    model: str = typer.Option(None, help="Override the provider's default summary model"),
    base_url: str = typer.Option(None, envvar="OPENAI_BASE_URL", help="OpenAI-compatible endpoint, e.g. https://api.featherless.ai/v1"),
    anthropic_key: str = typer.Option(None, envvar="ANTHROPIC_API_KEY", help="Anthropic API key for AI summaries"),
):
    """Phase 2: Analysis - score repos, generate AI summaries, and build a chart-based HTML report."""
    input_path = Path(input)
    if not input_path.exists():
        console.print(f"[bold red]No portfolio data found at {input_path}.[/] Run `gha scan` first.")
        raise typer.Exit(code=1)

    with open(input_path) as f:
        portfolio = json.load(f)
    repos = portfolio["repositories"]

    try:
        client = build_summary_client(
            provider, model=model, base_url=base_url, anthropic_api_key=anthropic_key
        )
    except (ValueError, RuntimeError) as e:
        console.print(f"[bold red]{e}[/]")
        raise typer.Exit(code=1)
    if client is None:
        console.print(f"[yellow]No credential found for provider '{provider}' - summaries will use a plain metadata fallback instead of AI.[/]")

    analyzer = PortfolioAnalyzer(client=client)

    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Scoring repos and generating summaries...", total=None)
        analysis = analyzer.analyze_portfolio(repos)
        progress.update(task, completed=True)

    analysis_file = output_dir / "analysis.json"
    with open(analysis_file, "w") as f:
        json.dump(analysis, f, indent=2, default=str)

    report_file = render_report(analysis, output_dir / "report.html")

    insights = analysis["insights"]
    console.print(f"[bold green]✅ Phase 2 Analysis complete![/]")
    console.print(f"Avg quality score: {insights['avg_quality_score']} | License coverage: {insights['license_coverage_pct']}%")
    console.print(f"Stale repos: {len(insights['stale_repos'])} | Archived: {len(insights['archived_repos'])}")
    console.print(f"Report: {report_file}")


def main():
    app()

if __name__ == "__main__":
    main()