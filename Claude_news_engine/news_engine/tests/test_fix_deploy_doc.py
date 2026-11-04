"""Static check: docs/fix-deploy.md keeps its safety-relevant ordering, names real scripts and holds no secrets."""
import re
import subprocess
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
DOC = APP / "docs" / "fix-deploy.md"
METHODOLOGY = APP / "docs" / "tier1-methodology.md"

# Markers in the order the runbook must present them (stop before backup before merge ... rollback last).
ORDERED_MARKERS = (
    "Stop the single engine copy",
    "Backup",
    "git merge --no-ff news-engine/fix-audit",
    "rederive_surprise_direction.py",
    "backfill_official_actuals.py",
    "register_tier1_tasks.ps1",
    "alert:*",
    "SOURCE POLICY",
    "Restart",
    "Checks",
    "git revert -m 1",
)


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_markers_appear_in_order() -> None:
    text = _text()
    pos = -1
    for marker in ORDERED_MARKERS:
        found = text.find(marker, pos + 1)
        assert found > pos, f"{marker!r} missing or out of order"
        pos = found


def test_every_step_is_applied_by_the_controller() -> None:
    assert "applied at deploy by the controller" in _text()


def test_every_named_script_exists() -> None:
    names = set(re.findall(r"scripts/[A-Za-z0-9_/]+\.(?:py|ps1)", _text()))
    assert {"scripts/rederive_surprise_direction.py", "scripts/backfill_official_actuals.py",
            "scripts/register_tier1_tasks.ps1"} <= names
    for name in names:
        assert (APP / name).is_file(), name


def test_no_secret_looking_text() -> None:
    text = _text()
    assert not re.search(r"_API_KEY\s*=\s*\S", text)
    assert not re.search(r"\b[0-9a-f]{32,}\b", text)
    assert not re.search(r"\b\d{8,}:[A-Za-z0-9_-]{30,}\b", text)  # Telegram bot token shape


def test_methodology_is_current_and_pre_registers_the_floor() -> None:
    result = subprocess.run([sys.executable, "scripts/export_tier1_methodology.py", "--check"],
                            cwd=APP, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    text = METHODOLOGY.read_text(encoding="utf-8")
    assert "NEWS_CALL_MIN_ARTICLES = 3" in text
    assert "2026-11-03" in text
    assert "never tuned on results" in text


def test_rederive_apply_command_uses_an_existing_report_folder() -> None:
    """--report is a FOLDER for rederive_surprise_direction.py (exit 4 if missing); a file name would abort the apply step."""
    text = _text()
    commands = re.findall(r"rederive_surprise_direction\.py[^\r\n]*--report\s+(\S+)", text)
    assert commands, "no rederive apply command with --report found"
    for target in commands:
        assert not target.endswith(".txt"), f"--report must be a folder, got {target!r}"
        assert (APP / target).is_dir(), f"--report folder {target!r} does not exist relative to the app dir"
