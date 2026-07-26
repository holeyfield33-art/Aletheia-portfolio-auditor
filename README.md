# GitHub Portfolio Auditor

Comprehensive tool to scan your entire GitHub account and generate detailed portfolio reports.

## Features
- Repository discovery and metadata (`gha scan`)
- Per-repo quality scoring (license, description, topics, contributors, releases, activity)
- One-sentence AI repo summaries (Anthropic API, with a plain metadata fallback if no key is set)
- Cross-repo insights: license coverage, stale/archived repos, repos sharing a dominant language
- Self-contained HTML dashboard report (JSON output also available: `portfolio.json`, `analysis.json`)

Not yet implemented (do not rely on these): CI/CD or security analysis, merge/dedupe
suggestions, action-plan generation, PDF export, and incremental (cache-based) scanning -
the `--incremental` flag is currently a no-op.

## Installation
```bash
pip install -e .
```

## Usage
```bash
gha scan --token <github-pat> --output reports
gha analyze --input reports/portfolio.json --output reports
```

Run `gha scan --help` or `gha analyze --help` for all options.

## Development
```bash
pip install -e ".[dev]"
pytest
```

See [docs](docs/) for details.