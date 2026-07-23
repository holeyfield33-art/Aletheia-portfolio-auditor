import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
import json
import os
from pathlib import Path

from .client import GitHubClient

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
    
    client = GitHubClient(token)
    
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Fetching repositories...", total=None)
        
        repos = client.get_repositories(username)
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

def main():
    app()

if __name__ == "__main__":
    main()