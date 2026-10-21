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
    assert ("description: Daily (08:06 SAST) Tier 1 research with an 8-day lookahead for upcoming "
            "USD JUDGMENT releases (PPI/NFP/FOMC/GDP/Core PCE/ISM/Retail)") in new
    for needle in ("python scripts/tier1_research.py plan", "tier1_research.py record-call",
                   "tier1_research.py record-late-check", "docs/tier1-methodology.md",
                   "NOT researched by this task (formula tier", "Do not modify any file.",
                   "first run exactly cd C:/Users/Masoodt/Documents/Claude/Projects/.worktrees/news-engine-live/Claude_news_engine/news_engine", "with the Read tool (do not run Python"):
        assert needle in new, needle
    # The old free-hand persistence path, the deleted Step 2 and the Mon/Thu cadence are gone; CPI left the
    # consolidation scope.
    for gone in ("record_tier1_prediction()", "Step 2", "applies to CPI m/m", "Mon/Thu", "Twice-weekly"):
        assert gone not in new, gone


def test_preapproval_step_gives_exact_rules_location_and_verification() -> None:
    text = DOC.read_text(encoding="utf-8")
    step = text.split("## 3. Switch the research task to the CLI\n", 1)[1].split("\n## 4. Rollback", 1)[0]
    assert ("OWNER APPROVAL REQUIRED — standing permission rules; the controller does not apply this "
            "without the owner's yes") in step
    assert r"C:\Users\Masoodt\Documents\Claude\Projects\Claude_news_engine\news_engine\.claude\settings.local.json" in step
    for sub in ("plan", "record-call", "record-late-check"):
        assert f'"Bash(python scripts/tier1_research.py {sub}:*)"' in step, sub
        assert f'"PowerShell(python scripts/tier1_research.py {sub}:*)"' in step, sub
    for rule in ('"Bash(cd C:/Users/Masoodt/Documents/Claude/Projects/.worktrees/news-engine-live/Claude_news_engine/news_engine)"', '"Read"', '"WebSearch"', '"WebFetch"'):
        assert rule in step, rule
    assert '"Bash(python:*)"' not in step          # named in the prose only as the rule NOT to add
    assert "STEP 5 report with no permission prompt" in step


def test_research_cadence_is_daily_0806_with_the_24h_window_consequence_stated() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "`6 8 * * *`" in text and "`6 8 * * 1,4`" in text   # new schedule, and the old one for rollback
    assert "about 6.4h before a 12:30 UTC" in text
    assert "It does NOT fire for a release the next day" in text


def test_previous_skill_is_kept_for_rollback() -> None:
    old = _fenced("Previous SKILL.md")
    assert old.startswith("---\nname: tier1-cpi-ppi-autoresearch\n")
    assert "record_tier1_prediction()" in old
    assert "STEP 2" in old
