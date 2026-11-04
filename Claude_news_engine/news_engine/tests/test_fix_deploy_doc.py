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


def _step(number: int) -> str:
    """The body of one numbered step, up to the next heading."""
    match = re.search(rf"^## {number}\. .*?(?=^## |\Z)", _text(), re.MULTILINE | re.DOTALL)
    assert match, f"step {number} missing"
    return match.group(0)


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


def test_shell_note_sends_step_10_away_from_plain_git_bash() -> None:
    """Git Bash rewrites schtasks /run into a path, so a plain call there fails and the engine stays stopped."""
    note = next(line for line in _text().splitlines() if line.startswith("Shell:"))
    assert "Every other command" not in note
    assert "Step 10" in note and "Git Bash" in note
    step = _step(10)
    assert "PowerShell or cmd:\n\n```\nschtasks /run /tn NewsEngine_AutoStart\n```" in step
    assert "Git Bash:\n\n```\nMSYS_NO_PATHCONV=1 schtasks /run /tn NewsEngine_AutoStart\n```" in step


def test_step_6_lists_the_seven_real_fills_and_no_august_value() -> None:
    step = _step(6)
    assert "seven fills" in step
    for value in ("7.6", "25.5", "-132.6B", "-134.9B", "0.7%", "0.6%", "3.99M"):
        assert value in step, value
    # The August rows have a NULL country, so a list naming these reads as a false mismatch.
    for value in ("20.6", "-118.8B", "1.3%"):
        assert value not in step, value
    assert "NULL country" in step


def test_step_5_explains_the_29_row_dry_run() -> None:
    step = _step(5)
    assert "29 rows" in step and "28 of the 59 `in_line` rows" in step
    assert "1 Prelim GDP q/q row going from NULL to `in_line`" in step


def test_step_6_reruns_the_dry_run_and_clears_the_reports() -> None:
    step = _step(6)
    commands = [line for line in step.splitlines() if line.startswith("python scripts/backfill_official_actuals.py")]
    assert len(commands) == 3
    assert "--apply" not in commands[0] and "--apply" in commands[1] and "--apply" not in commands[2]
    assert "must fill 0" in step
    assert "rederive_surprise_direction_<stamp>.txt" in step and "backfill-report.txt" in step and "Delete both" in step


def test_steps_1_8_and_9_name_what_really_exists() -> None:
    assert "`research_alerts` in `ops/ops_state.db`" in _step(1) and "Any new table" not in _step(1)
    assert "next to the existing tier1_research.py record-late-check rule" in _step(8)
    assert "tier1_allow_rules.py" not in _text()
    assert "BOTH occurrences of `(plan, record-call, record-late-check)`" in _step(9)


def test_step_11_names_the_path_that_really_fills_each_title() -> None:
    lines = _step(11).splitlines()
    empire = next(line for line in lines if "Empire State" in line)
    home_sales = next(line for line in lines if "Existing Home Sales" in line)
    assert "hourly FRED/ALFRED backfill" in empire and "Existing Home Sales" not in empire
    assert "release poller" in home_sales


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
