# Architecture

Two commands, two files, one direction of data flow. `scan` talks to GitHub and
writes JSON; `analyze` reads that JSON and writes a report. Nothing else in the
system talks to the network.

```
                    GitHub REST API
                          │
                    (PyGithub, 1h cache)
                          │
  gha scan  ──────────────┴─────────────►  reports/portfolio.json
                                                    │
  gha analyze  ◄────────────────────────────────────┘
      │
      ├─ score_repo()      heuristic 0-100 + explanatory notes
      ├─ summarize_repo()  ─── optional ───►  Anthropic / OpenAI-compatible API
      └─ render_report()
                          │
                          ├──►  reports/analysis.json
                          └──►  reports/report.html   (self-contained)
```

The split is deliberate: scanning is slow, rate-limited and needs a token;
analysis is fast, deterministic (without an LLM key) and re-runnable. You can
re-score and re-render a portfolio a hundred times off one scan.

## Modules

| File | Responsibility |
|---|---|
| `cli.py` | The `gha` Typer app: `scan`, `analyze`. Argument parsing, input validation, progress display, and turning every expected failure into a one-line message + exit 1. |
| `aletheia.py` | The `aletheia` Typer app. Re-exports `scan`/`analyze` from `cli.py` and adds `check`/`verify`, which locate sibling tools and `subprocess.call` them with all extra args passed through. |
| `client.py` | `GitHubClient` — thin PyGithub wrapper. `get_repositories()` (paginated) and `get_repo_metadata()` (the 11 fields everything downstream uses). |
| `analyzer.py` | `PortfolioAnalyzer` — `score_repo`, `summarize_repo`, `analyze_portfolio`. Pure functions over dicts; no I/O except the optional LLM call. |
| `providers.py` | `build_summary_client()` and the two `SummaryClient` implementations. The only place API keys are read. |
| `report.py` | `render_report()` — computes chart series, renders the Jinja template, inlines vendored Chart.js. |
| `templates/report.html.j2` | The dashboard. Jinja `autoescape=True`; all data reaches JS via `\|tojson`. |
| `templates/vendor/chart.umd.min.js` | Chart.js v4.4.4 (MIT), vendored so reports have zero network dependencies. |

## The data contract

`portfolio.json` is the interface between the two commands, and it is a stable,
hand-editable shape:

```json
{
  "repositories": [
    {
      "name": "owner/repo",
      "stars": 412,
      "forks": 38,
      "languages": {"TypeScript": 184000, "CSS": 21000},
      "topics": ["editor", "crdt"],
      "license": "MIT License",
      "last_commit": "2026-07-23T00:00:00+00:00",
      "contributors_count": 7,
      "releases_count": 12,
      "is_archived": false,
      "description": "Collaborative markdown editor"
    }
  ]
}
```

Every field except `name` is optional at analysis time — a repo with only a
name scores 10/100 and renders fine. `analyze` validates the envelope (object,
with a `repositories` list) and rejects anything else with an actionable
message rather than a traceback.

`analysis.json` is the same array with `score`, `notes`, `days_since_push`,
`is_stale`, `summary` and `summary_is_ai` merged in, plus a top-level
`insights` object.

## Design decisions worth knowing

**Summaries are never faked.** `summarize_repo()` returns
`(text, is_ai_generated)`. With no client, or when the API call raises, it
returns a metadata-derived sentence with `is_ai=False`, and the report's
"AI Summaries" stat counts only the real ones. A provider outage degrades a
300-repo run instead of ending it.

**Scoring is metadata-only.** Nothing reads source code. That keeps `analyze`
free and offline-capable, and it is why the pipeline hands off to vibe-check
(which reads code) and the Lie Detector (which executes it).

**The report is one file with no network dependencies.** Chart.js is inlined
and fonts are system stacks. A report you email to a collaborator renders
identically to the one on your machine, and it still renders in five years
when the CDN URL has moved.

**Untrusted strings are treated as untrusted.** Repo descriptions and topics
come from GitHub and can contain anything. Jinja autoescaping handles the HTML,
and `|tojson` escapes `<`/`>` in the embedded JS arrays so a description can't
break out of `<script>`. `tests/test_report.py` asserts both.

## Known rough edges

- `requests_cache.install_cache()` runs at `client.py` import time, patching
  `requests` process-wide. Harmless for the CLI, surprising if you import the
  package into a larger app.
- `--incremental` is accepted and ignored. The cache is time-based (1 hour),
  not diff-based.
- `gha scan` writes `portfolio.json` non-atomically, so an interrupted scan
  leaves a truncated file. `analyze` detects this and tells you to re-scan.
- `client.get_repositories()` materialises the full list before any metadata
  fetch, and issues ~4 API calls per repo. Large accounts will feel it.
