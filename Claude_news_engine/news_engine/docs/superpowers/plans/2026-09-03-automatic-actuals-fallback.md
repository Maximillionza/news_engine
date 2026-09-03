# Automatic Actuals Fallback (Cloud-Assisted) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the "stale missing actual" gap automatically — a new local module exports the current stale-candidate list to a dedicated git repo, a scheduled cloud agent routine researches real cited actuals via WebSearch and appends them to a second file in that same repo, and the local module applies them back into the live dashboard database, all without a human running `fill_missing_actuals.py` by hand.

**Architecture:** `webapp/actuals_sync.py` is a new module with three responsibilities — small git-subprocess helpers, `export_stale_queue()` (writes the current stale candidates, unchanged query, to a tracked JSON file), and `apply_resolved_inbox()` (reads a second, cloud-written, append-only JSON file and writes any new real actuals into `event_history`). Both are driven by a `start_actuals_sync()` daemon-thread loop, started alongside the existing scheduler in `webapp/app.py`. The cloud side is not code in this repo — it's a scheduled routine (created directly via this platform's scheduling tool, not part of this plan's tasks) that reads/writes the same two files in a separate GitHub repo (`https://github.com/Maximillionza/News_Engine2`) dedicated to this sync channel.

**Tech Stack:** Python 3, `subprocess` (git CLI calls), `json`, `sqlite3` (via `webapp/store.py`'s existing connection), pytest-discoverable test functions with the `print("PASS")` convention this codebase uses throughout.

**Spec:** `docs/superpowers/specs/2026-09-03-automatic-actuals-fallback-design.md`

## Global Constraints

- Only `actual` is ever written by this feature — forecast/previous/timing/impact stay untouched, matching `scripts/fill_missing_actuals.py`'s existing scope.
- The cloud routine only ever attempts candidates under 48 hours old — enforced ONLY at export time (`MAX_CANDIDATE_AGE_HOURS = 48.0` in `webapp/actuals_sync.py`); the cloud routine itself has no independent age check.
- Local writes `data_layer/pending_actuals_queue.json` only; the cloud routine writes `data_layer/resolved_actuals_inbox.json` only — never the reverse, by construction (no merge-conflict handling needed beyond a plain pull-before-write).
- Every git subprocess call runs with `GIT_TERMINAL_PROMPT=0` in its environment — a credentials gap must fail fast, never hang.
- New writes from this feature use `source="cloud_web_fallback"` — a distinct value, never collapsed into `"live_web_fallback"` or `"live"` anywhere it's read back (this is the exact class of bug this plan's Task 1 exists to prevent).
- No test in this plan invokes real git, network, or credentials — git-subprocess calls are small, separately mockable functions, monkeypatched in every test.
- Git credential setup (a Personal Access Token registered with Git Credential Manager) is a user-side prerequisite this plan's code assumes is already in place; every git failure path (including "not configured yet") must fail open — log and let the next 30-minute cycle retry, never crash the thread.

---

### Task 1: `webapp/history.py` — recognize `cloud_web_fallback` as its own source

**Files:**
- Modify: `webapp/history.py:206-212` (accumulator-prediction fallback branch), `webapp/history.py:251-256` (numeric print-call branch)
- Test: `tests/test_webapp_history.py` (extend)

**Interfaces:**
- Consumes: nothing new — this task only extends two existing `if`/`elif`/`else` chains already reading `event.source`/`call.source`/`prediction.source` (plain strings).
- Produces: `HistoryRow.source` can now be `"cloud_web_fallback"`, read by later tasks' own understanding of provenance (no function signature changes).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_webapp_history.py` (uses the file's existing `_resolved_event()` helper, `store`, `backtest_store`, `PrintCall` imports already present):

```python
def test_numeric_row_recognizes_cloud_web_fallback_source():
    print("=== webapp/history: HistoryRow.source recognizes 'cloud_web_fallback' on the numeric print-call path, never collapsed to 'live' ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("Core CPI m/m", event_time, "0.2%", "0.0%", "0.2%"),
            "in_line", now=event_time, source="cloud_web_fallback",
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_print_prediction_if_changed(
            bt_conn, "Core CPI m/m", event_time,
            PrintCall(direction="lower", confidence=0.51, article_count=89), now=event_time, source="live",
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert rows[0].source == "cloud_web_fallback"
    print("PASS\n")


def test_fallback_row_recognizes_cloud_web_fallback_source():
    print("=== webapp/history: HistoryRow.source recognizes 'cloud_web_fallback' on the accumulator-prediction fallback path too ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("CPI m/m", event_time, "0.1%", "-0.4%", "0.4%"),
            "higher", now=event_time, source="cloud_web_fallback",
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        # No print_predictions row at all -- exercises the fallback branch.
        backtest_store.record_prediction(
            bt_conn, "CPI m/m", "XAUUSD", event_time,
            0.7, "bearish", 0.6, 40, False, scored_at_utc=event_time,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert len(rows) == 1
        assert rows[0].source == "cloud_web_fallback"
    print("PASS\n")
```

Add both calls to the `if __name__ ==` block at the bottom of the file, after the existing `test_history_row_carries_fred_source_intact()` call.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_webapp_history.py -v -k cloud_web_fallback`
Expected: both FAIL — `assert rows[0].source == "cloud_web_fallback"` fails because the current code falls through to `"live"` for any unrecognized source value.

- [ ] **Step 3: Add the `cloud_web_fallback` branch to both source-precedence chains**

In the accumulator-prediction fallback branch (around `webapp/history.py:206`), change:

```python
                        source=(
                            "seeded" if "seeded" in (event.source, prediction.source)
                            else "live_web_fallback" if "live_web_fallback" in (event.source, prediction.source)
                            else "fred" if "fred" in (event.source, prediction.source)
                            else "live"
                        ),
```

to:

```python
                        source=(
                            "seeded" if "seeded" in (event.source, prediction.source)
                            else "live_web_fallback" if "live_web_fallback" in (event.source, prediction.source)
                            else "cloud_web_fallback" if "cloud_web_fallback" in (event.source, prediction.source)
                            else "fred" if "fred" in (event.source, prediction.source)
                            else "live"
                        ),
```

In the numeric print-call branch (around `webapp/history.py:251`), change:

```python
                source=(
                    "seeded" if "seeded" in (event.source, call.source)
                    else "live_web_fallback" if "live_web_fallback" in (event.source, call.source)
                    else "fred" if "fred" in (event.source, call.source)
                    else "live"
                ),
```

to:

```python
                source=(
                    "seeded" if "seeded" in (event.source, call.source)
                    else "live_web_fallback" if "live_web_fallback" in (event.source, call.source)
                    else "cloud_web_fallback" if "cloud_web_fallback" in (event.source, call.source)
                    else "fred" if "fred" in (event.source, call.source)
                    else "live"
                ),
```

Also update the comment immediately above the numeric print-call branch's chain (the one explaining "must genuinely distinguish all four values") to say "all five values" and mention `cloud_web_fallback` alongside the existing three, for the same reasons `live_web_fallback`/`fred` are already documented there (it only ever lands in `event_history`, never in `call.source`/`prediction.source`, but checking both sides costs nothing).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_webapp_history.py -v`
Expected: all tests PASS, including the two new ones.

- [ ] **Step 5: Commit**

```bash
git add webapp/history.py tests/test_webapp_history.py
git commit -m "feat: recognize cloud_web_fallback as its own History-tab source value

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: `webapp/actuals_sync.py` — git helper functions

**Files:**
- Create: `webapp/actuals_sync.py`
- Test: `tests/test_actuals_sync.py` (new file)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `_run_git(args: list[str], cwd: Path, timeout: int = 30) -> subprocess.CompletedProcess`, `_ensure_repo_cloned(repo_dir: Path, remote_url: str) -> bool`, `_git_pull(repo_dir: Path) -> bool`, `_git_commit_and_push(repo_dir: Path, message: str) -> bool` — all consumed by Task 3 and Task 4.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_actuals_sync.py`:

```python
"""
Tests for webapp/actuals_sync.py -- the cloud-assisted automatic actuals
fallback's local half (git helpers, queue export, inbox apply). No real
git, network, or credentials are used anywhere in this file -- every git
operation is monkeypatched. See docs/superpowers/specs/
2026-09-03-automatic-actuals-fallback-design.md.
"""
import sys
import os
import json
import tempfile
import datetime as dt
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
import webapp.actuals_sync as actuals_sync


def _fake_completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=["git"], returncode=returncode, stdout=stdout, stderr=stderr)


def test_run_git_disables_terminal_prompt():
    print("=== _run_git: GIT_TERMINAL_PROMPT=0 is always set, so a credentials gap fails fast instead of hanging ===")
    with tempfile.TemporaryDirectory() as tmp:
        captured_env = {}

        def _fake_run(args, cwd, env, capture_output, text, timeout):
            captured_env.update(env)
            return _fake_completed()

        with patch.object(subprocess, "run", side_effect=_fake_run):
            actuals_sync._run_git(["status"], cwd=Path(tmp))

        assert captured_env.get("GIT_TERMINAL_PROMPT") == "0"
    print("PASS\n")


def test_ensure_repo_cloned_clones_when_missing():
    print("=== _ensure_repo_cloned: clones the remote when repo_dir has no .git yet ===")
    with tempfile.TemporaryDirectory() as tmp:
        repo_dir = Path(tmp) / "repo"
        calls = []

        def _fake_run_git(args, cwd, timeout=30):
            calls.append(args)
            return _fake_completed()

        with patch.object(actuals_sync, "_run_git", side_effect=_fake_run_git):
            cloned = actuals_sync._ensure_repo_cloned(repo_dir, "https://example.test/repo.git")

        assert cloned is True
        assert calls == [["clone", "https://example.test/repo.git", str(repo_dir)]]
    print("PASS\n")


def test_ensure_repo_cloned_is_a_noop_when_already_cloned():
    print("=== _ensure_repo_cloned: does nothing when repo_dir already has a .git directory ===")
    with tempfile.TemporaryDirectory() as tmp:
        repo_dir = Path(tmp) / "repo"
        (repo_dir / ".git").mkdir(parents=True)

        with patch.object(actuals_sync, "_run_git") as mock_run_git:
            cloned = actuals_sync._ensure_repo_cloned(repo_dir, "https://example.test/repo.git")

        assert cloned is False
        mock_run_git.assert_not_called()
    print("PASS\n")


def test_git_pull_returns_true_on_success():
    print("=== _git_pull: returns True when the pull succeeds ===")
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(actuals_sync, "_run_git", return_value=_fake_completed(returncode=0)):
            assert actuals_sync._git_pull(Path(tmp)) is True
    print("PASS\n")


def test_git_pull_returns_false_on_failure_never_raises():
    print("=== _git_pull: returns False (never raises) when the pull fails, e.g. credentials not configured yet ===")
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(actuals_sync, "_run_git", return_value=_fake_completed(returncode=1, stderr="could not read Username for 'https://github.com': terminal prompts disabled")):
            assert actuals_sync._git_pull(Path(tmp)) is False
    print("PASS\n")


def test_git_commit_and_push_succeeds():
    print("=== _git_commit_and_push: stages, commits, and pushes; returns True on success ===")
    with tempfile.TemporaryDirectory() as tmp:
        calls = []

        def _fake_run_git(args, cwd, timeout=30):
            calls.append(args[0])
            return _fake_completed(returncode=0)

        with patch.object(actuals_sync, "_run_git", side_effect=_fake_run_git):
            result = actuals_sync._git_commit_and_push(Path(tmp), "test commit")

        assert result is True
        assert calls == ["add", "commit", "push"]
    print("PASS\n")


def test_git_commit_and_push_treats_nothing_to_commit_as_success():
    print("=== _git_commit_and_push: a 'nothing to commit' failure is treated as success (no push needed), not a real failure ===")
    with tempfile.TemporaryDirectory() as tmp:
        def _fake_run_git(args, cwd, timeout=30):
            if args[0] == "commit":
                return _fake_completed(returncode=1, stdout="nothing to commit, working tree clean")
            return _fake_completed(returncode=0)

        with patch.object(actuals_sync, "_run_git", side_effect=_fake_run_git):
            result = actuals_sync._git_commit_and_push(Path(tmp), "test commit")

        assert result is True
    print("PASS\n")


def test_git_commit_and_push_returns_false_when_push_fails():
    print("=== _git_commit_and_push: a real commit followed by a failed push returns False ===")
    with tempfile.TemporaryDirectory() as tmp:
        def _fake_run_git(args, cwd, timeout=30):
            if args[0] == "push":
                return _fake_completed(returncode=1, stderr="could not read Username")
            return _fake_completed(returncode=0)

        with patch.object(actuals_sync, "_run_git", side_effect=_fake_run_git):
            result = actuals_sync._git_commit_and_push(Path(tmp), "test commit")

        assert result is False
    print("PASS\n")


if __name__ == "__main__":
    test_run_git_disables_terminal_prompt()
    test_ensure_repo_cloned_clones_when_missing()
    test_ensure_repo_cloned_is_a_noop_when_already_cloned()
    test_git_pull_returns_true_on_success()
    test_git_pull_returns_false_on_failure_never_raises()
    test_git_commit_and_push_succeeds()
    test_git_commit_and_push_treats_nothing_to_commit_as_success()
    test_git_commit_and_push_returns_false_when_push_fails()
    print("All actuals_sync tests passed.")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_actuals_sync.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'webapp.actuals_sync'`.

- [ ] **Step 3: Write `webapp/actuals_sync.py` with the git helper functions**

```python
"""
Local half of the cloud-assisted automatic actuals fallback (see
docs/superpowers/specs/2026-09-03-automatic-actuals-fallback-design.md).

webapp/scheduler.py's background loop cannot call WebSearch, so
scripts/fill_missing_actuals.py's real fallback has always required a
human or an interactive agent session to notice a stale candidate and
run it by hand. This module closes that gap by exporting the current
stale-candidate list to a dedicated git repo every 30 minutes
(export_stale_queue()), where a separately-scheduled cloud agent routine
researches real cited actuals via WebSearch and appends them to a second
file in that same repo -- this module then applies those results back
into the live dashboard database (apply_resolved_inbox()). The cloud
routine itself is not code in this repo; it's a scheduled routine
created directly via this platform's own scheduling tool, reading and
writing the same two JSON files this module owns.

Local writes data_layer/pending_actuals_queue.json ONLY; the cloud
routine writes data_layer/resolved_actuals_inbox.json ONLY -- never the
reverse, by construction, so a plain pull-before-write never conflicts.
"""
from __future__ import annotations

import os
import subprocess
import threading
import time
import datetime as dt
from pathlib import Path
from typing import Optional


def _run_git(args: list[str], cwd: Path, timeout: int = 30) -> subprocess.CompletedProcess:
    """
    Runs `git <args>` in `cwd` with GIT_TERMINAL_PROMPT=0 -- a credentials
    gap (no PAT configured yet, or one that's expired) fails immediately
    with a non-zero exit and a real stderr message, instead of hanging
    forever waiting for a prompt that can never arrive in an unattended
    background thread. Never raises on a non-zero exit -- callers inspect
    .returncode themselves; only a genuinely broken invocation (git
    itself missing, a filesystem error) propagates.
    """
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    return subprocess.run(
        ["git", *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout,
    )


def _ensure_repo_cloned(repo_dir: Path, remote_url: str) -> bool:
    """
    Clones remote_url into repo_dir if it doesn't already look like a git
    checkout (no .git directory yet). Returns True if a fresh clone just
    happened, False if repo_dir was already a checkout (the common case
    on every cycle after the first). Raises RuntimeError if the clone
    itself fails -- callers (start_actuals_sync()'s loop) already wrap
    each cycle in a broad fail-open except, so this propagating is fine;
    it does NOT get silently swallowed inside this function, since a
    failed initial clone needs to be loud (every later cycle depends on
    it), not just logged and forgotten.
    """
    if (repo_dir / ".git").exists():
        return False
    result = _run_git(["clone", remote_url, str(repo_dir)], cwd=repo_dir.parent)
    if result.returncode != 0:
        raise RuntimeError(f"git clone failed: {result.stderr}")
    return True


def _git_pull(repo_dir: Path) -> bool:
    """
    Best-effort pull -- returns True on success, False on any failure
    (credentials not configured yet, network down, merge conflict that
    --ff-only refuses). Never raises. A failed pull just means this
    cycle might work from a slightly stale local copy or skip doing
    anything useful; never fatal, always retried next cycle.
    """
    result = _run_git(["pull", "--ff-only"], cwd=repo_dir)
    return result.returncode == 0


def _git_commit_and_push(repo_dir: Path, message: str) -> bool:
    """
    Stages everything in repo_dir, commits, and pushes. Returns True on
    success. A commit failure whose output mentions "nothing to commit"
    is treated as success (there was genuinely nothing new to push, not
    a real error) -- checked via the commit command's own stdout, not a
    separate `git status` call. Never raises.
    """
    _run_git(["add", "-A"], cwd=repo_dir)
    commit_result = _run_git(["commit", "-m", message], cwd=repo_dir)
    if commit_result.returncode != 0:
        return "nothing to commit" in commit_result.stdout.lower()
    push_result = _run_git(["push"], cwd=repo_dir)
    return push_result.returncode == 0
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_actuals_sync.py -v`
Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add webapp/actuals_sync.py tests/test_actuals_sync.py
git commit -m "feat: add git helper functions for the actuals-sync module

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: `export_stale_queue()`

**Files:**
- Modify: `webapp/actuals_sync.py` (add `export_stale_queue()`)
- Test: `tests/test_actuals_sync.py` (extend)

**Interfaces:**
- Consumes: `webapp.store.get_events_with_stale_missing_actual(conn, now, grace_period_hours=1.0) -> list[EventHistoryRow]` (unchanged, existing — each row has `.event_title`, `.event_time_utc`, `.forecast`, `.previous`); `_git_commit_and_push(repo_dir, message) -> bool` (Task 2).
- Produces: `export_stale_queue(conn, repo_dir: Path, now: Optional[dt.datetime] = None) -> bool`, consumed by Task 5's `start_actuals_sync()` loop.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_actuals_sync.py`'s imports: `from data_layer.calendar_feed import EconomicEvent` and `import webapp.store as store`.

Append these test functions:

```python
def _seed_pending_event(conn, title, event_time, forecast="0.2%", previous="0.1%"):
    event = EconomicEvent(title=title, country="USD", impact="High", event_time_utc=event_time, forecast=forecast, previous=previous)
    store.upsert_event_history(conn, event, surprise_direction=None, now=event_time)


def test_export_writes_candidates_within_cutoff():
    print("=== export_stale_queue: writes the current stale-candidate list as pending_actuals_queue.json ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        repo_dir = Path(tmp) / "repo"
        repo_dir.mkdir()
        now = dt.datetime(2026, 9, 3, 12, 0, tzinfo=UTC_TZ)
        stale_time = now - dt.timedelta(hours=5)  # past the 1h grace period, within the 48h cutoff

        conn = store.get_connection(dash_db)
        _seed_pending_event(conn, "PPI m/m", stale_time, forecast="0.2%", previous="0.1%")

        with patch.object(actuals_sync, "_git_commit_and_push", return_value=True):
            pushed = actuals_sync.export_stale_queue(conn, repo_dir, now=now)
        conn.close()

        assert pushed is True
        content = json.loads((repo_dir / "data_layer" / "pending_actuals_queue.json").read_text())
        assert content["candidates"] == [
            {"event_title": "PPI m/m", "event_time_utc": stale_time.isoformat(), "forecast": "0.2%", "previous": "0.1%"},
        ]
    print("PASS\n")


def test_export_excludes_candidates_older_than_48_hours():
    print("=== export_stale_queue: excludes a real stale candidate older than the 48h cutoff ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        repo_dir = Path(tmp) / "repo"
        repo_dir.mkdir()
        now = dt.datetime(2026, 9, 3, 12, 0, tzinfo=UTC_TZ)
        too_old_time = now - dt.timedelta(hours=60)

        conn = store.get_connection(dash_db)
        _seed_pending_event(conn, "PPI m/m", too_old_time)

        with patch.object(actuals_sync, "_git_commit_and_push", return_value=True):
            actuals_sync.export_stale_queue(conn, repo_dir, now=now)
        conn.close()

        content = json.loads((repo_dir / "data_layer" / "pending_actuals_queue.json").read_text())
        assert content["candidates"] == []
    print("PASS\n")


def test_export_does_not_push_when_candidates_unchanged():
    print("=== export_stale_queue: makes no commit/push when the candidate list hasn't changed from what's already written, even though generated_at_utc always differs ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        repo_dir = Path(tmp) / "repo"
        repo_dir.mkdir()
        stale_time = dt.datetime(2026, 9, 3, 7, 0, tzinfo=UTC_TZ)

        conn = store.get_connection(dash_db)
        _seed_pending_event(conn, "PPI m/m", stale_time)

        with patch.object(actuals_sync, "_git_commit_and_push", return_value=True) as mock_push:
            actuals_sync.export_stale_queue(conn, repo_dir, now=dt.datetime(2026, 9, 3, 12, 0, tzinfo=UTC_TZ))
            pushed_second_time = actuals_sync.export_stale_queue(conn, repo_dir, now=dt.datetime(2026, 9, 3, 12, 30, tzinfo=UTC_TZ))
        conn.close()

        assert pushed_second_time is False
        mock_push.assert_called_once()  # only the first call actually pushed
    print("PASS\n")


def test_export_pushes_again_when_candidates_actually_change():
    print("=== export_stale_queue: pushes again once the real candidate list changes (a new stale event appears) ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        repo_dir = Path(tmp) / "repo"
        repo_dir.mkdir()
        first_time = dt.datetime(2026, 9, 3, 7, 0, tzinfo=UTC_TZ)
        second_time = dt.datetime(2026, 9, 3, 8, 0, tzinfo=UTC_TZ)
        now = dt.datetime(2026, 9, 3, 12, 0, tzinfo=UTC_TZ)

        conn = store.get_connection(dash_db)
        _seed_pending_event(conn, "PPI m/m", first_time)

        with patch.object(actuals_sync, "_git_commit_and_push", return_value=True) as mock_push:
            actuals_sync.export_stale_queue(conn, repo_dir, now=now)
            _seed_pending_event(conn, "Retail Sales m/m", second_time)
            pushed_again = actuals_sync.export_stale_queue(conn, repo_dir, now=now)
        conn.close()

        assert pushed_again is True
        assert mock_push.call_count == 2
    print("PASS\n")
```

Add all four calls to the `if __name__ ==` block.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_actuals_sync.py -v -k export`
Expected: FAIL with `AttributeError: module 'webapp.actuals_sync' has no attribute 'export_stale_queue'`.

- [ ] **Step 3: Implement `export_stale_queue()`**

Add these imports to the top of `webapp/actuals_sync.py`:

```python
import json
from webapp.store import get_events_with_stale_missing_actual
```

Add this constant near the top of the file, after the imports:

```python
# The cloud routine only ever attempts candidates younger than this --
# older gaps are the existing manual/backdate workflow's job, not
# something a 2-hourly automated pass should keep retrying forever.
MAX_CANDIDATE_AGE_HOURS = 48.0
```

Add this function after `_git_commit_and_push()`:

```python
def export_stale_queue(conn, repo_dir: Path, now: Optional[dt.datetime] = None) -> bool:
    """
    Overwrites <repo_dir>/data_layer/pending_actuals_queue.json with the
    CURRENT stale-missing-actual candidate list (via
    webapp.store.get_events_with_stale_missing_actual(), completely
    unchanged -- every one of its existing exclusions, e.g. title outside
    EVENT_SURPRISE_DIRECTION, structurally text-only, still within the
    1h grace period, applies here identically), filtered to occurrences
    within the last MAX_CANDIDATE_AGE_HOURS. Always a full snapshot, never
    an append -- it reflects current DB state, not a log.

    Commits and pushes only if the candidate list ITSELF changed from
    what's already on disk (generated_at_utc is deliberately excluded
    from that comparison -- it always differs and isn't real
    information; comparing it would push on every single cycle). Returns
    True if a push happened. Never raises -- the caller
    (start_actuals_sync()'s loop) wraps the whole cycle in a broad
    fail-open except.
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(hours=MAX_CANDIDATE_AGE_HOURS)
    rows = get_events_with_stale_missing_actual(conn, now)
    candidates = [
        {
            "event_title": r.event_title,
            "event_time_utc": r.event_time_utc,
            "forecast": r.forecast,
            "previous": r.previous,
        }
        for r in rows
        if dt.datetime.fromisoformat(r.event_time_utc) >= cutoff
    ]

    queue_path = repo_dir / "data_layer" / "pending_actuals_queue.json"
    existing_candidates = None
    if queue_path.exists():
        try:
            existing_candidates = json.loads(queue_path.read_text()).get("candidates")
        except (json.JSONDecodeError, OSError):
            existing_candidates = None
    if existing_candidates == candidates:
        return False

    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(json.dumps(
        {"generated_at_utc": now.isoformat(), "candidates": candidates}, indent=2, sort_keys=True,
    ))
    return _git_commit_and_push(repo_dir, f"chore: update pending actuals queue ({len(candidates)} candidate(s))")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_actuals_sync.py -v -k export`
Expected: all 4 tests PASS.

- [ ] **Step 5: Run the full new test file**

Run: `python -m pytest tests/test_actuals_sync.py -v`
Expected: all 12 tests PASS (8 from Task 2 + 4 new).

- [ ] **Step 6: Commit**

```bash
git add webapp/actuals_sync.py tests/test_actuals_sync.py
git commit -m "feat: add export_stale_queue() to the actuals-sync module

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: `apply_resolved_inbox()`

**Files:**
- Modify: `webapp/actuals_sync.py` (add `apply_resolved_inbox()`)
- Test: `tests/test_actuals_sync.py` (extend)

**Interfaces:**
- Consumes: `_git_pull(repo_dir) -> bool` (Task 2); `webapp.store.upsert_event_history(conn, event, surprise_direction, now, source="live")` (existing, unchanged); `data_layer.calendar_feed.EconomicEvent`, `data_layer.calendar_feed.classify_surprise` (existing, unchanged); `scripts.fill_missing_actuals.FillReport` (existing dataclass, reused as-is: `written: int = 0`, `skipped: int = 0`, `skip_reasons: list[str] = field(default_factory=list)`).
- Produces: `apply_resolved_inbox(conn, repo_dir: Path, now: Optional[dt.datetime] = None) -> FillReport`, consumed by Task 5's `start_actuals_sync()` loop.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_actuals_sync.py`'s imports: `from data_layer.calendar_feed import classify_surprise` and `from scripts.fill_missing_actuals import FillReport`.

Append these test functions:

```python
def _write_inbox(repo_dir, entries):
    inbox_path = repo_dir / "data_layer" / "resolved_actuals_inbox.json"
    inbox_path.parent.mkdir(parents=True, exist_ok=True)
    inbox_path.write_text(json.dumps({"entries": entries}))


def test_apply_writes_pending_entries_with_cloud_source():
    print("=== apply_resolved_inbox: writes a real actual for a still-pending event, with source='cloud_web_fallback' ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        repo_dir = Path(tmp) / "repo"
        event_time = dt.datetime(2026, 9, 1, 12, 30, tzinfo=UTC_TZ)

        conn = store.get_connection(dash_db)
        _seed_pending_event(conn, "PPI m/m", event_time, forecast="0.2%", previous="0.1%")
        _write_inbox(repo_dir, [
            {"event_title": "PPI m/m", "event_time_utc": event_time.isoformat(), "actual": "0.3%",
             "source_note": "BLS official release, https://example.test", "researched_at_utc": "2026-09-03T10:00:00+00:00"},
        ])

        with patch.object(actuals_sync, "_git_pull", return_value=True):
            report = actuals_sync.apply_resolved_inbox(conn, repo_dir, now=dt.datetime(2026, 9, 3, 12, 0, tzinfo=UTC_TZ))

        rows = store.get_event_history(conn, "PPI m/m")
        conn.close()

        assert report.written == 1
        assert len(rows) == 1
        assert rows[0].actual == "0.3%"
        assert rows[0].source == "cloud_web_fallback"
    print("PASS\n")


def test_apply_skips_entries_already_resolved():
    print("=== apply_resolved_inbox: an inbox entry for an already-resolved event is skipped, never overwritten ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        repo_dir = Path(tmp) / "repo"
        event_time = dt.datetime(2026, 9, 1, 12, 30, tzinfo=UTC_TZ)

        conn = store.get_connection(dash_db)
        event = EconomicEvent(title="PPI m/m", country="USD", impact="High", event_time_utc=event_time, forecast="0.2%", previous="0.1%", actual="0.5%")
        store.upsert_event_history(conn, event, classify_surprise(event), now=event_time, source="live")
        _write_inbox(repo_dir, [
            {"event_title": "PPI m/m", "event_time_utc": event_time.isoformat(), "actual": "0.3%",
             "source_note": "BLS official release, https://example.test", "researched_at_utc": "2026-09-03T10:00:00+00:00"},
        ])

        with patch.object(actuals_sync, "_git_pull", return_value=True):
            report = actuals_sync.apply_resolved_inbox(conn, repo_dir, now=dt.datetime(2026, 9, 3, 12, 0, tzinfo=UTC_TZ))

        rows = store.get_event_history(conn, "PPI m/m")
        conn.close()

        assert report.written == 0
        assert report.skipped == 1
        assert rows[0].actual == "0.5%"  # untouched -- the live value wins, never overwritten by the cloud-researched one
        assert rows[0].source == "live"
    print("PASS\n")


def test_apply_treats_missing_inbox_file_as_empty():
    print("=== apply_resolved_inbox: a repo with no inbox file yet is treated as zero entries, not an error ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        repo_dir = Path(tmp) / "repo"
        repo_dir.mkdir()
        conn = store.get_connection(dash_db)

        with patch.object(actuals_sync, "_git_pull", return_value=True):
            report = actuals_sync.apply_resolved_inbox(conn, repo_dir)
        conn.close()

        assert report.written == 0
        assert report.skipped == 0
    print("PASS\n")


def test_apply_treats_malformed_inbox_json_as_empty():
    print("=== apply_resolved_inbox: a corrupted/malformed inbox file is treated as zero entries, not an error ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        repo_dir = Path(tmp) / "repo"
        inbox_path = repo_dir / "data_layer" / "resolved_actuals_inbox.json"
        inbox_path.parent.mkdir(parents=True)
        inbox_path.write_text("{not valid json")
        conn = store.get_connection(dash_db)

        with patch.object(actuals_sync, "_git_pull", return_value=True):
            report = actuals_sync.apply_resolved_inbox(conn, repo_dir)
        conn.close()

        assert report.written == 0
        assert report.skipped == 0
    print("PASS\n")


def test_apply_skips_malformed_entry_missing_actual():
    print("=== apply_resolved_inbox: an inbox entry missing a real 'actual' is skipped, never fabricated ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        repo_dir = Path(tmp) / "repo"
        event_time = dt.datetime(2026, 9, 1, 12, 30, tzinfo=UTC_TZ)

        conn = store.get_connection(dash_db)
        _seed_pending_event(conn, "PPI m/m", event_time)
        _write_inbox(repo_dir, [
            {"event_title": "PPI m/m", "event_time_utc": event_time.isoformat(), "actual": None,
             "source_note": "no real value found", "researched_at_utc": "2026-09-03T10:00:00+00:00"},
        ])

        with patch.object(actuals_sync, "_git_pull", return_value=True):
            report = actuals_sync.apply_resolved_inbox(conn, repo_dir)
        conn.close()

        assert report.written == 0
        assert report.skipped == 1
    print("PASS\n")


def test_apply_pulls_before_reading_the_inbox():
    print("=== apply_resolved_inbox: pulls the repo before reading the inbox file, so it sees the cloud routine's latest push ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        repo_dir = Path(tmp) / "repo"
        conn = store.get_connection(dash_db)

        with patch.object(actuals_sync, "_git_pull", return_value=True) as mock_pull:
            actuals_sync.apply_resolved_inbox(conn, repo_dir)
        conn.close()

        mock_pull.assert_called_once_with(repo_dir)
    print("PASS\n")
```

Add all six calls to the `if __name__ ==` block.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_actuals_sync.py -v -k apply`
Expected: FAIL with `AttributeError: module 'webapp.actuals_sync' has no attribute 'apply_resolved_inbox'`.

- [ ] **Step 3: Implement `apply_resolved_inbox()`**

Add these imports to the top of `webapp/actuals_sync.py`:

```python
from data_layer.calendar_feed import EconomicEvent, classify_surprise
from webapp.store import upsert_event_history
from scripts.fill_missing_actuals import FillReport
```

Add this function after `export_stale_queue()`:

```python
def apply_resolved_inbox(conn, repo_dir: Path, now: Optional[dt.datetime] = None) -> FillReport:
    """
    Pulls repo_dir (best-effort -- a failed pull just means this cycle
    works from a slightly stale local copy, never fatal), reads
    <repo_dir>/data_layer/resolved_actuals_inbox.json (absent, unreadable,
    or malformed JSON is treated as zero entries, never an error -- same
    "absent is a valid state" discipline as everywhere else in this
    codebase), and for each entry whose event_history row STILL has
    actual IS NULL, writes it via the exact write scripts/fill_missing_
    actuals.py's run() uses, with source="cloud_web_fallback" (a distinct
    provenance value, never collapsed into "live_web_fallback" -- see
    webapp/history.py's source-precedence chains, Task 1). An entry for
    an already-resolved row (by ANY source) is silently skipped -- safe
    to re-read the same append-only inbox file forever, since nothing
    here ever mutates or removes an inbox entry. Returns the same
    FillReport shape fill_missing_actuals.run() does. Never raises.
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    report = FillReport()
    _git_pull(repo_dir)

    inbox_path = repo_dir / "data_layer" / "resolved_actuals_inbox.json"
    entries = []
    if inbox_path.exists():
        try:
            entries = json.loads(inbox_path.read_text()).get("entries", [])
        except (json.JSONDecodeError, OSError):
            entries = []

    for entry in entries:
        title = entry.get("event_title")
        event_time_str = entry.get("event_time_utc")
        actual = entry.get("actual")
        if not title or not event_time_str or not actual:
            report.skipped += 1
            report.skip_reasons.append(f"malformed inbox entry: {entry!r}")
            continue

        rows = conn.execute(
            "SELECT * FROM event_history WHERE event_title = ? AND event_time_utc = ?",
            (title, event_time_str),
        ).fetchall()
        if not rows:
            report.skipped += 1
            report.skip_reasons.append(f"{title}@{event_time_str}: no matching event_history row")
            continue
        existing = dict(rows[0])
        if existing["actual"] is not None:
            report.skipped += 1
            report.skip_reasons.append(f"{title}@{event_time_str}: already has a real actual, not overwritten")
            continue

        event = EconomicEvent(
            title=title, country="USD", impact="High",
            event_time_utc=dt.datetime.fromisoformat(event_time_str),
            forecast=existing["forecast"], previous=existing["previous"], actual=actual,
        )
        surprise_direction = classify_surprise(event)
        upsert_event_history(conn, event, surprise_direction, now, source="cloud_web_fallback")
        report.written += 1

    return report
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_actuals_sync.py -v -k apply`
Expected: all 6 tests PASS.

- [ ] **Step 5: Run the full new test file**

Run: `python -m pytest tests/test_actuals_sync.py -v`
Expected: all 18 tests PASS (12 from Tasks 2-3 + 6 new).

- [ ] **Step 6: Commit**

```bash
git add webapp/actuals_sync.py tests/test_actuals_sync.py
git commit -m "feat: add apply_resolved_inbox() to the actuals-sync module

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: `start_actuals_sync()`, `webapp/app.py` integration, and final verification

**Files:**
- Modify: `webapp/actuals_sync.py` (add `start_actuals_sync()`)
- Modify: `webapp/app.py` (start the new sync loop alongside the existing scheduler)
- Test: manual verification only (matching the existing precedent — `webapp/scheduler.py`'s own `start_scheduler()` threading wrapper has no direct unit test either; only the function it calls is tested)

**Interfaces:**
- Consumes: `_ensure_repo_cloned()`, `apply_resolved_inbox()`, `export_stale_queue()` (Tasks 2-4); `webapp.store.get_connection()` (existing, unchanged).
- Produces: `start_actuals_sync(repo_dir: Optional[Path] = None) -> None`, called once from `webapp/app.py`'s `__main__` block. Nothing else depends on this — it's the final integration point.

- [ ] **Step 1: Add `start_actuals_sync()` to `webapp/actuals_sync.py`**

Add this import to the top of the file: `from webapp.store import get_connection`

Add these constants near `MAX_CANDIDATE_AGE_HOURS`:

```python
# Decoupled from webapp/scheduler.py's own adaptive FF-fetch cadence --
# this is purely "how often do we check the sync repo for cloud-side
# progress and re-export our own current candidate list," a much cheaper
# operation than a live FF fetch (most cycles find nothing changed and
# push nothing at all).
ACTUALS_SYNC_INTERVAL_SECONDS = 30 * 60

DEFAULT_SYNC_REPO_DIR = Path(__file__).parent / ".actuals_sync" / "repo"
SYNC_REMOTE_URL = "https://github.com/Maximillionza/News_Engine2.git"
```

Add this function at the end of the file:

```python
def start_actuals_sync(repo_dir: Optional[Path] = None) -> None:
    """
    Background daemon thread mirroring webapp/scheduler.py's
    start_scheduler() pattern exactly: infinite loop, one fixed retry
    interval, and a broad fail-open except around the whole cycle body
    so one bad git/DB operation never kills the thread. Each cycle:
    ensure the dedicated sync clone exists (cloning it on the very first
    cycle only), apply any new cloud-researched actuals into the live
    DB, then export the current stale-candidate queue (which may have
    just shrunk from the applies immediately above, if anything was
    newly resolved this cycle).
    """
    repo_dir = repo_dir or DEFAULT_SYNC_REPO_DIR

    def _loop():
        while True:
            try:
                repo_dir.parent.mkdir(parents=True, exist_ok=True)
                _ensure_repo_cloned(repo_dir, SYNC_REMOTE_URL)
                conn = get_connection()
                try:
                    report = apply_resolved_inbox(conn, repo_dir)
                    if report.written:
                        print(f"[actuals_sync] applied {report.written} cloud-researched actual(s)")
                    export_stale_queue(conn, repo_dir)
                finally:
                    conn.close()
            except Exception as exc:  # noqa: BLE001 — the loop must survive any unhandled error
                print(f"[actuals_sync] ERROR: sync cycle failed, will retry next interval: {exc}")
            time.sleep(ACTUALS_SYNC_INTERVAL_SECONDS)

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
```

Also add `webapp/.actuals_sync/` to this project's `.gitignore` (the dedicated clone must never become part of THIS repo's own tracked tree — it's a separate git checkout nested inside it).

- [ ] **Step 2: Wire it into `webapp/app.py`**

Add this import alongside the existing `from webapp.scheduler import start_scheduler` line:

```python
from webapp.actuals_sync import start_actuals_sync
```

Add this call immediately after the existing `start_scheduler(_get_tracked_symbols)` line in the `if __name__ == "__main__":` block:

```python
    start_actuals_sync()
```

- [ ] **Step 3: Run the full test suite**

Run: `python -m pytest -q`
Expected: same pass/fail count as the pre-plan baseline (481 passed, 1 known pre-existing FinBERT failure) plus this plan's 20 new tests (2 from Task 1, 18 from Tasks 2-4), all passing — 501 passed, 1 known failure.

- [ ] **Step 4: Commit**

```bash
git add webapp/actuals_sync.py webapp/app.py .gitignore
git commit -m "feat: wire the actuals-sync loop into webapp/app.py's startup

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

---

### Task 6 (optional, non-blocking): `webapp/static/app.js` — badge label for `cloud_web_fallback`

**Files:**
- Modify: `webapp/static/app.js:850-854`

**Interfaces:**
- Consumes: `HistoryRow.source` (Task 1) — already correctly `"cloud_web_fallback"` on the wire; this task is purely a display polish, the `source` field itself is already fully correct without it.

This task is optional and non-blocking — `"fred"` already has no badge today (a pre-existing gap, not introduced by this plan) and `"cloud_web_fallback"` would fall into that same no-badge case if this task is skipped. Do it only if time allows; skipping it does not affect correctness anywhere.

- [ ] **Step 1: Add the badge case**

In `webapp/static/app.js`, change:

```javascript
    const sourceBadge = r.source === "seeded"
      ? ' <span style="color:#888;font-size:11px;font-weight:normal">(seeded)</span>'
      : r.source === "live_web_fallback"
      ? ' <span style="color:#888;font-size:11px;font-weight:normal">(web-sourced)</span>'
      : "";
```

to:

```javascript
    const sourceBadge = r.source === "seeded"
      ? ' <span style="color:#888;font-size:11px;font-weight:normal">(seeded)</span>'
      : r.source === "live_web_fallback"
      ? ' <span style="color:#888;font-size:11px;font-weight:normal">(web-sourced)</span>'
      : r.source === "cloud_web_fallback"
      ? ' <span style="color:#888;font-size:11px;font-weight:normal">(cloud-researched)</span>'
      : "";
```

- [ ] **Step 2: Manually verify in the browser**

Since this file has no test suite (matches the rest of `webapp/static/`), verify by hand: open the dashboard's History tab, confirm existing `"seeded"`/`"live_web_fallback"` rows still show their badges unchanged, and that the syntax is valid (no console errors on page load).

- [ ] **Step 3: Commit**

```bash
git add webapp/static/app.js
git commit -m "feat: add a History-tab badge label for cloud_web_fallback rows

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Post-plan step (not a task — done by the orchestrating session directly, not a subagent)

Once all four tasks land and `webapp\app.py` is restarted (picking up `start_actuals_sync()`), create the cloud routine directly via this platform's `RemoteTrigger` tool (per `docs/superpowers/specs/2026-09-03-automatic-actuals-fallback-design.md`'s "Cloud routine" section for the exact prompt and config):
- `cron_expression: "0 */2 * * *"`, model `claude-sonnet-5`
- Source repo: `https://github.com/Maximillionza/News_Engine2`
- `allowed_tools: ["Read", "Write", "Bash"]`
- The self-contained prompt from the spec, verbatim

This is a platform API call, not code in this repo — it has no test and isn't part of any task's implementer scope.
