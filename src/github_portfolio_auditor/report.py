"""Renders the analyzed portfolio into a self-contained HTML dashboard."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).parent / "templates"


def _status_breakdown(repos: list[dict[str, Any]]) -> tuple[list[str], list[int]]:
    active = sum(1 for r in repos if not r["is_stale"] and not r.get("is_archived"))
    stale = sum(1 for r in repos if r["is_stale"] and not r.get("is_archived"))
    archived = sum(1 for r in repos if r.get("is_archived"))
    return ["Active", "Stale", "Archived"], [active, stale, archived]


def _language_breakdown(repos: list[dict[str, Any]], top_n: int = 8) -> tuple[list[str], list[int]]:
    counts: dict[str, int] = {}
    for r in repos:
        langs = r.get("languages") or {}
        dominant = max(langs, key=langs.get) if langs else "Unknown"
        counts[dominant] = counts.get(dominant, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    return [k for k, _ in ranked], [v for _, v in ranked]


def render_report(analysis: dict[str, Any], output_path: Path) -> Path:
    repos = analysis["repositories"]
    insights = analysis["insights"]

    # Sort by score descending for the score chart / table readability
    repos_sorted = sorted(repos, key=lambda r: r["score"], reverse=True)

    status_labels, status_counts = _status_breakdown(repos_sorted)
    lang_labels, lang_counts = _language_breakdown(repos_sorted)

    top_stars = sorted(repos_sorted, key=lambda r: r.get("stars", 0), reverse=True)[:10]

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
    template = env.get_template("report.html.j2")

    html = template.render(
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        repositories=repos_sorted,
        insights=insights,
        repo_names=[r["name"].split("/")[-1] for r in repos_sorted],
        repo_scores=[r["score"] for r in repos_sorted],
        status_labels=status_labels,
        status_counts=status_counts,
        lang_labels=lang_labels,
        lang_counts=lang_counts,
        top_star_names=[r["name"].split("/")[-1] for r in top_stars],
        top_star_values=[r.get("stars", 0) for r in top_stars],
    )

    output_path.write_text(html, encoding="utf-8")
    return output_path
