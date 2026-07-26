# examples/

## `sample-portfolio.json`

A synthetic 12-repo GitHub account under the fictional owner `octo-dev`, in
exactly the shape `gha scan` writes. **It is not real data** — no such account
exists, and the stars, dates and contributor counts are invented.

It exists so that:

- you can see a real report before spending a GitHub token on one,
- the screenshots in [`docs/images/`](../docs/images) are reproducible by anyone,
- `tests/test_report.py` has a realistic end-to-end fixture,
- demos have a deterministic, offline, never-rate-limited fallback.

```bash
gha analyze --input examples/sample-portfolio.json --output reports/demo
open reports/demo/report.html
```

The mix is deliberate: five well-maintained repos that score 100, two stale
ones, one archived, and a couple with no license, description or topics that
bottom out at 15–25 — so every branch of the scoring heuristic and every badge
in the report renders.

Expected result: **avg quality 70.0, license coverage 66.7%, 4 stale,
1 archived**. If those numbers change, the scoring heuristic changed.

Regenerating the screenshots after a template change:

```bash
gha analyze --input examples/sample-portfolio.json --output reports/demo
# then screenshot reports/demo/report.html at 1440px wide into docs/images/
```
