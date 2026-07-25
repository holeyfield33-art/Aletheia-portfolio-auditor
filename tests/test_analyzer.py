"""Regression tests for PortfolioAnalyzer.score_repo edge cases."""

from github_portfolio_auditor.analyzer import PortfolioAnalyzer


def test_score_repo_with_malformed_last_commit_does_not_crash():
    """A repo with a non-ISO 'last_commit' string must not blow up the whole
    analysis run - it should be scored like a repo with no commit history."""
    analyzer = PortfolioAnalyzer()
    repo = {
        "name": "example/repo",
        "license": "MIT",
        "description": "desc",
        "topics": ["x"],
        "contributors_count": 2,
        "releases_count": 1,
        "is_archived": False,
        "last_commit": "not-a-date-at-all",
    }

    result = analyzer.score_repo(repo)

    assert result["days_since_push"] is None
    assert result["is_stale"] is False


def test_analyze_portfolio_skips_bad_date_without_crashing_other_repos():
    analyzer = PortfolioAnalyzer()
    repos = [
        {"name": "good/repo", "license": "MIT", "description": "d",
         "topics": [], "contributors_count": 1, "releases_count": 0,
         "is_archived": False, "last_commit": "2024-01-01T00:00:00Z",
         "languages": {"Python": 1}},
        {"name": "bad/repo", "license": None, "description": None,
         "topics": [], "contributors_count": 0, "releases_count": 0,
         "is_archived": False, "last_commit": "not-a-date-at-all",
         "languages": {}},
    ]

    result = analyzer.analyze_portfolio(repos)

    assert result["insights"]["total_repos"] == 2
    names = [r["name"] for r in result["repositories"]]
    assert "good/repo" in names
    assert "bad/repo" in names
