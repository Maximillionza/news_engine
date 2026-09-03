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
from data_layer.calendar_feed import EconomicEvent, classify_surprise
from scripts.fill_missing_actuals import FillReport
import webapp.actuals_sync as actuals_sync
import webapp.store as store


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
    print("=== _git_commit_and_push: a real commit followed by a push that fails even after the pull-and-retry returns False ===")
    with tempfile.TemporaryDirectory() as tmp:
        calls = []

        def _fake_run_git(args, cwd, timeout=30):
            calls.append(args[0])
            if args[0] == "push":
                return _fake_completed(returncode=1, stderr="could not read Username")
            return _fake_completed(returncode=0)

        with patch.object(actuals_sync, "_run_git", side_effect=_fake_run_git):
            result = actuals_sync._git_commit_and_push(Path(tmp), "test commit")

        assert result is False
        # add, commit, push (fails), pull (retry), push (fails again) -- gives up after one retry
        assert calls == ["add", "commit", "push", "pull", "push"]
    print("PASS\n")


def test_git_commit_and_push_retries_push_after_pull_on_rejection():
    print("=== _git_commit_and_push: a rejected push is retried exactly once after a pull, and recovers if the retry succeeds ===")
    with tempfile.TemporaryDirectory() as tmp:
        calls = []
        push_attempts = {"count": 0}

        def _fake_run_git(args, cwd, timeout=30):
            calls.append(args[0])
            if args[0] == "push":
                push_attempts["count"] += 1
                if push_attempts["count"] == 1:
                    return _fake_completed(returncode=1, stderr="rejected -- remote advanced")
                return _fake_completed(returncode=0)
            return _fake_completed(returncode=0)

        with patch.object(actuals_sync, "_run_git", side_effect=_fake_run_git):
            result = actuals_sync._git_commit_and_push(Path(tmp), "test commit")

        assert result is True
        assert calls == ["add", "commit", "push", "pull", "push"]
        assert push_attempts["count"] == 2
    print("PASS\n")


def test_run_git_catches_timeout_and_returns_completed_process():
    print("=== _run_git: catches subprocess.TimeoutExpired and returns CompletedProcess with returncode=1 (never raises) ===")
    with tempfile.TemporaryDirectory() as tmp:
        def _fake_run(args, cwd, env, capture_output, text, timeout):
            raise subprocess.TimeoutExpired(cmd=["git"], timeout=30)

        with patch.object(subprocess, "run", side_effect=_fake_run):
            result = actuals_sync._run_git(["status"], cwd=Path(tmp), timeout=30)

        assert isinstance(result, subprocess.CompletedProcess)
        assert result.returncode != 0
        assert "timed out" in result.stderr.lower()
    print("PASS\n")


def test_git_commit_and_push_returns_false_when_add_fails():
    print("=== _git_commit_and_push: returns False immediately when git add fails, and skips commit/push ===")
    with tempfile.TemporaryDirectory() as tmp:
        calls = []

        def _fake_run_git(args, cwd, timeout=30):
            calls.append(args[0])
            if args[0] == "add":
                return _fake_completed(returncode=1, stderr="could not add files")
            return _fake_completed(returncode=0)

        with patch.object(actuals_sync, "_run_git", side_effect=_fake_run_git):
            result = actuals_sync._git_commit_and_push(Path(tmp), "test commit")

        assert result is False
        assert calls == ["add"]
    print("PASS\n")


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
    print("=== export_stale_queue: makes no commit/push when the candidate list hasn't changed from what's already written, even though generated_at_utc always differs, and nothing is left unpushed ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        repo_dir = Path(tmp) / "repo"
        repo_dir.mkdir()
        stale_time = dt.datetime(2026, 9, 3, 7, 0, tzinfo=UTC_TZ)

        conn = store.get_connection(dash_db)
        _seed_pending_event(conn, "PPI m/m", stale_time)

        with patch.object(actuals_sync, "_git_commit_and_push", return_value=True) as mock_push, \
             patch.object(actuals_sync, "_has_unpushed_commits", return_value=False):
            actuals_sync.export_stale_queue(conn, repo_dir, now=dt.datetime(2026, 9, 3, 12, 0, tzinfo=UTC_TZ))
            pushed_second_time = actuals_sync.export_stale_queue(conn, repo_dir, now=dt.datetime(2026, 9, 3, 12, 30, tzinfo=UTC_TZ))
        conn.close()

        assert pushed_second_time is False
        mock_push.assert_called_once()  # only the first call actually pushed
    print("PASS\n")


def test_export_retries_push_when_candidates_unchanged_but_something_unpushed_remains():
    print("=== export_stale_queue: even when the candidate list hasn't changed, a prior cycle's unpushed commit still gets retried ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        repo_dir = Path(tmp) / "repo"
        repo_dir.mkdir()
        stale_time = dt.datetime(2026, 9, 3, 7, 0, tzinfo=UTC_TZ)

        conn = store.get_connection(dash_db)
        _seed_pending_event(conn, "PPI m/m", stale_time)

        with patch.object(actuals_sync, "_git_commit_and_push", return_value=True):
            actuals_sync.export_stale_queue(conn, repo_dir, now=dt.datetime(2026, 9, 3, 12, 0, tzinfo=UTC_TZ))

        with patch.object(actuals_sync, "_has_unpushed_commits", return_value=True), \
             patch.object(actuals_sync, "_git_push_with_retry", return_value=True) as mock_retry_push:
            pushed_second_time = actuals_sync.export_stale_queue(conn, repo_dir, now=dt.datetime(2026, 9, 3, 12, 30, tzinfo=UTC_TZ))
        conn.close()

        assert pushed_second_time is True
        mock_retry_push.assert_called_once_with(repo_dir)
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


def test_export_excludes_non_usd_country_candidates():
    print("=== export_stale_queue: a row with a real non-USD country is excluded, since this automated path has no human reviewer ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        repo_dir = Path(tmp) / "repo"
        repo_dir.mkdir()
        now = dt.datetime(2026, 9, 3, 12, 0, tzinfo=UTC_TZ)
        stale_time = now - dt.timedelta(hours=5)

        conn = store.get_connection(dash_db)
        eur_event = EconomicEvent(title="CPI m/m", country="EUR", impact="High", event_time_utc=stale_time, forecast="0.2%", previous="0.1%")
        store.upsert_event_history(conn, eur_event, surprise_direction=None, now=stale_time)

        with patch.object(actuals_sync, "_git_commit_and_push", return_value=True):
            actuals_sync.export_stale_queue(conn, repo_dir, now=now)
        conn.close()

        content = json.loads((repo_dir / "data_layer" / "pending_actuals_queue.json").read_text())
        assert content["candidates"] == []
    print("PASS\n")


def test_apply_treats_inbox_root_list_as_empty():
    print("=== apply_resolved_inbox: an inbox whose JSON root is a list (not an object) is treated as zero entries ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        repo_dir = Path(tmp) / "repo"
        inbox_path = repo_dir / "data_layer" / "resolved_actuals_inbox.json"
        inbox_path.parent.mkdir(parents=True)
        inbox_path.write_text(json.dumps(["not", "a", "dict"]))
        conn = store.get_connection(dash_db)

        with patch.object(actuals_sync, "_git_pull", return_value=True):
            report = actuals_sync.apply_resolved_inbox(conn, repo_dir)
        conn.close()

        assert report.written == 0
        assert report.skipped == 0
    print("PASS\n")


def test_apply_skips_bare_string_entry_but_still_processes_good_one():
    print("=== apply_resolved_inbox: a bare string entry alongside a valid dict entry is skipped without poisoning the good entry ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        repo_dir = Path(tmp) / "repo"
        event_time = dt.datetime(2026, 9, 1, 12, 30, tzinfo=UTC_TZ)

        conn = store.get_connection(dash_db)
        _seed_pending_event(conn, "PPI m/m", event_time, forecast="0.2%", previous="0.1%")
        inbox_path = repo_dir / "data_layer" / "resolved_actuals_inbox.json"
        inbox_path.parent.mkdir(parents=True, exist_ok=True)
        inbox_path.write_text(json.dumps({"entries": [
            "not a dict, just a bare string",
            {"event_title": "PPI m/m", "event_time_utc": event_time.isoformat(), "actual": "0.3%",
             "source_note": "BLS official release, https://example.test", "researched_at_utc": "2026-09-03T10:00:00+00:00"},
        ]}))

        with patch.object(actuals_sync, "_git_pull", return_value=True):
            report = actuals_sync.apply_resolved_inbox(conn, repo_dir, now=dt.datetime(2026, 9, 3, 12, 0, tzinfo=UTC_TZ))

        rows = store.get_event_history(conn, "PPI m/m")
        conn.close()

        assert report.written == 1
        assert report.skipped == 1
        assert rows[0].actual == "0.3%"
    print("PASS\n")


def test_apply_skips_entry_whose_actual_is_a_json_number_not_a_string():
    print("=== apply_resolved_inbox: an 'actual' arriving as a JSON number is skipped, never coerced/fabricated into a string ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        repo_dir = Path(tmp) / "repo"
        event_time = dt.datetime(2026, 9, 1, 12, 30, tzinfo=UTC_TZ)

        conn = store.get_connection(dash_db)
        _seed_pending_event(conn, "PPI m/m", event_time, forecast="0.2%", previous="0.1%")
        inbox_path = repo_dir / "data_layer" / "resolved_actuals_inbox.json"
        inbox_path.parent.mkdir(parents=True, exist_ok=True)
        inbox_path.write_text(json.dumps({"entries": [
            {"event_title": "PPI m/m", "event_time_utc": event_time.isoformat(), "actual": 0.3,
             "source_note": "BLS official release, https://example.test", "researched_at_utc": "2026-09-03T10:00:00+00:00"},
        ]}))

        with patch.object(actuals_sync, "_git_pull", return_value=True):
            report = actuals_sync.apply_resolved_inbox(conn, repo_dir, now=dt.datetime(2026, 9, 3, 12, 0, tzinfo=UTC_TZ))

        rows = store.get_event_history(conn, "PPI m/m")
        conn.close()

        assert report.written == 0
        assert report.skipped == 1
        assert rows[0].actual is None
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


if __name__ == "__main__":
    test_run_git_disables_terminal_prompt()
    test_ensure_repo_cloned_clones_when_missing()
    test_ensure_repo_cloned_is_a_noop_when_already_cloned()
    test_git_pull_returns_true_on_success()
    test_git_pull_returns_false_on_failure_never_raises()
    test_git_commit_and_push_succeeds()
    test_git_commit_and_push_treats_nothing_to_commit_as_success()
    test_git_commit_and_push_returns_false_when_push_fails()
    test_git_commit_and_push_retries_push_after_pull_on_rejection()
    test_run_git_catches_timeout_and_returns_completed_process()
    test_git_commit_and_push_returns_false_when_add_fails()
    test_export_writes_candidates_within_cutoff()
    test_export_excludes_candidates_older_than_48_hours()
    test_export_does_not_push_when_candidates_unchanged()
    test_export_retries_push_when_candidates_unchanged_but_something_unpushed_remains()
    test_export_pushes_again_when_candidates_actually_change()
    test_export_excludes_non_usd_country_candidates()
    test_apply_writes_pending_entries_with_cloud_source()
    test_apply_skips_entries_already_resolved()
    test_apply_treats_missing_inbox_file_as_empty()
    test_apply_treats_malformed_inbox_json_as_empty()
    test_apply_treats_inbox_root_list_as_empty()
    test_apply_skips_bare_string_entry_but_still_processes_good_one()
    test_apply_skips_entry_whose_actual_is_a_json_number_not_a_string()
    test_apply_skips_malformed_entry_missing_actual()
    test_apply_pulls_before_reading_the_inbox()
    print("All actuals_sync tests passed.")
