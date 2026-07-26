"""The generated report must be a single file that renders with no network."""

import json
import re

from github_portfolio_auditor.analyzer import PortfolioAnalyzer
from github_portfolio_auditor.report import render_report

REPOS = [
    {
        "name": "octo/alpha",
        "stars": 3,
        "languages": {"Python": 100},
        "topics": ["x"],
        "license": "MIT License",
        "last_commit": "2026-07-01T00:00:00+00:00",
        "contributors_count": 2,
        "releases_count": 1,
        "is_archived": False,
        "description": "a repo",
    }
]


def _render(tmp_path, repos=REPOS):
    analysis = PortfolioAnalyzer().analyze_portfolio([dict(r) for r in repos])
    return render_report(analysis, tmp_path / "report.html").read_text(encoding="utf-8")


def test_report_has_no_external_resource_references(tmp_path):
    """No CDN script, stylesheet, font or image - the whole point of the
    'single self-contained HTML file' claim in the README."""
    html = _render(tmp_path)
    external = re.findall(r'(?:src|href)\s*=\s*["\'](https?:)?//[^"\']+', html)
    assert external == [], f"report reaches out to the network: {external}"


def test_report_inlines_chartjs(tmp_path):
    html = _render(tmp_path)
    assert "Chart.register" in html or "window.Chart" in html


def test_report_escapes_hostile_repo_metadata(tmp_path):
    """Repo descriptions are attacker-influenceable; they must never break out
    of the HTML or the inlined JS data arrays."""
    hostile = dict(REPOS[0])
    hostile["name"] = "octo/</script><img src=x onerror=alert(1)>"
    hostile["description"] = "<script>alert('xss')</script>"
    html = _render(tmp_path, [hostile])

    assert "<script>alert('xss')</script>" not in html
    assert "<img src=x onerror=alert(1)>" not in html


def test_report_renders_empty_portfolio(tmp_path):
    analysis = PortfolioAnalyzer().analyze_portfolio([])
    html = render_report(analysis, tmp_path / "report.html").read_text(encoding="utf-8")
    assert "Portfolio Audit" in html


def test_sample_dataset_analyzes_and_renders(tmp_path):
    """examples/sample-portfolio.json is the documented demo input - keep it
    loadable and in the shape `gha analyze` expects."""
    from pathlib import Path

    sample = Path(__file__).resolve().parents[1] / "examples" / "sample-portfolio.json"
    repos = json.loads(sample.read_text())["repositories"]
    assert len(repos) >= 5
    analysis = PortfolioAnalyzer().analyze_portfolio(repos)
    assert analysis["insights"]["total_repos"] == len(repos)
    render_report(analysis, tmp_path / "report.html")
