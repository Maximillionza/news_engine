"""README must stay in step with the real tabs, DBs and the jobs pointer."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DB_PATHS = (
    "webapp/dashboard.db",
    "scoring/backtest_log.db",
    "alerting/shock_alerts.db",
    "ops/ops_state.db",
)


def test_readme_matches_tabs_dbs_and_jobs_pointer() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    html = (ROOT / "webapp" / "static" / "index.html").read_text(encoding="utf-8")
    labels = re.findall(r'aria-controls="(?:view|stats-pane)-[^"]+"[^>]*>([^<]+)<', html)
    assert len(labels) == 9
    for label in labels:
        assert label.strip() in readme, label
    for db in DB_PATHS:
        assert db in readme, db
    assert "docs/feature-inventory-2026-09-11.md" in readme
    assert not (ROOT / "HANDOVER.md").exists()
