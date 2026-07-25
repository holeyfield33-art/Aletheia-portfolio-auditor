"""Regression tests for the `gha scan` CLI error handling."""

from typer.testing import CliRunner

from github_portfolio_auditor import cli

runner = CliRunner()


def test_scan_reports_friendly_error_on_client_failure(tmp_path, monkeypatch):
    """An invalid token / network failure while creating the GitHub client
    must produce a clean error message and non-zero exit code, not a raw
    traceback dump."""

    def boom(self, token):
        raise Exception("401 Bad credentials")

    monkeypatch.setattr(cli.GitHubClient, "__init__", boom)

    result = runner.invoke(
        cli.app,
        ["scan", "--token", "bad-token", "--output", str(tmp_path / "out")],
    )

    assert result.exit_code != 0
    assert isinstance(result.exception, SystemExit) or result.exception is None
