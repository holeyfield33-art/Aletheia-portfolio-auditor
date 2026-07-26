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
   repository discovery, per-repo quality scoring, AI summaries, and
   cross-repo insights, rendered as an HTML dashboard.
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

- Repository discovery and metadata (`gha scan`)
- Per-repo quality scoring (license, description, topics, contributors,
  releases, activity)
- One-sentence AI repo summaries (Anthropic by default, or any
  OpenAI-compatible endpoint via `--provider openai`, with a plain metadata
  fallback if no key is set)
- Cross-repo insights: license coverage, stale/archived repos, repos sharing
  a dominant language
- Self-contained HTML dashboard report (JSON output also available:
  `portfolio.json`, `analysis.json`)

Not yet implemented (do not rely on these): CI/CD or security analysis,
merge/dedupe suggestions, action-plan generation, PDF export, and incremental
(cache-based) scanning - the `--incremental` flag is currently a no-op.

## Setup

```bash
pip install -e .
export GITHUB_TOKEN=ghp_...        # a PAT with repo read scope
export ANTHROPIC_API_KEY=sk-...    # optional, enables AI summaries

gha scan                            # writes reports/portfolio.json
gha analyze                         # writes reports/analysis.json + report.html
```

Run `gha scan --help` or `gha analyze --help` for all options.

### LLM providers for AI summaries

`gha analyze` mirrors [The Lie Detector](https://github.com/holeyfield33-art/Lie-Detector)'s
provider flags and env vars, so one `.env` configures the whole toolchain:

```bash
# Anthropic (default): uses ANTHROPIC_API_KEY
gha analyze

# Any OpenAI-compatible endpoint (OpenAI, Featherless, OpenRouter, local llama.cpp):
pip install -e ".[openai]"
gha analyze --provider openai --base-url https://api.featherless.ai/v1 --model <model-id>
```

The OpenAI provider reads `OPENAI_API_KEY` or `FEATHERLESS_API_KEY`, and
`--base-url` can also come from `OPENAI_BASE_URL`. With no credential for the
chosen provider, summaries fall back to a plain metadata sentence and are
flagged as not AI-generated — never faked. A failed API call mid-scan logs a
warning and falls back for that repo instead of aborting the run.

## Development

```bash
pip install -e ".[dev]"
pytest
```

See [docs/architecture.md](docs/architecture.md) for internals, and
[AUDIT.md](AUDIT.md) for the pre-launch audit log.

## License

MIT.
