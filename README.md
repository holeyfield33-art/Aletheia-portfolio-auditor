# Aletheia — portfolio auditor

**Proof, not vibes, for AI-built software.**

Aletheia scans your entire GitHub account, scores every repository, and tells
you exactly which ones need attention — the discovery stage of a three-tool
pipeline that ends in an evidence-backed truth badge on your README.

```bash
pip install -e .
gha scan          # discover every repo in your account
gha analyze       # score them and build the HTML portfolio report
```

## The pipeline

Aletheia is the front door to three standalone tools that answer three
different questions about a codebase:

```
 discover                triage                  verify
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────────┐
│ portfolio auditor│ →  │    vibe-check    │ →  │   The Lie Detector   │ → badge
│ which repos need │    │ what's wrong     │    │ does the repo do     │
│ attention?       │    │ with this repo?  │    │ what its README says?│
└──────────────────┘    └──────────────────┘    └──────────────────────┘
  account-level           offline, free,          sandboxed execution,
  reports + scores        deterministic           receipt-backed verdicts
```

1. **Aletheia portfolio auditor** (this repo) — walks your whole account:
   repository discovery, per-repo analysis (docs, stack, CI/CD, security),
   AI summaries, cross-repo insights, quality scoring, and action plans.
2. [**vibe-check**](https://github.com/holeyfield33-art/vibe-check) — a
   zero-dependency, offline scanner that flags the debt AI-assisted coding
   leaves behind (syntax errors, undeclared imports, typosquats, duplicated
   blocks, dead code) and emits a triage disposition: `FAST_TRACK`,
   `STANDARD_TRIAGE`, or `DEEP_AUDIT_REQUIRED`.
3. [**The Lie Detector**](https://github.com/holeyfield33-art/Lie-Detector) —
   extracts the factual claims from a README, turns each into a sandboxed
   pytest harness, executes it twice in a locked-down container, and
   adjudicates `PROVEN / FALSE / INCONCLUSIVE / UNTESTABLE` — producing an
   immutable verification receipt, an HTML Truth Report, and a
   [shields.io badge](https://github.com/holeyfield33-art/Lie-Detector#the-badge)
   anyone can independently re-verify.

The routing rule: run the auditor to find the repos worth polishing, run
vibe-check until a repo hits `FAST_TRACK`, then spend LLM time on the Lie
Detector to earn the badge. Every tool also works entirely on its own.

## The `aletheia` command

The package installs two entry points: `gha` (the auditor, unchanged) and
`aletheia`, one front door for the whole pipeline:

```bash
aletheia scan                 # = gha scan      (discover)
aletheia analyze              # = gha analyze   (score + report)
aletheia check ~/code/myrepo  # triage with vibe-check (offline, free)
aletheia verify https://github.com/you/yourrepo   # Lie Detector run
```

`check` and `verify` are thin wrappers: they find `vibe-check` /
`liedetector` on your PATH (or `VIBE_CHECK_PATH`), pass every extra flag
straight through, and print install instructions if the tool is missing.
Installing the other two tools is optional — the auditor works standalone.

## Auditor features

- Repository discovery and metadata for the whole account
- Per-repo analysis: docs, stack, CI/CD, security posture
- Code intelligence with AI summaries (Anthropic API key optional —
  falls back to plain metadata summaries without one)
- Cross-repo insights: duplicates, merge candidates, stale and archived repos
- Quality scoring, license coverage, and per-repo action plans
- Chart-based HTML report plus raw JSON output
- Incremental scanning with caching

## Setup

```bash
pip install -e .
export GITHUB_TOKEN=ghp_...        # a PAT with repo read scope
export ANTHROPIC_API_KEY=sk-...    # optional, enables AI summaries

gha scan                            # writes reports/portfolio.json
gha analyze                         # writes reports/analysis.json + report.html
```

See [docs/architecture.md](docs/architecture.md) for internals.

## License

MIT.
