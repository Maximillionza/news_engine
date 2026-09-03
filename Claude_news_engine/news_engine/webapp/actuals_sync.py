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

import json
import os
import subprocess
import threading
import time
import datetime as dt
from pathlib import Path
from typing import Optional

from webapp.store import get_events_with_stale_missing_actual

# The cloud routine only ever attempts candidates younger than this --
# older gaps are the existing manual/backdate workflow's job, not
# something a 2-hourly automated pass should keep retrying forever.
MAX_CANDIDATE_AGE_HOURS = 48.0


def _run_git(args: list[str], cwd: Path, timeout: int = 30) -> subprocess.CompletedProcess:
    """
    Runs `git <args>` in `cwd` with GIT_TERMINAL_PROMPT=0 -- a credentials
    gap (no PAT configured yet, or one that's expired) fails immediately
    with a non-zero exit and a real stderr message, instead of hanging
    forever waiting for a prompt that can never arrive in an unattended
    background thread. Never raises on a non-zero exit -- callers inspect
    .returncode themselves; only a genuinely broken invocation (git
    itself missing, a filesystem error) propagates. TimeoutExpired is
    caught and converted to a CompletedProcess with returncode=1, so the
    "never raises" contract is literally true.
    """
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        return subprocess.run(
            ["git", *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args=["git", *args], returncode=1, stdout="", stderr=f"git {args[0] if args else ''} timed out after {timeout}s")


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
    separate `git status` call. Never raises. If git add fails, returns
    False immediately and skips commit/push.
    """
    add_result = _run_git(["add", "-A"], cwd=repo_dir)
    if add_result.returncode != 0:
        return False
    commit_result = _run_git(["commit", "-m", message], cwd=repo_dir)
    if commit_result.returncode != 0:
        return "nothing to commit" in commit_result.stdout.lower()
    push_result = _run_git(["push"], cwd=repo_dir)
    return push_result.returncode == 0


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
