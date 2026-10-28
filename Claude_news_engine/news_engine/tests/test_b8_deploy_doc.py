"""Static check: the file:line pointers in docs/b8-deploy.md (U2 root cause) land on the code they name."""
import re
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
DOC = APP / "docs" / "b8-deploy.md"

# pointer -> text that must appear on (or within) the cited lines
EXPECTED = {
    "data_layer/calendar_feed.py:383": 'actual=item.get("actual") or None',
    "webapp/scheduler.py:205-209": "get_actual_from_fred(",
    "webapp/store.py:34": "EVENT_SURPRISE_DIRECTION",
    "webapp/store.py:623-649": "EVENT_SURPRISE_DIRECTION",
    "config/settings.py:153": "FRED_SERIES_ID_BY_EVENT_TITLE",
    "config/settings.py:443": "JOLTS Job Openings",
    "webapp/actuals_sync.py:40": "MAX_CANDIDATE_AGE_HOURS",
    # Section 1: the trend-window readers the seed and fills change.
    "scoring/backtest_accumulator.py:332": "get_event_history(conn, event_title)",
    "webapp/app.py:147": "get_event_history(conn, title)",
    "scoring/probability_engine.py:512": "get_event_history(conn, precursor_title, limit=6)",
}


def test_u2_file_line_pointers_resolve() -> None:
    text = DOC.read_text(encoding="utf-8")
    for pointer, needle in EXPECTED.items():
        assert pointer in text, pointer
        path, span = pointer.split(":")
        lo, _, hi = span.partition("-")
        lines = (APP / path).read_text(encoding="utf-8").splitlines()
        window = "\n".join(lines[int(lo) - 1:int(hi or lo)])
        assert needle in window, f"{pointer} does not contain {needle!r}"
    # No stale pointers from the first draft.
    assert not re.search(r"calendar_feed\.py:335|scheduler\.py:188|store\.py:586|store\.py:621-647", text)


def test_runbook_commands_are_shell_agnostic_and_rollback_is_precise() -> None:
    text = DOC.read_text(encoding="utf-8")
    # cmd-only and PowerShell-only temp paths broke --report/--out in the other shells.
    assert "%TEMP%" not in text and "$env:" not in text
    # No escaped inner double quotes (PowerShell 5.1 cannot pass them to python -c).
    assert '\\"' not in text
    # The old rollback deleted every source='fred' row after the apply, including graded FF rows.
    assert "recorded_at_utc >=" not in text
    assert 'seed_fred_history.py --rollback "<seed run recorded_at_utc>" --apply' in text
    # Step 7 quotes the real format_report output.
    assert "APPLIED - nothing to write" in text and "inserts: 0  fills: 0" in text
