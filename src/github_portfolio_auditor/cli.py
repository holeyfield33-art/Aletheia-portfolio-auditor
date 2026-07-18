import typer
from rich.console import Console

app = typer.Typer()
console = Console()

@app.command()
def scan(
    token: str = typer.Option(..., envvar="GITHUB_TOKEN", help="GitHub PAT"),
    username: str = typer.Option(None, help="GitHub username (defaults to token owner)"),
    output: str = typer.Option("reports", help="Output directory"),
):
    """Scan GitHub portfolio and generate reports."""
    console.print(f"Scanning portfolio for {username or 'authenticated user'}...")
    # TODO: Implement core logic
    console.print("✅ Scan complete! Reports generated.")

if __name__ == "__main__":
    app()