"""Static check: docs/b10-deploy.md keeps its safety-relevant ordering and names only real scripts."""
import re
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
DOC = APP / "docs" / "b10-deploy.md"


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_backup_name_and_backfill_order() -> None:
    text = _text()
    assert "shock_alerts.db.pre_b10_" in text
    # The dry run is documented before the first --apply.
    assert "backfill_shock_grades.py" in text
    first_apply = text.index("--apply")
    assert text.index("Dry run") < first_apply
    assert "graded 0" in text
    assert "14 of 26" in text


def test_rollback_heading_exists() -> None:
    assert re.search(r"^## .*Rollback", _text(), re.MULTILINE)


def test_commands_are_shell_agnostic() -> None:
    text = _text()
    assert "%TEMP%" not in text and "$env:" not in text
    assert '\\"' not in text


def test_every_named_script_exists() -> None:
    names = set(re.findall(r"scripts/[A-Za-z0-9_/]+\.py", _text()))
    assert "scripts/backfill_shock_grades.py" in names
    for name in names:
        assert (APP / name).is_file(), name


def test_stop_step_matches_b8_deploy_doc() -> None:
    """The Get-CimInstance stop lines must equal B8's (a lone backslash-a in a .NET regex is BEL, not a path)."""
    def _lines(path: Path) -> list[str]:
        return [l for l in path.read_text(encoding="utf-8").splitlines() if l.startswith("Get-CimInstance")]

    assert _lines(DOC) == _lines(APP / "docs" / "b8-deploy.md")
    assert r"webapp\\app\.py" in _text()
