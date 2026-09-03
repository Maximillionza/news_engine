# Automatic Actuals Fallback (Cloud-Assisted) — Design

**Date:** 2026-09-03
**Status:** Approved via conversational brainstorm (architectural path)
**Builds on:**
- `scripts/fill_missing_actuals.py` — the existing manual, agent-run WebSearch fallback this spec makes hands-off. That script, its `FillReport`/`run()` function, and its "real data or absent, never guessed" discipline are reused, not replaced.
- `webapp/store.py`'s `get_events_with_stale_missing_actual()` (grace period recently lowered 6h → 1h, 2026-09-02) — the exact query this spec's export step calls to build its candidate list.
- The `country` column fix (2026-09-03) — `get_events_with_stale_missing_actual()` stays permissive on `country` by design (manual-research list, human-reviewed); this spec's cloud routine is NOT human-reviewed per entry, so its own correctness depends entirely on the local export step already scoping candidates to `EVENT_SURPRISE_DIRECTION` (USD-only titles).

## Problem

`scripts/fill_missing_actuals.py` closes real gaps, but only when a human or an interactive agent session notices a stale candidate and runs it by hand — nothing on this machine can call WebSearch unattended (`webapp/scheduler.py`'s background loop cannot, same limitation that motivated the FRED fallback and this script's own existence). The user's own words: "this engine requires a lot of maintenance to function normally... there shouldn't be stale events older than 3 hours with missing information." A background *cloud* agent session genuinely can call WebSearch on a schedule — but it runs against a clone of a git repo, with **no path to this machine's live SQLite database in either direction**. Closing that gap is the whole of this spec.

## Scope boundary

- Only closes the gap for titles the *local* side already trusts as USD-scored — the queue this spec exports is built from `get_events_with_stale_missing_actual()`, unchanged, so every existing exclusion (title outside `EVENT_SURPRISE_DIRECTION`, structurally text-only, still within the grace period) applies identically here. No change to what counts as "a real candidate."
- Only the `actual` field, same as `fill_missing_actuals.py` — forecast/previous/timing/impact stay untouched.
- The cloud routine only attempts candidates whose `event_time_utc` is **under 48 hours old** at export time — older gaps are the existing manual/backdate workflow's job (this session's own 3-month backfill), not a search a 2-hourly automated pass should keep retrying indefinitely.
- No change to the FRED fallback (`data_layer/fred_actuals.py`) or its ~10-title coverage — this spec is strictly additive, for titles FRED doesn't cover.
- Git credential setup (a Personal Access Token registered with Git Credential Manager on this machine) is an explicit **prerequisite the user configures themselves** — this spec's local code assumes it's already in place and fails open (logs, retries next cycle) if it isn't yet.
- The dedicated sync clone (`webapp/.actuals_sync/repo/`) is entirely separate from this monorepo's own git history and from the `News_Engine2` GitHub repo's own use as a readable mirror of the news_engine source — this spec's automation touches only two JSON files in that repo, never the source tree.

## Architecture

Three new pieces:

### 1. Local export — `webapp/actuals_sync.py`

```python
def export_stale_queue(conn, repo_dir: Path, now: Optional[dt.datetime] = None) -> bool:
    """
    Builds the current stale-missing-actual candidate list (via
    webapp.store.get_events_with_stale_missing_actual(), unchanged) and
    writes it to <repo_dir>/data_layer/pending_actuals_queue.json,
    filtered to event_time_utc within the last 48 hours. Always
    OVERWRITES the full file (never appends) -- it's a snapshot of
    current DB state, not a log. Commits and pushes only if the
    serialized content actually changed from what's already committed
    (same "store and use as current until new information supersedes
    this" discipline webapp/store.py's save_calendar_snapshot_if_changed()
    already uses). Returns True if a push happened, False otherwise.
    Never raises -- fails open, logs, and lets the next cycle retry.
    """
```

Queue file schema (`data_layer/pending_actuals_queue.json`):
```json
{
  "generated_at_utc": "2026-09-03T10:00:00+00:00",
  "candidates": [
    {"event_title": "PPI m/m", "event_time_utc": "2026-09-02T12:30:00+00:00", "forecast": "0.2%", "previous": "0.1%"}
  ]
}
```

### 2. Cloud routine — scheduled via this platform's `RemoteTrigger`, no new repo code

Runs every 2 hours (`0 */2 * * *`), model `claude-sonnet-5`, source repo `https://github.com/Maximillionza/News_Engine2`, `allowed_tools: ["Read", "Write", "Bash"]`. Self-contained prompt (the cloud session starts with zero context, so this is the entire spec it needs):

> You are a data-research agent for the news_engine project. Your repo has two files: `data_layer/pending_actuals_queue.json` (candidates needing a real actual figure) and `data_layer/resolved_actuals_inbox.json` (append-only, your own output — create it with `{"entries": []}` if it doesn't exist yet).
>
> For each candidate in the queue's `candidates` list:
> 1. Skip it if the inbox's `entries` already has a matching `(event_title, event_time_utc)` pair — already researched, don't repeat.
> 2. Otherwise, use WebSearch to find the REAL, cited actual value for this US economic release (the event's `forecast`/`previous` are given for context; `event_time_utc` is when it published). Only proceed on a real, attributable source (BLS, Census Bureau, Federal Reserve, or a reputable financial outlet citing the release) — never fabricate or guess a plausible-sounding number.
> 3. If found, append ONE new entry to the inbox's `entries` array (never modify or remove any existing entry) with: `event_title`, `event_time_utc` (copied exactly from the queue entry), `actual` (matching the forecast/previous format style, e.g. `"0.3%"` or `"203K"`), `source_note` (a real citation: publication + URL), `researched_at_utc` (current UTC time).
> 4. If no reliable real value turns up after a genuine search, skip it — leave it for the next run, never fabricate.
>
> Never modify `pending_actuals_queue.json` — it's owned by a separate local process. If you added any new entries, commit with a clear message and push to `origin/master`. If nothing new was found, make no commit at all.

Inbox file schema (`data_layer/resolved_actuals_inbox.json`):
```json
{
  "entries": [
    {
      "event_title": "PPI m/m", "event_time_utc": "2026-09-02T12:30:00+00:00",
      "actual": "0.3%", "source_note": "BLS official release, https://www.bls.gov/...",
      "researched_at_utc": "2026-09-03T10:05:00+00:00"
    }
  ]
}
```

### 3. Local apply — `webapp/actuals_sync.py`

```python
def apply_resolved_inbox(conn, repo_dir: Path, now: Optional[dt.datetime] = None) -> FillReport:
    """
    Pulls repo_dir, reads data_layer/resolved_actuals_inbox.json (absent
    or malformed -> treated as empty, never an error), and for each entry
    whose event_history row still has actual IS NULL, writes it via the
    exact same path scripts/fill_missing_actuals.py's run() uses --
    upsert_event_history(conn, event, classify_surprise(event), now,
    source="cloud_web_fallback") -- a new, distinct source value (never
    collapsed into "live_web_fallback", matching this project's "never
    collapse provenance to a boolean" convention). An entry whose row is
    already resolved (by ANY source -- a live fetch, a human running
    fill_missing_actuals.py by hand, or a prior cycle of this same
    function) is silently skipped, same "first-writer-wins" contract
    upsert_event_history() already enforces -- safe to re-read the same
    append-only inbox file forever. Returns the same FillReport shape
    fill_missing_actuals.run() does. Never raises.
    """
```

### Required side-effect fix — `webapp/history.py`

`build_print_call_history()`'s source-precedence chain (both the numeric print-call branch and the accumulator-prediction fallback branch added 2026-09-02) explicitly enumerates `"seeded"` / `"live_web_fallback"` / `"fred"` and falls through to `"live"` for anything else — a `source="cloud_web_fallback"` row would silently mislabel as `"live"` there, the exact "collapse to a boolean/short list" this codebase's own comment on that chain explicitly warns against. Both `if`/`else` chains need a new explicit `"cloud_web_fallback"` branch (ranked the same tier as `"live_web_fallback"` — both are a WebSearch-researched real citation, just attributed to a different research path — checked before `"fred"`, after `"seeded"`), so the History tab's `source` field keeps genuinely distinguishing all five values now, never silently re-labeling the newest one as `"live"`.

`webapp/static/app.js`'s History-tab badge (`sourceBadge`, line ~850) only special-cases `"seeded"` and `"live_web_fallback"` today — `"fred"` already shows no badge at all (pre-existing gap, not introduced by this spec) and `"cloud_web_fallback"` would fall into that same no-badge case. Left as an optional, non-blocking polish item for the implementation plan — the `source` field itself is still correct and queryable either way, this only affects a cosmetic label.

### Local integration point — `webapp/app.py`

```python
from webapp.actuals_sync import start_actuals_sync
# ... alongside the existing start_scheduler(_get_tracked_symbols) call:
start_actuals_sync()
```

`start_actuals_sync()` mirrors `webapp/scheduler.py`'s `start_scheduler()` exactly: a daemon thread, an infinite loop, a fixed 30-minute sleep between cycles, and the same broad fail-open `except Exception` around the whole cycle body (log, sleep, retry — never let one bad git/DB operation kill the thread). Each cycle: ensure the dedicated clone at `webapp/.actuals_sync/repo/` exists (`git clone` if not), `git pull`, run `apply_resolved_inbox()`, run `export_stale_queue()`.

## Data Flow

```
webapp.store.get_events_with_stale_missing_actual()   [unchanged, existing query]
  → export_stale_queue()   [webapp/actuals_sync.py, every 30 min]
      → data_layer/pending_actuals_queue.json   [committed + pushed to News_Engine2, only if changed]
        → (cloud) RemoteTrigger routine, every 2h
            → WebSearch per un-researched candidate
            → data_layer/resolved_actuals_inbox.json   [append-only, pushed only if something new was found]
              → apply_resolved_inbox()   [webapp/actuals_sync.py, every 30 min, next local cycle]
                  → webapp.store.upsert_event_history(source="cloud_web_fallback")
```

## Error Handling

- Every git subprocess call runs with `GIT_TERMINAL_PROMPT=0` in its environment — a credentials gap (PAT not yet configured) fails immediately with a non-zero exit, never hangs the daemon thread waiting for a prompt that can never arrive headlessly.
- No merge conflicts by construction: the local process only ever writes `pending_actuals_queue.json`; the cloud routine only ever writes `resolved_actuals_inbox.json`. Each side pulls before it writes its own file, so two commits touching disjoint files merge trivially.
- `apply_resolved_inbox()` treats a missing or malformed inbox file as `{"entries": []}` — never an error, matching "absent is a valid state, not a crash" everywhere else in this codebase.
- The 48-hour cutoff is enforced ONLY at export time (`export_stale_queue()`) — the cloud routine has no independent age check and doesn't need one, since it only ever sees what's currently in the queue.
- A push rejected because the remote advanced (the other side committed in between) is handled by one pull-and-retry, not an unbounded loop — if it still fails, the cycle logs and moves on; the next 30-minute cycle tries again with fresh state.

## Testing

- `tests/test_actuals_sync.py` (new): `export_stale_queue()`'s JSON schema and 48h-cutoff filtering (mocking `get_events_with_stale_missing_actual()`, a temp queue file, asserting exact serialized content and the no-op-when-unchanged behavior); `apply_resolved_inbox()`'s idempotent apply (a fixture inbox file, a temp DB with a mix of still-pending and already-resolved rows, asserting only the pending ones get written, with `source="cloud_web_fallback"`, and that a missing/malformed inbox file is treated as empty, not an error).
- Git operations (`_git_pull`, `_git_commit_and_push`, clone-if-missing) are small, separately mockable functions — no test invokes real git, network, or credentials, mirroring how `scripts/fill_missing_actuals.py`'s own tests avoid real WebSearch calls.
- No test for the cloud routine itself — it's a prompt, not code in this repo; its behavior is verified by the platform's own routine-run logging (`RemoteTrigger`'s `list_runs`/`get_run_log`), not by this project's test suite.

## Explicitly out of scope

- **Any change to `get_events_with_stale_missing_actual()`'s own filtering** (title set, grace period, country permissiveness) — this spec is purely a new consumer of that existing, unchanged query.
- **Retrying candidates older than 48 hours automatically** — deliberately left to the existing manual/backdate workflow; see Scope boundary.
- **A UI or dashboard surface for `pending_actuals_queue.json`/`resolved_actuals_inbox.json`** — these are pure plumbing files, never displayed anywhere; the *result* (a filled `actual`) is what already surfaces everywhere `event_history` is read (dashboard, History tab, precursor links).
- **Automating the git credential setup itself** (PAT generation, Git Credential Manager registration) — the user's own explicit choice this session; this spec's code assumes it's done and fails open, with a clear log line, if it isn't.
- **Reusing `News_Engine2`'s repo for anything beyond these two JSON files** — no source-code sync, no CI, no other automation piggybacks on this channel.
