"""Tests for the summary provider layer and the analyzer's use of it."""

import pytest

from github_portfolio_auditor import providers
from github_portfolio_auditor.analyzer import PortfolioAnalyzer
from github_portfolio_auditor.providers import (
    AnthropicSummaryClient,
    OpenAISummaryClient,
    build_summary_client,
)

REPO = {
    "name": "example/repo",
    "description": "does a thing",
    "topics": ["x"],
    "languages": {"Python": 100},
    "license": "MIT",
    "contributors_count": 1,
    "releases_count": 0,
    "is_archived": False,
    "last_commit": "2026-01-01T00:00:00+00:00",
}


class FakeClient:
    def __init__(self, text="An AI summary.", fail=False):
        self.text = text
        self.fail = fail

    def summarize(self, prompt):
        if self.fail:
            raise RuntimeError("provider exploded")
        return self.text


def test_analyzer_uses_injected_client():
    summary, is_ai = PortfolioAnalyzer(client=FakeClient()).summarize_repo(REPO)
    assert summary == "An AI summary."
    assert is_ai is True


def test_analyzer_without_client_falls_back_and_is_flagged():
    summary, is_ai = PortfolioAnalyzer().summarize_repo(REPO)
    assert "example/repo" in summary
    assert is_ai is False


def test_failed_summary_falls_back_without_aborting_portfolio():
    """One dead API call must not kill the whole scan - public-facing runs
    can be hundreds of repos deep when a provider hiccups."""
    result = PortfolioAnalyzer(client=FakeClient(fail=True)).analyze_portfolio([dict(REPO)])
    repo = result["repositories"][0]
    assert repo["summary_is_ai"] is False
    assert "example/repo" in repo["summary"]
    assert result["insights"]["ai_summaries_generated"] == 0


def test_build_summary_client_openai_without_key_returns_none(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FEATHERLESS_API_KEY", raising=False)
    assert build_summary_client("openai") is None


def test_build_summary_client_openai_reads_featherless_key_and_base_url(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("FEATHERLESS_API_KEY", "fk-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.featherless.ai/v1")
    client = build_summary_client("openai", model="some-model")
    assert isinstance(client, OpenAISummaryClient)
    assert client.model == "some-model"
    assert str(client.client.base_url).startswith("https://api.featherless.ai/v1")


def test_build_summary_client_anthropic_uses_explicit_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = build_summary_client("anthropic", anthropic_api_key="sk-test")
    assert isinstance(client, AnthropicSummaryClient)
    assert client.model == providers.DEFAULT_ANTHROPIC_MODEL


def test_build_summary_client_anthropic_without_key_returns_none(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert build_summary_client("anthropic") is None


def test_build_summary_client_rejects_unknown_provider():
    with pytest.raises(ValueError, match="unknown provider"):
        build_summary_client("grok")


def test_legacy_anthropic_api_key_argument_still_works():
    analyzer = PortfolioAnalyzer(anthropic_api_key="sk-test")
    assert isinstance(analyzer.client, AnthropicSummaryClient)
