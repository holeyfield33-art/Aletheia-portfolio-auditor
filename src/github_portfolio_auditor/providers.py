"""LLM provider clients for AI repo summaries.

Mirrors The Lie Detector's provider model (same flag names, same env vars),
so one `.env` configures the whole Aletheia toolchain:

- ``anthropic`` (default): ``ANTHROPIC_API_KEY``.
- ``openai``: any OpenAI-compatible endpoint (OpenAI, Featherless, OpenRouter,
  local llama.cpp). ``OPENAI_API_KEY`` or ``FEATHERLESS_API_KEY``, plus an
  optional ``OPENAI_BASE_URL`` / ``--base-url``.

``build_summary_client`` returns ``None`` when the chosen provider has no
credential - callers fall back to plain metadata summaries, clearly flagged
as not AI-generated, never faked.
"""

from __future__ import annotations

import os
from typing import Protocol

# Summaries are short and high-volume (one call per repo), so both defaults
# are the provider's cheap/fast tier rather than a top model.
DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


class SummaryClient(Protocol):
    def summarize(self, prompt: str) -> str: ...


class AnthropicSummaryClient:
    def __init__(self, api_key: str | None = None, model: str = DEFAULT_ANTHROPIC_MODEL):
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self.model = model

    def summarize(self, prompt: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in response.content if block.type == "text").strip()


class OpenAISummaryClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_OPENAI_MODEL,
        base_url: str | None = None,
    ):
        try:
            import openai
        except ImportError as exc:
            raise RuntimeError(
                'openai SDK not installed - install it with: pip install -e ".[openai]"'
            ) from exc

        kwargs: dict[str, str] = {}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        self.client = openai.OpenAI(**kwargs)
        self.model = model

    def summarize(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        return (response.choices[0].message.content or "").strip()


def build_summary_client(
    provider: str = "anthropic",
    model: str | None = None,
    base_url: str | None = None,
    anthropic_api_key: str | None = None,
) -> SummaryClient | None:
    """Build the summary client for ``provider``, or ``None`` if it has no credential.

    Raises ``ValueError`` for an unknown provider name.
    """
    if provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("FEATHERLESS_API_KEY")
        if not api_key:
            return None
        return OpenAISummaryClient(
            api_key=api_key,
            model=model or DEFAULT_OPENAI_MODEL,
            base_url=base_url or os.environ.get("OPENAI_BASE_URL"),
        )
    if provider == "anthropic":
        api_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return None
        return AnthropicSummaryClient(api_key=api_key, model=model or DEFAULT_ANTHROPIC_MODEL)
    raise ValueError(f"unknown provider {provider!r} (expected 'anthropic' or 'openai')")
