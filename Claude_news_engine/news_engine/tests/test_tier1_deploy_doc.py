"""Static checks on docs/tier1-b3-deploy.md (B3): the runbook the controller applies at deploy.

Nothing is executed; the live SKILL.md is never read (the doc carries both versions).
"""
from pathlib import Path

DOC = Path(__file__).resolve().parent.parent / "docs" / "tier1-b3-deploy.md"


def _fenced(section_heading: str) -> str:
    text = DOC.read_text(encoding="utf-8")
    after = text.split(f"## {section_heading}\n", 1)[1]
    return after.split("````text\n", 1)[1].split("\n````", 1)[0]


def test_runbook_has_the_dry_run_registration_retirement_and_rollback_steps() -> None:
    text = DOC.read_text(encoding="utf-8")
    for needle in (
        "python scripts/capture_nowcast_from_cleveland.py --dry-run --window-hours 192",
        r"powershell -ExecutionPolicy Bypass -File scripts\register_tier1_tasks.ps1",
        "Get-ScheduledTask NewsEngine_Tier1*",
        "StartWhenAvailable True",
        "tier1-nowcast-release-eve",
        r"C:\Users\Masoodt\.claude\scheduled-tasks\tier1-cpi-ppi-autoresearch\SKILL.md",
        "Unregister-ScheduledTask -TaskName NewsEngine_Tier1Weekly",
        "Unregister-ScheduledTask -TaskName NewsEngine_Tier1Daily",
    ):
        assert needle in text, needle


def test_new_skill_runs_only_the_cli_and_never_researches_cpi() -> None:
    new = _fenced("New SKILL.md")
    assert new.startswith("---\nname: tier1-cpi-ppi-autoresearch\n")
    assert ("description: Twice-weekly (Mon/Thu 08:06 SAST) Tier 1 research with an 8-day lookahead for upcoming "
            "USD JUDGMENT releases (PPI/NFP/FOMC/GDP/Core PCE/ISM/Retail)") in new
    for needle in ("python scripts/tier1_research.py plan", "tier1_research.py record-call",
                   "tier1_research.py record-late-check", "docs/tier1-methodology.md",
                   "NOT researched by this task (formula tier", "Do not modify any file."):
        assert needle in new, needle
    # The old free-hand persistence path and the deleted Step 2 are gone; CPI left the consolidation scope.
    for gone in ("record_tier1_prediction()", "Step 2", "applies to CPI m/m"):
        assert gone not in new, gone


def test_previous_skill_is_kept_for_rollback() -> None:
    old = _fenced("Previous SKILL.md")
    assert old.startswith("---\nname: tier1-cpi-ppi-autoresearch\n")
    assert "record_tier1_prediction()" in old
    assert "STEP 2" in old
