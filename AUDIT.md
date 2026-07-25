# Pre-Launch Audit — GitHub Portfolio Auditor (`gha`)

Date: 2026-07-25
Base commit audited: `6da05c2`
Branch: `claude/portfolio-auditor-audit-41w3zo` (repo's assigned working branch;
substituted for the `audit/<date>` convention per this session's fixed
branch-naming requirement)
Environment: Python 3.11.15, fresh venv, `pip install -e .`

## Classification

**Python CLI / library.** Skipping frontend and API/auth phases (no server,
no exposed endpoints) — the tool is a local CLI (`gha scan`, `gha analyze`)
that calls the GitHub and Anthropic APIs as a client and writes local files.
The generated HTML report is static output, not a served app, but was still
checked for XSS since it renders GitHub-sourced (attacker-influenceable)
strings — see Phase 2.

## Phase 0/1 — Baseline

```
$ python3 -m venv venv && source venv/bin/activate
$ pip install -e .                     # clean install from README, succeeded
$ gha --help                           # OK, shows scan/analyze commands
$ gha scan --help                      # OK
$ gha analyze --help                   # OK
```
No test suite existed before this audit (`find . -iname "*test*"` → nothing).
Added `tests/` (see below); baseline after fixes:
```
$ pip install -e ".[dev]" && pytest tests/ -v
3 passed in 0.73s
```
No committed secrets found (`git log --all -p` scanned for GitHub/Anthropic/AWS
token patterns and private-key headers — no hits).
No `subprocess`/`os.system`/`eval`/`exec`/`pickle`/`shell=True` usage anywhere
in `src/` — no command-injection surface.

## Phase 2 — Core flow attack

Primary flow per README: `gha scan --token ... ` → `gha analyze --input
reports/portfolio.json`.

| Input | Result before fix | Result after fix |
|---|---|---|
| `gha scan --token invalidtoken123` (bad/expired token) | Unhandled `GithubException`, raw traceback to the user, exit 0 (misleading) | Friendly `Failed to fetch repositories: ...` message, exit 1 |
| `analyze` with `{"repositories": []}` | Works, 0/0/0 stats | Unchanged, still works |
| `analyze` with malformed JSON (`{"repositories": [invalid json`) | Unhandled `JSONDecodeError`, raw traceback, exit 1 | Unchanged (logged as P2 below, not fixed) |
| `analyze` with JSON missing `"repositories"` key | Unhandled `KeyError`, raw traceback, exit 1 | Unchanged (logged as P2, not fixed) |
| `analyze` with repo missing all optional fields (only `name`) | Works, scored 10/100 | Unchanged, still works |
| `analyze` with repo `description`/`topics` containing `<script>alert(1)</script>`, `'; DROP TABLE--`, `onerror=alert(2)`, emoji/unicode, 100KB string | Rendered into `report.html` — **all HTML-escaped correctly** by Jinja `autoescape=True`; JS array embeds via `\|tojson` also correctly escape `<`/`>` (`>`) so no `</script>` breakout | No change needed — not vulnerable |
| `analyze` with `last_commit: "not-a-date-at-all"` (malformed date, e.g. a hand-edited or partially-migrated `portfolio.json`) | Unhandled `ValueError`, **crashes the entire batch** including all other valid repos, exit 1 | Fixed: bad repo gets a note ("Unrecognized last_commit value") and is scored as if it had no commit history; rest of the batch unaffected |

Repro commands actually run (see history above) are preserved verbatim in this
session; key ones:
```
gha scan --token invalidtoken123 --output out
gha analyze --input portfolio.json --output out   # malformed JSON / missing key / bad-date fixtures constructed via Python and fed in
```

## Phase 3 — README claims verification

| Claim | Verdict | Evidence |
|---|---|---|
| "Repository discovery and metadata" | TRUE | `client.py get_repositories`/`get_repo_metadata`, exercised in Phase 1/2 |
| "Per-repo analysis (docs, stack, CI/CD, security)" | **FALSE** (P1) | `grep -ri "ci.?cd\|security" src/` → no matches. Only license/description/topics/contributors/releases/staleness are scored — no CI/CD or security analysis exists |
| "Code intelligence with AI summaries" | PARTIALLY TRUE, overstated | `summarize_repo` sends only name/description/languages/topics metadata to Claude for a one-sentence blurb — no actual source code is read. Real feature, misleading name |
| "Cross-repo insights (duplicates, merges)" | **PARTIALLY FALSE** (P1) | `duplicate_stacks` (grouping by dominant language) exists; `grep -ri "merge" src/` → no matches, no merge/dedupe suggestion feature exists |
| "Quality scoring and action plans" | **PARTIALLY FALSE** (P1) | Scoring exists (`score_repo`); `grep -ri "action.?plan" src/` → no matches, no action-plan generation exists |
| "Multiple output formats (HTML, PDF, JSON, etc.)" | **FALSE** (P1) | Only `report.html` and `*.json` are produced; `grep -ri "pdf" src/` → no matches |
| "Incremental scanning" | **FALSE** (P1) | `--incremental` flag is accepted in `cli.py` but never read anywhere else (`grep -i incremental src/` → one hit, the flag declaration itself). It is a pure no-op |

Per the audit rules, false claims in a launch README are P1. **Fixed** by
rewriting the README Features/Usage section to describe only what the code
actually does, and explicitly listing the not-yet-implemented items so users
don't rely on them.

## Fixed (P0/P1)

| # | Severity | Finding | Fix | Regression test | Repro (fails before fix / passes after) |
|---|---|---|---|---|---|
| 1 | P1 — broken core flow | `gha scan` crashes with a raw Python traceback (not a clean error) on any GitHub auth/network failure (bad token, revoked token, outage, rate limit) — a very realistic first-run scenario | `cli.py`: wrap `GitHubClient(token)` construction and `client.get_repositories()` in `try/except`, print a red one-line error, exit 1 | `tests/test_cli.py::test_scan_reports_friendly_error_on_client_failure` | `pytest tests/test_cli.py -v` — failed before (`AssertionError`, raw exception leaked out), passes after |
| 2 | P1 — broken core flow | `gha analyze` crashes entirely (`ValueError: Invalid isoformat string`) if **any single repo** in `portfolio.json` has a non-ISO `last_commit` value — losing the whole report instead of just flagging that repo. Realistic when `portfolio.json` is hand-edited, produced by an older schema, or the GitHub API returns an unexpected value | `analyzer.py score_repo`: catch `ValueError` from `datetime.fromisoformat`, add a note, treat as "no commit date" instead of crashing | `tests/test_analyzer.py::test_score_repo_with_malformed_last_commit_does_not_crash`, `test_analyze_portfolio_skips_bad_date_without_crashing_other_repos` | `pytest tests/test_analyzer.py -v` — failed before (`ValueError` propagated), passes after |
| 3 | P1 — false README claims | README advertised CI/CD analysis, security analysis, merge detection, action plans, PDF export, and incremental scanning — none of which exist in the code (see Phase 3 table) | Rewrote README Features section to match actual behavior; explicitly listed unimplemented items | N/A (doc fix, verified by `grep` showing zero matching code, re-pasted above) | — |

Full re-run of Phase 1 baseline after fixes: `pytest tests/ -v` → 3 passed;
`gha --help` / `gha scan --help` / `gha analyze --help` all still exit 0.

## Open findings (not fixed — logged per fix policy)

| # | Severity | Finding | Repro | Why not fixed now |
|---|---|---|---|---|
| 4 | P2 | `gha analyze` crashes with raw `JSONDecodeError` traceback on a truncated/malformed `portfolio.json` (e.g. if `gha scan` was killed mid-write — writes are not atomic, plain `open(file, "w")`) | `echo '{"repositories": [invalid json' > portfolio.json && gha analyze --input portfolio.json` → `JSONDecodeError`, exit 1 | Real bug, but input validation hardening beyond the two crash-the-whole-run bugs already fixed is scoped as P2 reliability work, not a P0/P1 blocker; needs a design decision (retry? clear re-scan message?) beyond a minimal diff |
| 5 | P2 | `gha analyze` crashes with raw `KeyError: 'repositories'` if the input JSON is valid but missing the `repositories` key | `echo '{"foo": "bar"}' > portfolio.json && gha analyze --input portfolio.json` → `KeyError`, exit 1 | Same as #4 — input validation, not core-flow-destroying under normal (non-tampered) usage |
| 6 | P2 | `client.py` calls `requests_cache.install_cache(...)` at **module import time**, globally monkey-patching `requests` process-wide as a side effect of `import github_portfolio_auditor.client` — surprising for anything else in the same process that uses `requests`/PyGithub without expecting caching | `python -c "import github_portfolio_auditor.client"` then inspect `requests.Session` — patched | Design smell, not a correctness bug for the CLI's own use; fixing means moving cache setup into `GitHubClient.__init__` — more than a trivial one-line change and out of scope for a ship-blocker pass |
| 7 | P3 | "Code intelligence with AI summaries" in README is misleading — summaries are generated from metadata only (name/description/languages/topics), never from actual source code | See Phase 3 table | Cosmetic wording; addressed partially by the README rewrite in fix #3, left as a minor residual naming nit |
| 8 | P3 | `docs/architecture.md` is a one-line stub ("See the full spec in the project root or conversation history") pointing at a spec that doesn't exist in the repo | `cat docs/architecture.md` | Docs polish, not launch-blocking |

## Unverified

- Behavior of `gha scan` against a **real, valid** GitHub token/account was
  not verified — this session's outbound network is proxied and returned a
  proxy-level 403 for all GitHub API calls rather than real GitHub responses,
  so only error-handling paths (not the happy-path scan-with-valid-token
  flow) could be exercised. The happy path is unit-covered indirectly by the
  `analyze` tests (which consume real-shaped `portfolio.json` output) but the
  `scan` → real API → `portfolio.json` write step itself needs a live-token
  smoke test before launch.
- Anthropic API summary generation (`analyzer.py summarize_repo` real API
  path, `is_ai=True` branch) was not exercised against the live Anthropic API
  in this session (no key configured) — only the no-key fallback path was
  tested.
- Rate-limit and pagination behavior of `client.get_repositories()` /
  `PyGithub`'s automatic pagination against a large (100+ repo) real account
  was not tested.

## Stop condition

Baseline green (`pytest` 3/3, `--help` commands exit 0) · core flow (`scan`
error paths, `analyze` with empty/partial/malformed-date/XSS-payload input)
survives Phase 2 attacks without crashing or rendering unescaped content ·
all identified P0/P1s fixed with passing regression tests · P2/P3 logged
above with real repro commands. No P0 (secrets/injection/auth/data-loss)
findings were found. Stopping here per directive — not hunting further P3s.
