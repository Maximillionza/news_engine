"""B10 C5: the one-off scripts live in scripts/archive and nothing in production depends on them."""
from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
ARCHIVE = APP / "scripts" / "archive"

ARCHIVED_STEMS = [
    "market_reaction_phase0", "audit_fa_probes", "audit_shock_impact",
    "migrate_adp_title_rename", "migrate_country_backfill", "migrate_gdp_title_rename",
    "stats_phase0_news_input", "compare_fred_lookahead",
    "event_study_once", "event_study_groups", "event_study_metrics", "event_study_checks",
]

PRODUCTION_DIRS = ["alerting", "webapp", "ops", "scoring", "data_layer", "config", "scripts"]


def _production_files() -> list[Path]:
    files: list[Path] = []
    for name in PRODUCTION_DIRS:
        base = APP / name
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            # Hidden dirs hold git-ignored copies, e.g. webapp/.actuals_sync/repo (a full clone, live only).
            hidden = any(part.startswith(".") for part in path.relative_to(base).parts)
            if ARCHIVE in path.parents or "node_modules" in path.parts or hidden:
                continue
            files.append(path)
    return files


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append(node.module)
            if node.module == "scripts":
                found.extend(f"scripts.{alias.name}" for alias in node.names)
    return found


def test_no_production_module_imports_archive_or_one_offs() -> None:
    forbidden = {f"scripts.{stem}" for stem in ARCHIVED_STEMS}
    offenders = []
    for path in _production_files():
        for module in _imported_modules(path):
            if module.startswith("scripts.archive") or module in forbidden:
                offenders.append(f"{path.relative_to(APP)} -> {module}")
    assert offenders == []


def test_archived_scripts_load_standalone(tmp_path: Path) -> None:
    code = (
        "import importlib.util, sys\n"
        "spec = importlib.util.spec_from_file_location('archived_under_test', sys.argv[1])\n"
        "mod = importlib.util.module_from_spec(spec)\n"
        "sys.modules[spec.name] = mod\n"
        "spec.loader.exec_module(mod)\n"
    )
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    for stem in ARCHIVED_STEMS:
        path = ARCHIVE / f"{stem}.py"
        assert path.exists(), path
        result = subprocess.run(
            [sys.executable, "-c", code, str(path)], cwd=tmp_path, env=env,
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, f"{stem}: {result.stderr[-600:]}"


def test_every_archived_script_has_a_readme_line() -> None:
    readme = (ARCHIVE / "README.md").read_text(encoding="utf-8")
    missing = [stem for stem in ARCHIVED_STEMS if f"{stem}.py" not in readme]
    assert missing == []


def test_scheduled_entry_points_stay_in_scripts() -> None:
    pattern = re.compile(r"scripts[\\/]+([A-Za-z0-9_]+\.py)")
    launchers = []
    for folder in (APP / "scripts", APP / "alerting" / "scripts"):
        for ext in ("*.bat", "*.vbs", "*.ps1"):
            launchers.extend(folder.glob(ext))
    assert launchers
    for launcher in launchers:
        text = launcher.read_text(encoding="utf-8", errors="replace")
        for name in pattern.findall(text):
            candidates = [APP / "scripts" / name, APP / "alerting" / "scripts" / name]
            assert any(c.exists() for c in candidates), f"{launcher.name} names missing {name}"


def test_event_study_repo_root_is_git_root() -> None:
    from scripts.archive import event_study_once
    assert event_study_once.REPO_ROOT == APP.parents[1]
