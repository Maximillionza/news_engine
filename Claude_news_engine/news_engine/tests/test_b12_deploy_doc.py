"""Static checks on docs/b12-deploy.md (B12): the runbook the controller applies at deploy.

Nothing is executed; the live SKILL.md is never read (the doc carries both versions).
"""
from pathlib import Path

DOC = Path(__file__).resolve().parent.parent / "docs" / "b12-deploy.md"


def _fenced(section_heading: str) -> str:
    text = DOC.read_text(encoding="utf-8")
    after = text.split(f"## {section_heading}\n", 1)[1]
    return after.split("````text\n", 1)[1].split("\n````", 1)[0]


def test_runbook_has_backup_registration_capture_skill_backup_restart_and_rollback() -> None:
    text = DOC.read_text(encoding="utf-8")
    for needle in (
        "backtest_log.db.pre_b12_",
        "register_tier1_tasks.ps1",
        "capture_tier1.py --dry-run --window-hours 192",
        "SKILL.md.bak_",
        "docs/b11-deploy.md",
        "git revert",
        r"C:\Users\Masoodt\.claude\scheduled-tasks\tier1-cpi-ppi-autoresearch\SKILL.md",
        "Get-ScheduledTask NewsEngine_Tier1*",
        "StartWhenAvailable",
        "api/stats/events?event=Federal%20Funds%20Rate",
        '"tier1_tier": "market_implied"',
    ):
        assert needle in text, needle


def test_new_skill_drops_the_kalshi_and_formula_titles_and_keeps_the_cli_rules() -> None:
    new = _fenced("New SKILL.md")
    assert new.startswith("---\nname: tier1-cpi-ppi-autoresearch\n")
    for needle in ("NOT researched by this task (market-implied tier", "CME FedWatch", "tier1_research.py plan",
                   "Do not modify any file.", "(FOMC/GDP/ISM Services/Core Retail)",
                   "CPI y/y / Core CPI y/y / Core PCE Price Index m/m: NOT researched by this task (formula tier",
                   "SUB-READING CONSOLIDATION (applies to Core Retail Sales m/m"):
        assert needle in new, needle
    for gone in ("- PPI m/m (POC_PPI_Leading_Indicators)", "- Non-Farm Employment Change (POC_NFP_Leading_Indicators)",
                 "- ISM Manufacturing PMI (POC_ISM_Manufacturing_PMI)", "- Core PCE Price Index m/m (POC_Core_PCE)",
                 "/ Federal Funds Rate (POC_FOMC_Rate_Decision)", "/ Advance GDP q/q /",
                 "- Retail Sales m/m / Core Retail Sales m/m"):
        assert gone not in new, gone
    for ticker in ("KXUSPPI", "KXPAYROLLS", "KXFED", "KXGDP", "KXISMPMI", "KXUSRETAIL"):
        assert ticker in new, ticker


def test_previous_skill_is_kept_for_rollback() -> None:
    old = _fenced("Previous SKILL.md")
    assert old.startswith("---\nname: tier1-cpi-ppi-autoresearch\n")
    assert "- PPI m/m (POC_PPI_Leading_Indicators)" in old
    assert "Do not modify any file." in old


def test_the_doc_uses_crlf() -> None:
    data = DOC.read_bytes()
    assert b"\n" in data
    assert data.count(b"\n") == data.count(b"\r\n")
