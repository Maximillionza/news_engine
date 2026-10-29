"""ACT: the cloud web-fallback queue is retired; nothing in production may bring it back."""
from __future__ import annotations

from pathlib import Path

APP = Path(__file__).resolve().parents[1]


def test_web_fallback_is_retired() -> None:
    assert not (APP / "webapp" / "actuals_sync.py").exists()
    assert not (APP / "tests" / "test_actuals_sync.py").exists()
    assert "actuals_sync" not in (APP / "webapp" / "app.py").read_text(encoding="utf-8")
    assert "get_events_with_stale_missing_actual" not in (APP / "webapp" / "store.py").read_text(encoding="utf-8")
    # The manual tool lists the new missing-numeric view, not the old queue.
    script = (APP / "scripts" / "fill_missing_actuals.py").read_text(encoding="utf-8")
    assert "get_events_with_stale_missing_actual" not in script
    assert "missing_numeric_rows" in script
