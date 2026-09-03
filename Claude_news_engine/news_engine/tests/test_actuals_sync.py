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
