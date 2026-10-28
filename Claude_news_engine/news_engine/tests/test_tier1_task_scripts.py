"""Static checks on the Windows task scripts for the Tier 1 formula capture (B3 T4).

Nothing is executed: the files are read as bytes and inspected.
"""
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
BAT = SCRIPTS / "tier1_capture_scheduled.bat"
VBS = SCRIPTS / "tier1_capture_scheduled.vbs"
PS1 = SCRIPTS / "register_tier1_tasks.ps1"


def test_register_tier1_tasks_script_has_both_tasks_with_start_when_available() -> None:
    text = PS1.read_bytes().decode("utf-8")
    for needle in ("NewsEngine_Tier1Weekly", "NewsEngine_Tier1Daily", "-StartWhenAvailable",
                   "-DaysOfWeek Monday", "-Daily", "tier1_capture_scheduled.vbs"):
        assert needle in text, needle
    assert text.count("-At 07:00") == 2
    assert "schtasks" not in text


def test_tier1_bat_passes_192_hours_for_weekly_and_48_by_default() -> None:
    text = BAT.read_bytes().decode("utf-8")
    assert "set WINDOW=48" in text
    assert '"%1"=="weekly" set WINDOW=192' in text
    assert "--window-hours %WINDOW%" in text
    assert r"--bt-db scoring\backtest_log.db" in text
    assert r"--dash-db webapp\dashboard.db" in text
    assert r"scripts\tier1_capture_scheduled.log" in text
    assert "tier1_capture_scheduled.bat" in VBS.read_bytes().decode("utf-8")


def test_tier1_bat_runs_capture_tier1() -> None:
    # B12: one task path runs both phases (Cleveland formula, then Kalshi market-implied).
    text = BAT.read_bytes().decode("utf-8")
    commands = [line for line in text.splitlines() if line.startswith("python ")]
    assert len(commands) == 1
    assert r"-- scripts\capture_tier1.py --window-hours %WINDOW%" in commands[0]
    assert "capture_nowcast_from_cleveland" not in commands[0]
    ps1 = PS1.read_bytes().decode("utf-8")
    assert ps1.count("capture_tier1.py --window-hours") == 2


def test_tier1_task_scripts_use_crlf() -> None:
    for path in (BAT, VBS, PS1):
        data = path.read_bytes()
        assert b"\n" in data, path.name
        assert data.count(b"\n") == data.count(b"\r\n"), path.name
