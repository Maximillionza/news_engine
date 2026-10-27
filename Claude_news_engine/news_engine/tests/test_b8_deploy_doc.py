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
    "webapp/store.py:621-647": "EVENT_SURPRISE_DIRECTION",
    "config/settings.py:153": "FRED_SERIES_ID_BY_EVENT_TITLE",
    "config/settings.py:443": "JOLTS Job Openings",
    "webapp/actuals_sync.py:40": "MAX_CANDIDATE_AGE_HOURS",
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
    assert not re.search(r"calendar_feed\.py:335|scheduler\.py:188|store\.py:586", text)
