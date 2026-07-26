# Running a demo

The demo is not "here are my features." It's **one uncomfortable question,
answered with a number, in five minutes**:

> *You have 40 repos. Which four are worth showing anyone, and which one is
> quietly lying in its README?*

That question is the whole product. The auditor answers the first half; the
pipeline answers the second. Everything below serves that arc.

## Pick your version

| Version | Length | Use when |
|---|---|---|
| **A. Sample data** | 2 min | Recorded demo, conference talk, README GIF. Deterministic, no keys, no network, never rate-limited. |
| **B. Your real account** | 5 min | Live 1:1s, investor/hiring conversations. Far more convincing — it's *your* mess on screen. |
| **C. Full pipeline** | 10 min | You're pitching Aletheia the *suite*, not the auditor. Needs vibe-check and the Lie Detector installed. |

Do **A** first even if you're planning **B**. It's your fallback when the
network dies.

## Before you start (5 minutes, once)

```bash
git clone https://github.com/holeyfield33-art/Aletheia-portfolio-auditor
cd Aletheia-portfolio-auditor
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
pytest                                   # sanity: 20 passed

export GITHUB_TOKEN=ghp_...              # version B only

# Optional, makes summaries real. Either provider works:
export ANTHROPIC_API_KEY=sk-ant-...
# ...or any OpenAI-compatible endpoint (verified working):
export FEATHERLESS_API_KEY=rc_...
```

With a key, add these flags to every `analyze` below — 12 repos takes about
25 seconds:

```bash
--provider openai --base-url https://api.featherless.ai/v1 \
--model google/gemma-4-26B-A4B-it
```

Then, critically — **pre-run the scan**:

```bash
gha scan --output demo-run              # do this BEFORE the audience is watching
```

`scan` is the slow part (≈4 API calls per repo, and it can hit rate limits).
Never make an audience watch it. You'll re-run `analyze` live, which takes
seconds and is where all the visible payoff is.

Have `demo-run/portfolio.json` on disk and a terminal ready with a large font.

---

## Version A — sample data (2 minutes)

```bash
gha analyze --input examples/sample-portfolio.json --output reports/demo
open reports/demo/report.html
```

**Say:** "Twelve repos, one command, no config. Average quality 70, license
coverage 67%, four stale, one archived."

**Then scroll to the table and land the actual point:** every score has a
*reason* next to it. `webgl-toys` scores 15 and the notes say exactly why —
no license, no description, no topics, single contributor, no releases, no
commits in 341 days. "This isn't a vibe. It's a list of five things to fix,
and it took nine seconds."

## Version B — your real account (5 minutes)

**0:00 — the setup.** Terminal only, no slides.

> "I've built a lot of software with AI in the loop. I genuinely could not
> tell you which of my repos are presentable. Let's find out."

**0:20 — run analyze on the pre-scanned data.**

```bash
gha analyze --input demo-run/portfolio.json --output demo-run
```

Let the summary lines land:

```
✅ Phase 2 Analysis complete!
Avg quality score: 62.4 | License coverage: 41.0%
Stale repos: 17 | Archived: 3
```

> "Forty-one percent licensed. Seventeen repos I haven't touched in six
> months. I did not know that thirty seconds ago."

**1:00 — open the report.**

```bash
open demo-run/report.html
```

Charts first (the shape of the portfolio), then the table (the specifics).

**2:00 — the pivot.** Point at your top-scoring repo.

> "So this one wins. High score, licensed, active, described. But every signal
> here is *metadata*. Nothing has looked at a single line of code, and nothing
> has checked whether the README is true. That's the next two tools."

**3:00 — hand off.** If you're not doing Version C, this is where you say what
vibe-check and the Lie Detector do and stop. If you are, keep going.

**4:00 — close on the honest bit.** Scroll to the "not yet implemented" list
in the README on screen.

> "The README tells you what this doesn't do. That's the entire ethos —
> the tool that scores your honesty ships with its own limitations documented."

That's the moment people remember. Don't skip it.

## Version C — the full pipeline (10 minutes)

Continue from Version B at 3:00, using your *worst-scoring interesting* repo:

```bash
aletheia check ~/code/that-repo                        # triage: what's wrong
aletheia verify https://github.com/you/that-repo       # verify: is the README true
```

Pre-run `verify` too — it builds a container and makes LLM calls, and you do
not want to narrate a Docker pull. Show the saved Truth Report and the badge.

The arc to hold onto: **discover → triage → verify → badge.** Which repos
matter, what's broken in this one, and whether it does what it claims.

---

## Demo hygiene

- **Pre-run everything that touches the network.** `scan` and `verify`. Live-run
  only `analyze` and `check`.
- **Have the sample-data report open in a background tab.** If anything fails,
  switch to it and keep talking.
- **Don't demo an empty account.** Zero repos renders correctly and lands
  terribly. Use sample data instead.
- **Delete `github_cache.sqlite` after a demo** if you're about to re-scan for
  real — responses are cached for an hour.
- **Reports are portable.** `report.html` is a single file with no network
  dependencies, so you can email it to someone after the call and it renders
  exactly as they saw it.
- **Don't overclaim in the room.** The tool scores metadata, not code. Saying
  so out loud is what makes the next two tools sound necessary rather than
  redundant.
- **Know which column is soft.** If someone asks how the summaries work, the
  honest answer is that a repo with no description gets a summary the model
  guessed from its name. Volunteer it before you're caught by it — in the
  sample report, `scrape-lab` is exactly that case. Scores and notes are
  computed from real metadata; the summary column is a convenience.

## Recording it

For a README GIF or a 60-second clip, Version A with `asciinema` or a terminal
recorder:

1. `gha analyze --input examples/sample-portfolio.json --output reports/demo`
2. Cut to the rendered report.
3. Scroll from the stat row to the table, and stop on a low-scoring repo with
   its notes visible.

Three beats, no narration needed. The notes column does the talking.
