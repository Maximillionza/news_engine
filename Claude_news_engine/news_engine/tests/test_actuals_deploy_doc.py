"""Static check: docs/actuals-deploy.md keeps its safety-relevant ordering and names only real scripts."""
import re
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
DOC = APP / "docs" / "actuals-deploy.md"

KEY_NAMES = ("BLS_API_KEY", "BEA_API_KEY", "CENSUS_API_KEY", "EIA_API_KEY", "FRED_API_KEY")
FIRST_RELEASE_TITLES = (
    "Advance GDP q/q",
    "Advance GDP Price Index q/q",
    "Core PCE Price Index m/m",
    "Unemployment Claims",
    "Personal Income m/m",
    "Personal Spending m/m",
)


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_backup_name_and_backfill_order() -> None:
    text = _text()
    assert "dashboard.db.pre_act_" in text
    assert "backfill_official_actuals.py" in text
    # The dry run is documented before the first --apply.
    first_apply = text.index("--apply")
    assert text.index("Dry run") < first_apply
    assert "filled 0" in text


def test_rollback_heading_exists() -> None:
    assert re.search(r"^## .*Rollback", _text(), re.MULTILINE)


def test_commands_are_shell_agnostic() -> None:
    text = _text()
    assert "%TEMP%" not in text and "$env:" not in text
    assert '\\"' not in text


def test_every_named_script_exists() -> None:
    names = set(re.findall(r"scripts/[A-Za-z0-9_/]+\.py", _text()))
    assert "scripts/backfill_official_actuals.py" in names
    assert "scripts/verify_official_actuals.py" in names
    for name in names:
        assert (APP / name).is_file(), name


def test_key_check_lists_names_and_never_prints_values() -> None:
    text = _text()
    for name in KEY_NAMES:
        assert name in text, name
    # The key check prints booleans only (bool(...)), never a key attribute on its own.
    assert "bool(getattr(k, n))" in text
    assert not re.search(r"print\(\s*k\.|print\(\s*load_keys\(\)\s*\)", text)
    # No key-shaped literal (long hex/alphanumeric run after an equals sign) is embedded.
    assert not re.search(r"_API_KEY\s*=\s*\S", text)


def test_first_release_verification_lists_the_target_titles() -> None:
    text = _text()
    assert "2026-10-29" in text and "12:30Z" in text
    for title in FIRST_RELEASE_TITLES:
        assert title in text, title


def test_coverage_table_matches_committed_spec() -> None:
    spec = (APP / "docs" / "superpowers" / "specs" / "2026-10-28-act-coverage.md").read_text(encoding="utf-8")
    assert spec.strip().replace("\r\n", "\n") in _text().replace("\r\n", "\n")


def test_stop_step_matches_b10_deploy_doc() -> None:
    def _lines(path: Path) -> list[str]:
        return [l for l in path.read_text(encoding="utf-8").splitlines() if l.startswith("Get-CimInstance")]

    assert _lines(DOC) == _lines(APP / "docs" / "b10-deploy.md")
