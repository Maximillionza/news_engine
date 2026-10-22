"""
Tests for data_layer/subject_rules.py -- pure functions, no network, no DB.

B6 (2026-10-22), audit AUD-P0-1 / AS-04: foreign central-bank headlines
(ECB, BoE, BoJ, RBA, ...) were scored as US-dollar news for FOMC and CPI
events, and off-subject titles (a gold-led headline that merely mentions
the dollar) voted on FOMC. These tests pin the three rules in order:
foreign_cb (every event title) -> no_fed_coterm (FOMC family) ->
off_subject (FOMC and CPI families, title only).
"""
import sys
import os
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import CPI_FAMILY_TITLES, FOMC_FAMILY_TITLES
from data_layer.subject_rules import (
    b6_exclusion_reason,
    foreign_cb_match,
    names_us_marker,
    passes_subject_rule,
    title_family,
)

_MODULE_PATH = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "data_layer" / "subject_rules.py"

# Probe 1 headlines, copied literally from scripts/audit_fa_probes.py's FOREIGN_CB_HEADLINES.
_PROBE1_FOMC = [
    ("ECB signals faster rate cuts as euro zone stalls", "Lagarde said the central bank is ready to ease further."),
    ("Bank of England delivers surprise rate cut", "The BoE cut rates by 50bp citing weak growth."),
    ("Bank of Japan hawkish, signals rate hike in December", "Ueda said the central bank could raise rates."),
    ("RBA holds, warns rate hike possible", "Australia's central bank kept rates on hold."),
]
# CPI-relevant variants of the same four central banks.
_PROBE1_CPI = [
    ("ECB's Schnabel says inflation risks mean rates must rise", ""),
    ("Bank of England's Pill warns inflation is sticky", ""),
    ("Bank of Japan's Ueda sees inflation near target", ""),
    ("RBA warns inflation still too high", ""),
]

# Real titles from the live backtest_log.db's top_contributions_json (audit AUD-P0-1).
_LIVE_OFFENDERS = [
    "Interest rates must rise further on inflation risks, ECB's Schnabel tells Bloomberg - Reuters",
    "BoE's Pill says a rate hike need not be start of long series - Reuters",
    "Bank of England's Breeden says cost-cutting by firms helping central bank - Reuters",
    "'Godzilla El Niño' is wreaking havoc with Philippine central bank's inflation forecasts",
    "China's slower loan growth is the new normal, central bank governor says - reuters.com",
    "Dollar languishes as inflation awaited; Euro edges up on Lagarde warning",
]


def test_family_sets_are_exact():
    assert FOMC_FAMILY_TITLES == {
        "FOMC Meeting Minutes", "FOMC Statement", "Federal Funds Rate",
        "FOMC Press Conference", "FOMC Economic Projections", "Fed Chairman Warsh Speaks",
    }
    assert CPI_FAMILY_TITLES == {"CPI m/m", "CPI y/y", "Core CPI m/m", "Core CPI y/y"}
    assert title_family("Core PCE Price Index m/m") == "other"
    assert title_family("PPI m/m") == "ppi"


@pytest.mark.parametrize(
    "event_title,title,summary",
    [("FOMC Statement", t, s) for t, s in _PROBE1_FOMC] + [("CPI m/m", t, s) for t, s in _PROBE1_CPI],
)
def test_probe1_foreign_cb_dropped(event_title, title, summary):
    assert b6_exclusion_reason(title, summary, event_title) == "foreign_cb"


@pytest.mark.parametrize(
    "event_title,title,summary",
    [
        ("FOMC Statement", "Fed signals faster rate cuts as US growth slows", "Federal Reserve officials see easing ahead"),
        ("FOMC Statement", "Warsh says inflation fight is not over", ""),
        ("CPI m/m", "US CPI rises 0.4% in September, hotter than forecast", ""),
        ("CPI m/m", "Fed's Waller says inflation still too high", ""),
    ],
)
def test_fed_headlines_kept(event_title, title, summary):
    assert b6_exclusion_reason(title, summary, event_title) is None


@pytest.mark.parametrize("event_title", ["FOMC Statement", "CPI m/m"])
@pytest.mark.parametrize("title", _LIVE_OFFENDERS)
def test_live_offender_titles_excluded(event_title, title):
    assert b6_exclusion_reason(title, "", event_title) == "foreign_cb"


def test_foreign_cb_ignores_us_lookalikes():
    for title in (
        "Bank of America CEO sees at least 10% drop in Q3 investment banking fees",
        "Federal Reserve Bank of New York survey shows inflation expectations rise",
        "New York Fed's Williams says policy is well positioned",
        "Novo's weight-loss pill sales jump",
    ):
        assert foreign_cb_match(title) is None, title
    assert foreign_cb_match("Reserve Bank of India holds rates") is not None


def test_generic_fomc_term_needs_fed_coterm():
    assert b6_exclusion_reason(
        "Gold retains key reserve status despite surging bond yields, central bankers say", "", "FOMC Statement"
    ) == "no_fed_coterm"
    # The co-term is found in the summary, so the article reaches the title rule (and fails it there).
    assert b6_exclusion_reason(
        "Rate cut bets rise", "Traders price a Federal Reserve cut in December", "FOMC Statement"
    ) == "off_subject"


def test_gold_led_dollar_title_not_scored_for_fomc():
    title = "Gold edges up as October rate hike bets ease, stronger dollar cap gains"
    assert b6_exclusion_reason(title, "Traders trimmed bets on a Federal Reserve hike", "FOMC Meeting Minutes") == "off_subject"
    assert b6_exclusion_reason(title, "", "FOMC Meeting Minutes") == "no_fed_coterm"


def test_subject_rule_accepts_us_subjects():
    fomc_ok = [
        "Dollar firms as Fed officials push back on cuts",
        "Treasury yields climb after hot jobs data",
        "US 10-year yields hit two-month high",
        "Greenback slips ahead of Warsh testimony",
    ]
    cpi_only_ok = [
        "U.S. consumer prices rise 0.4% in September",
        "American inflation expectations climb",
        "Inflation data due Wednesday, CPI expected to ease",
        "BLS delays September report",
    ]
    for title in fomc_ok:
        assert passes_subject_rule(title, "fomc"), title
        assert passes_subject_rule(title, "cpi"), title
    for title in cpi_only_ok:
        assert passes_subject_rule(title, "cpi"), title


def test_subject_rule_rejects_off_subject():
    for title in ("Americans' incomes rose and poverty fell, Census Bureau says", "AI chip stocks slump"):
        assert not passes_subject_rule(title, "fomc"), title
    for title in ("Inflation worries weigh on us all", "Japan CPI rises 2.9%", "Euro zone inflation eases to 2.1%"):
        assert not passes_subject_rule(title, "cpi"), title


def test_us_marker_is_case_sensitive():
    assert names_us_marker("tells us nothing") is False
    for text in ("US", "U.S.", "USA", "American"):
        assert names_us_marker(text) is True, text
    assert names_us_marker("USD rallies") is False


def test_foreign_dollar_is_not_the_dollar():
    assert not passes_subject_rule("Canadian dollar firms after inflation data", "cpi")
    assert not passes_subject_rule("Australian dollar jumps as rate hike bets build", "fomc")


def test_other_titles_only_get_foreign_cb():
    assert b6_exclusion_reason("US payrolls jump 250,000; rate cut bets fade", "", "Non-Farm Employment Change") is None
    assert b6_exclusion_reason("BoE's Bailey says UK hiring slows", "", "Non-Farm Employment Change") == "foreign_cb"
    assert passes_subject_rule("AI chip stocks slump", "jobs") is True


def test_summary_foreign_cb_only_without_us_title():
    assert b6_exclusion_reason("Markets steady", "The ECB held rates", "Retail Sales m/m") == "foreign_cb"
    assert b6_exclusion_reason("US retail sales jump 0.6%", "Elsewhere the ECB held rates", "Retail Sales m/m") is None


def test_source_has_no_backspace_bytes():
    assert b"\x08" not in _MODULE_PATH.read_bytes()


def test_audit_probe1_now_drops_all():
    from scripts.audit_fa_probes import probe_foreign_cb_sign
    lines = probe_foreign_cb_sign()
    assert len(lines) == 4
    for line in lines:
        assert line.startswith("DROP"), line
