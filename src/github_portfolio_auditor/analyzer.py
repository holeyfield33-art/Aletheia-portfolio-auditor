"""Core analysis modules for repositories.

Phase 2: Analysis - turns raw repo metadata (from Phase 1 discovery) into
quality scores, AI-generated summaries, and cross-repo portfolio insights.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import anthropic

# Cheap/fast model - summaries are short, high-volume (one call per repo),
# so we don't need a top-tier model here.
SUMMARY_MODEL = "claude-haiku-4-5-20251001"

STALE_DAYS = 180  # repos with no push in this many days are flagged "stale"


class PortfolioAnalyzer:
    def __init__(self, anthropic_api_key: str | None = None):
        """anthropic_api_key may be None - AI summaries are skipped (not faked)
        if no key is available, so callers can tell the difference between a
        real summary and a fallback."""
        self.client = anthropic.Anthropic(api_key=anthropic_api_key) if anthropic_api_key else None

    def score_repo(self, repo: dict[str, Any]) -> dict[str, Any]:
        """Heuristic quality score (0-100) from metadata we already collected
        in Phase 1. Returns the score plus the notes that explain it, so the
        report can show *why* a repo scored the way it did."""
        score = 0
        notes: list[str] = []

        if repo.get("license"):
            score += 20
        else:
            notes.append("No license file")

        if repo.get("description"):
            score += 15
        else:
            notes.append("No description")

        if repo.get("topics"):
            score += 10
        else:
            notes.append("No topics/tags")

        contributors = repo.get("contributors_count") or 0
        if contributors > 1:
            score += 15
        elif contributors == 1:
            score += 5
            notes.append("Single contributor")

        if (repo.get("releases_count") or 0) > 0:
            score += 10
        else:
            notes.append("No releases")

        last_commit = repo.get("last_commit")
        days_since_push = None
        if last_commit:
            try:
                pushed = last_commit if isinstance(last_commit, datetime) else datetime.fromisoformat(str(last_commit))
            except ValueError:
                notes.append(f"Unrecognized last_commit value: {last_commit!r}")
                pushed = None
            if pushed is not None:
                if pushed.tzinfo is None:
                    pushed = pushed.replace(tzinfo=timezone.utc)
                days_since_push = (datetime.now(timezone.utc) - pushed).days
                if days_since_push <= 30:
                    score += 20
                elif days_since_push <= STALE_DAYS:
                    score += 10
                else:
                    notes.append(f"Stale - no commits in {days_since_push} days")

        if repo.get("is_archived"):
            notes.append("Archived")
        else:
            score += 10

        return {
            "score": min(score, 100),
            "notes": notes,
            "days_since_push": days_since_push,
            "is_stale": (days_since_push or 0) > STALE_DAYS,
        }

    def summarize_repo(self, repo: dict[str, Any]) -> tuple[str, bool]:
        """Returns (summary_text, is_ai_generated). Falls back to a plain
        metadata-derived sentence if no API key is configured, rather than
        silently pretending it's an AI summary."""
        if self.client is None:
            langs = ", ".join(list(repo.get("languages", {}).keys())[:3]) or "unknown stack"
            return (
                f"{repo['name']}: {repo.get('description') or 'no description'} ({langs}).",
                False,
            )

        prompt = (
            "Write a single, plain-English sentence (max 30 words) summarizing what this "
            "GitHub repo is for, based on this metadata. No preamble, just the sentence.\n\n"
            f"Name: {repo.get('name')}\n"
            f"Description: {repo.get('description')}\n"
            f"Languages: {list(repo.get('languages', {}).keys())}\n"
            f"Topics: {repo.get('topics')}\n"
        )
        response = self.client.messages.create(
            model=SUMMARY_MODEL,
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if block.type == "text").strip()
        return text, True

    def analyze_portfolio(self, repos: list[dict[str, Any]]) -> dict[str, Any]:
        """Runs per-repo scoring + summaries, then computes cross-repo
        insights (duplicate stacks, staleness, license coverage, etc)."""
        analyzed = []
        ai_calls_made = 0
        for repo in repos:
            scoring = self.score_repo(repo)
            summary, is_ai = self.summarize_repo(repo)
            if is_ai:
                ai_calls_made += 1
            analyzed.append({**repo, **scoring, "summary": summary, "summary_is_ai": is_ai})

        total = len(analyzed)
        licensed = sum(1 for r in analyzed if r.get("license"))
        stale = [r for r in analyzed if r["is_stale"]]
        archived = [r for r in analyzed if r.get("is_archived")]

        # Group repos by their dominant language to spot overlapping/duplicate projects
        by_language: dict[str, list[str]] = {}
        for r in analyzed:
            langs = r.get("languages") or {}
            dominant = max(langs, key=langs.get) if langs else "Unknown"
            by_language.setdefault(dominant, []).append(r["name"])

        duplicate_stacks = {lang: names for lang, names in by_language.items() if len(names) > 1}

        insights = {
            "total_repos": total,
            "license_coverage_pct": round((licensed / total) * 100, 1) if total else 0,
            "stale_repos": [r["name"] for r in stale],
            "archived_repos": [r["name"] for r in archived],
            "duplicate_stacks": duplicate_stacks,
            "avg_quality_score": round(sum(r["score"] for r in analyzed) / total, 1) if total else 0,
            "ai_summaries_generated": ai_calls_made,
        }

        return {"repositories": analyzed, "insights": insights}
