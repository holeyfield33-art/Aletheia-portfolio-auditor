"""Regression tests for `gha scan` / `gha analyze` CLI error handling."""

import json

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


def _analyze(tmp_path, text):
    bad = tmp_path / "portfolio.json"
    bad.write_text(text)
    return runner.invoke(
        cli.app,
        ["analyze", "--input", str(bad), "--output", str(tmp_path / "out")],
    )


def test_analyze_rejects_truncated_json_without_traceback(tmp_path):
    """An interrupted `gha scan` leaves a half-written portfolio.json; analyze
    must say so, not dump a JSONDecodeError traceback."""
    result = _analyze(tmp_path, '{"repositories": [{"name": "a/b"')

    assert result.exit_code == 1
    assert not isinstance(result.exception, json.JSONDecodeError)
    assert "not valid JSON" in result.output


def test_analyze_rejects_json_without_repositories_key(tmp_path):
    """Valid JSON that isn't a portfolio file must not raise a raw KeyError."""
    result = _analyze(tmp_path, '{"foo": "bar"}')

    assert result.exit_code == 1
    assert not isinstance(result.exception, KeyError)
    assert "not a portfolio file" in result.output


def test_analyze_rejects_repositories_of_wrong_type(tmp_path):
    result = _analyze(tmp_path, '{"repositories": "nope"}')

    assert result.exit_code == 1
    assert "not a portfolio file" in result.output
