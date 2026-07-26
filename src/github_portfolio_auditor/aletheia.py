"""aletheia: one front door for the discover -> triage -> verify -> badge pipeline.

The suite is three standalone tools; this CLI only routes between them:

    aletheia scan      # discover: audit every repo in a GitHub account (this package)
    aletheia analyze   # discover: score repos and build the portfolio report (this package)
    aletheia check     # triage:   run vibe-check on one local repo (offline, free)
    aletheia verify    # verify:   run The Lie Detector on a repo's README claims

``check`` and ``verify`` are thin subprocess wrappers so each tool keeps its
own release cadence and zero/its-own dependency story. Unknown options are
passed through untouched, so any vibe-check or liedetector flag works here.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

from .cli import analyze as _analyze
from .cli import scan as _scan

app = typer.Typer(
    help="Aletheia: discover -> triage -> verify -> badge for AI-built code.",
    no_args_is_help=True,
)
console = Console()

app.command(name="scan")(_scan)
app.command(name="analyze")(_analyze)

_PASSTHROUGH = {"allow_extra_args": True, "ignore_unknown_options": True}


def _vibe_check_command() -> list[str] | None:
    """Locate vibe-check: a PATH executable, or VIBE_CHECK_PATH pointing at vibe_check.py."""
    exe = shutil.which("vibe-check")
    if exe:
        return [exe]
    script = os.environ.get("VIBE_CHECK_PATH")
    if script and Path(script).is_file():
        return [sys.executable, script]
    return None


@app.command(context_settings=_PASSTHROUGH)
def check(
    ctx: typer.Context,
    path: Path = typer.Argument(Path("."), help="Repository root to scan."),
) -> None:
    """Triage a local repo with vibe-check (offline, no keys, stdlib only)."""
    cmd = _vibe_check_command()
    if cmd is None:
        console.print(
            "[bold red]vibe-check not found.[/] Install it with:\n"
            "  git clone https://github.com/holeyfield33-art/vibe-check\n"
            "then either put a `vibe-check` launcher on your PATH or set\n"
            "  export VIBE_CHECK_PATH=/path/to/vibe-check/vibe_check.py"
        )
        raise typer.Exit(code=2)
    raise typer.Exit(code=subprocess.call([*cmd, str(path), *ctx.args]))


@app.command(context_settings=_PASSTHROUGH)
def verify(
    ctx: typer.Context,
    repo_url: str = typer.Argument(..., help="https://github.com/<owner>/<repo>"),
) -> None:
    """Verify a repo's README claims with The Lie Detector (Docker + LLM key required)."""
    exe = shutil.which("liedetector")
    if exe is None:
        console.print(
            "[bold red]liedetector not found.[/] Install it with:\n"
            "  git clone https://github.com/holeyfield33-art/Lie-Detector\n"
            '  pip install -e "Lie-Detector[openai]"\n'
            "then run `liedetector doctor` to check Docker and credentials."
        )
        raise typer.Exit(code=2)
    raise typer.Exit(code=subprocess.call([exe, "run", repo_url, *ctx.args]))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
