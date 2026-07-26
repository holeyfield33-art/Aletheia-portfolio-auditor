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

---

# End-to-End Audit — 2026-07-26

Date: 2026-07-26
Base commit audited: `987987f`
Branch: `claude/e2e-audit-docs-update-qo8zkl`
Environment: Python 3.11.15, fresh `.venv`, `pip install -e ".[dev]"`
Scope: full end-to-end run of every documented command, plus a docs pass.

## Phase 0 — Baseline

```
$ python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"   # clean, succeeded
$ .venv/bin/pytest -q                                          # 1 FAILED, 11 passed
$ gha --help / scan --help / analyze --help                    # all exit 0
$ aletheia --help / check --help / verify --help               # all exit 0
```

**The documented dev flow was red on a clean checkout** — see finding 1.

## Phase 1 — Every documented command, run for real

| Command | Result |
|---|---|
| `gha scan` (valid token, live) | **Unverified** — this session's proxy rejects `GET /user/repos` with a 403 (`sessions are bound to their configured repositories`). Error path handled cleanly; happy path still untested against live GitHub. |
| `gha scan --token badtoken123` | Clean one-line error, exit 1 ✅ |
| `gha scan --username holeyfield33-art` | Clean one-line error, exit 1 (same proxy block) ✅ |
| `gha analyze` (missing input) | `No portfolio data found ... Run 'gha scan' first`, exit 1 ✅ |
| `gha analyze` (truncated JSON) | Raw `JSONDecodeError` traceback → **finding 2** |
| `gha analyze` (JSON without `repositories`) | Raw `KeyError` traceback → **finding 3** |
| `gha analyze` (empty portfolio) | Renders a 0/0/0 report, exit 0 ✅ |
| `gha analyze --provider grok` | `unknown provider 'grok' ...`, exit 1 ✅ |
| `gha analyze` (12-repo sample portfolio) | avg 70.0, coverage 66.7%, 4 stale, 1 archived, exit 0 ✅ |
| `aletheia check .` (no vibe-check) | Install instructions, exit 2 ✅ |
| `aletheia verify <url>` (no liedetector) | Install instructions, exit 2 ✅ |

## Phase 2 — Report rendering, verified in a real browser

Rendered `report.html` was loaded in headless Chromium with request
interception, which surfaced finding 4 directly: two requests failed and the
charts did not draw.

## Fixed

| # | Severity | Finding | Fix | Regression test |
|---|---|---|---|---|
| 1 | P1 — documented flow is broken | `pip install -e ".[dev]" && pytest` (the README's Development section) **fails on a clean checkout**: `test_build_summary_client_openai_reads_featherless_key_and_base_url` needs the `openai` SDK, which lives in the separate `[openai]` extra | `pytest.importorskip("openai")` in that test | Verified both ways: `[dev]` → 19 passed, 1 skipped; `[dev,openai]` → 20 passed |
| 2 | P2→fixed | `gha analyze` dumps a raw `JSONDecodeError` traceback on a truncated `portfolio.json` (realistic: `scan` writes non-atomically, so any interrupted scan produces one). Was logged as open finding #4 in the previous audit | `cli.py`: catch `JSONDecodeError`, print the file, the parse error, and "re-run `gha scan`", exit 1 | `test_analyze_rejects_truncated_json_without_traceback` |
| 3 | P2→fixed | `gha analyze` dumps a raw `KeyError: 'repositories'` on valid JSON that isn't a portfolio file. Previous audit's open finding #5 | `cli.py`: validate the envelope (dict with a `repositories` list) before use, exit 1 with an actionable message | `test_analyze_rejects_json_without_repositories_key`, `test_analyze_rejects_repositories_of_wrong_type` |
| 4 | P1 — false README claim | README claimed a "**self-contained** HTML dashboard report". It was not: the template pulled Chart.js from cdnjs and webfonts from Google Fonts. Offline, air-gapped, or emailed-to-someone-else, **every chart silently failed to render** — the report degraded to a bare table with no indication anything was missing. Confirmed in headless Chromium: 2 failed requests, 0 charts drawn | Vendored Chart.js v4.4.4 (MIT) into `templates/vendor/` and inlined it into every report; replaced the webfont link with system font stacks; added `templates/vendor/*.js` to `package-data` | `test_report_has_no_external_resource_references` asserts zero `http(s)://` `src`/`href` in the output. Re-verified in the browser: **0 failed requests, 4 charts drawn** |
| 5 | P3 — presentation | Every chart card stretched to the height of the tallest (the doughnut), leaving ~40% dead space in the three bar charts | Fixed-height `.chart-wrap` + `maintainAspectRatio: false`; 2×2 grid at `minmax(420px, 1fr)`; integer ticks on the language axis; `overflow-x` wrapper on the table for narrow screens | Visual, captured in `docs/images/` |
| 6 | P3 — docs | `docs/architecture.md` was a one-line stub pointing at a spec not in the repo. Previous audit's open finding #8 | Rewritten: data-flow diagram, module table, the `portfolio.json` contract, four design decisions, and a known-rough-edges list | — |

Also added, to close the "no reproducible demo" gap: `examples/sample-portfolio.json`
(12 synthetic repos exercising every scoring branch and every report badge),
`examples/README.md`, `docs/demo.md`, and `docs/images/` screenshots generated
from that dataset.

## Security re-check

- `templates/vendor/chart.umd.min.js` is inlined via `{{ chartjs|safe }}`. It
  is a vendored build artifact, not user data. Verified it contains zero
  `</script` sequences, so it cannot break out of the `<script>` block.
- Re-confirmed the previous audit's XSS finding still holds after the template
  rewrite: hostile repo names/descriptions (`</script><img src=x onerror=...>`,
  `<script>alert('xss')</script>`) are escaped in both the HTML and the
  `|tojson` data arrays — now asserted by
  `test_report_escapes_hostile_repo_metadata` rather than checked by hand.

## Final state

```
$ .venv/bin/pytest -q
20 passed
$ .venv/bin/pytest -q          # without the [openai] extra
19 passed, 1 skipped
```

## Still unverified

- **`gha scan` against live GitHub with a valid token.** Same limitation as the
  previous audit: the sandbox proxy blocks `/user/repos` and `/users/*/repos`.
  Only error paths were exercised. This remains the one untested link in the
  chain and needs a real-token smoke test.
- **The Anthropic provider** specifically. The `openai` provider path is now
  verified end to end (see below), but `AnthropicSummaryClient` still has no
  live run behind it.
- **Rate-limit and pagination behaviour** on an account with 100+ repos.

## Open findings (not fixed)

| # | Severity | Finding | Why not fixed |
|---|---|---|---|
| 7 | P2 | `requests_cache.install_cache()` still runs at `client.py` import time, monkey-patching `requests` process-wide. Previous audit's finding #6 | Unchanged assessment: a design smell, not a correctness bug for the CLI. Moving it into `GitHubClient.__init__` changes caching semantics for any existing embedder |
| 8 | P2 | `gha scan` writes `portfolio.json` non-atomically, so an interrupted scan still corrupts the file — `analyze` now reports it clearly (finding 2) but `scan` should write to a temp file and rename | Detection was the user-visible half; the atomic-write fix belongs with a broader `scan` resilience pass (resume, rate-limit backoff) |
| 9 | P3 | `--incremental` remains an accepted no-op | Documented as a no-op in the README options table and the architecture doc rather than silently ignored |

## Addendum — live LLM provider run (2026-07-26)

The `openai` provider path, listed as unverified above, was subsequently
exercised against a real OpenAI-compatible endpoint.

```
$ export FEATHERLESS_API_KEY=rc_...
$ gha analyze --input examples/sample-portfolio.json --output <out> \
              --provider openai \
              --base-url https://api.featherless.ai/v1 \
              --model google/gemma-4-26B-A4B-it
Avg quality score: 70.0 | License coverage: 66.7%
real  0m25.781s
$ jq .insights.ai_summaries_generated <out>/analysis.json
12
```

| Check | Result |
|---|---|
| `--provider openai` + `--base-url` + `--model` reach a third-party endpoint | ✅ 12/12 repos summarised, `summary_is_ai: true` throughout |
| `FEATHERLESS_API_KEY` picked up without `OPENAI_API_KEY` set | ✅ |
| Report `AI Summaries` stat reflects real calls only | ✅ reads 12, was 0 on the keyless run |
| Throughput | 12 sequential calls in ~26s (~2.2s/repo); no batching or concurrency |
| Report still network-free with AI summaries present | ✅ 0 failed requests, 4 charts, re-verified in headless Chromium |
| API key leakage into `analysis.json` / `report.html` / repo files | ✅ none (`grep -rl` for the key across all outputs and tracked files: no hits) |

Screenshots in `docs/images/` were regenerated from this run, so they show
real model output rather than metadata fallbacks.

### New finding

| # | Severity | Finding | Status |
|---|---|---|---|
| 10 | P2 — misleading output | **Summaries for repos with no description are confabulated from the repo name and presented in the same confident voice as grounded ones.** `scrape-lab` (no description, no topics, languages `{"Python": 42000}`) got *"provides a Python-based tool for web scraping and data extraction experiments"* — inferred entirely from the eleven-character repo name. `webgl-toys` behaved the same way. The report gives the reader no signal that one summary is grounded in a real description and another is a guess | Documented, not code-fixed. `summary_is_ai` distinguishes AI from fallback but **not** grounded-AI from inferred-AI. README now carries an explicit "read AI summaries as guesses, not findings" section pointing readers at the `No description` note in the same row. A real fix would either pass the description's absence to the model as a constraint, or flag inferred summaries in the report UI — both are product decisions beyond this audit |

This matters more here than it would elsewhere: the project's stated premise is
"proof, not vibes", and this is the one column in the report that is vibes.
