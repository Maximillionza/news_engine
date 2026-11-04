"""
Tests for config.settings.EVENT_REGISTRY and
data_layer/event_registry.py's get_approximate_next_occurrence().
"""
import datetime as dt
import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import EVENT_REGISTRY, EVENT_INFLUENCE_LINKS, UTC_TZ
from data_layer.calendar_feed import EconomicEvent
from data_layer.event_registry import get_approximate_next_occurrence
import webapp.store as store


def test_event_registry_every_entry_has_impact_and_interval():
    print("=== EVENT_REGISTRY: every entry has a valid impact tier and a positive avg_interval_months ===")
    for title, entry in EVENT_REGISTRY.items():
        assert entry["impact"] in ("Low", "Medium", "High"), f"{title!r} has an invalid impact tier: {entry['impact']!r}"
        assert entry["avg_interval_months"] > 0, f"{title!r} has a non-positive avg_interval_months"
    print("PASS\n")


def test_event_registry_covers_every_event_surprise_direction_title():
    print("=== EVENT_REGISTRY: every EVENT_SURPRISE_DIRECTION title is also registered ===")
    from config.settings import EVENT_SURPRISE_DIRECTION
    missing = [t for t in EVENT_SURPRISE_DIRECTION if t not in EVENT_REGISTRY]
    assert not missing, f"titles scored today but missing from EVENT_REGISTRY: {missing}"
    print("PASS\n")


def _event(title, event_time_utc, forecast="0.2%", actual=None, impact="High"):
    return EconomicEvent(title=title, country="USD", impact=impact, event_time_utc=event_time_utc, forecast=forecast, actual=actual)


def test_get_approximate_next_occurrence_unregistered_title_returns_none():
    print("=== get_approximate_next_occurrence: a title not in EVENT_REGISTRY returns None ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = store.get_connection(Path(tmp) / "test.db")
        try:
            assert get_approximate_next_occurrence("Not A Real Event", conn) is None
        finally:
            conn.close()
    print("PASS\n")


def test_get_approximate_next_occurrence_no_sources_returns_none():
    print("=== get_approximate_next_occurrence: no FF snapshot, no macro_calendar row, no resolved history -> None ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = store.get_connection(Path(tmp) / "test.db")
        try:
            assert get_approximate_next_occurrence("CPI m/m", conn, now=dt.date(2026, 9, 2)) is None
        finally:
            conn.close()
    print("PASS\n")


def test_get_approximate_next_occurrence_tier3_cadence_math():
    print("=== get_approximate_next_occurrence: falls back to last-confirmed + avg_interval_months when no real source has an answer ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = store.get_connection(Path(tmp) / "test.db")
        try:
            last = dt.datetime(2026, 8, 13, 12, 30, tzinfo=UTC_TZ)
            store.upsert_event_history(conn, _event("CPI m/m", last, actual="0.3%"), surprise_direction="higher", now=last)
            result = get_approximate_next_occurrence("CPI m/m", conn, now=dt.date(2026, 9, 2))
            # avg_interval_months=1.0 -> ~30 days after 2026-08-13
            assert result == dt.date(2026, 8, 13) + dt.timedelta(days=30)
        finally:
            conn.close()
    print("PASS\n")


def test_get_approximate_next_occurrence_tier3_fractional_interval():
    print("=== get_approximate_next_occurrence: FOMC's 1.6-month cadence produces a real fractional-month offset, not a rounded whole month ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = store.get_connection(Path(tmp) / "test.db")
        try:
            last = dt.datetime(2026, 7, 29, 18, 0, tzinfo=UTC_TZ)
            store.upsert_event_history(conn, _event("FOMC Statement", last, forecast=None, actual="ok", impact="High"), surprise_direction=None, now=last)
            result = get_approximate_next_occurrence("FOMC Statement", conn, now=dt.date(2026, 9, 2))
            expected_days = round(1.6 * 30.4368)
            assert result == dt.date(2026, 7, 29) + dt.timedelta(days=expected_days)
        finally:
            conn.close()
    print("PASS\n")


def test_get_approximate_next_occurrence_macro_calendar_beats_cadence_math():
    print("=== get_approximate_next_occurrence: a macro_calendar row wins over the cadence-math fallback ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = store.get_connection(Path(tmp) / "test.db")
        try:
            last = dt.datetime(2026, 8, 13, 12, 30, tzinfo=UTC_TZ)
            store.upsert_event_history(conn, _event("CPI m/m", last, actual="0.3%"), surprise_direction="higher", now=last)
            store.upsert_macro_calendar_event(
                conn, "CPI m/m", event_date="2026-09-10", estimated_time_utc=None,
                time_source="history_derived", now=dt.datetime(2026, 9, 2, tzinfo=UTC_TZ),
            )
            result = get_approximate_next_occurrence("CPI m/m", conn, now=dt.date(2026, 9, 2))
            assert result == dt.date(2026, 9, 10), "macro_calendar's real estimate must win over the cadence-math guess"
        finally:
            conn.close()
    print("PASS\n")


def test_get_approximate_next_occurrence_ff_snapshot_beats_everything():
    print("=== get_approximate_next_occurrence: a real FF snapshot row wins over both macro_calendar and cadence math ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = store.get_connection(Path(tmp) / "test.db")
        try:
            last = dt.datetime(2026, 8, 13, 12, 30, tzinfo=UTC_TZ)
            store.upsert_event_history(conn, _event("CPI m/m", last, actual="0.3%"), surprise_direction="higher", now=last)
            store.upsert_macro_calendar_event(
                conn, "CPI m/m", event_date="2026-09-10", estimated_time_utc=None,
                time_source="history_derived", now=dt.datetime(2026, 9, 2, tzinfo=UTC_TZ),
            )
            future_event = _event("CPI m/m", dt.datetime(2026, 9, 11, 12, 30, tzinfo=UTC_TZ), forecast="0.2%")
            store.save_calendar_snapshot_if_changed(conn, [future_event], dt.datetime(2026, 9, 2, tzinfo=UTC_TZ))
            result = get_approximate_next_occurrence("CPI m/m", conn, now=dt.date(2026, 9, 2))
            assert result == dt.date(2026, 9, 11), "a real FF snapshot occurrence must win over every fallback"
        finally:
            conn.close()
    print("PASS\n")


def test_event_influence_links_every_title_is_registered():
    print("=== EVENT_INFLUENCE_LINKS: every target and precursor title is present in EVENT_REGISTRY ===")
    for target, precursors in EVENT_INFLUENCE_LINKS.items():
        assert target in EVENT_REGISTRY, f"link target {target!r} is not in EVENT_REGISTRY — a link to an unregistered title is a config bug"
        for precursor_title, weight in precursors:
            assert precursor_title in EVENT_REGISTRY, f"link precursor {precursor_title!r} (-> {target!r}) is not in EVENT_REGISTRY"
            assert 0.0 < weight <= 1.0, f"link {precursor_title!r} -> {target!r} has an out-of-range weight: {weight}"
    print("PASS\n")


def test_rejected_adp_is_no_precursor_and_claims_lead_nfp():
    print("=== EVENT_INFLUENCE_LINKS: ADP (rejected by the workbook) feeds nothing; claims is NFP's only link ===")
    for precursors in EVENT_INFLUENCE_LINKS.values():
        assert "ADP Non-Farm Employment Change" not in dict(precursors)
    assert EVENT_INFLUENCE_LINKS["Non-Farm Employment Change"] == [("Unemployment Claims", 0.40)]
    print("PASS\n")


def test_event_influence_links_drops_the_old_hardcoded_ppi_link():
    print("=== EVENT_INFLUENCE_LINKS: the previously-hardcoded PPI->CPI link is gone; PPI feeds no CPI event ===")
    for target in ("CPI m/m", "CPI y/y", "Core CPI m/m", "Core CPI y/y"):
        linked = dict(EVENT_INFLUENCE_LINKS.get(target, []))
        assert "PPI m/m" not in linked and "Core PPI m/m" not in linked
    print("PASS\n")


# Causation Matrix fidelity check, 2026-11-04: pairs the workbook contradicts or does not verify.
DELETED_LINKS = [
    ("Non-Farm Employment Change", "JOLTS Job Openings"),
    ("Non-Farm Employment Change", "Challenger Job Cuts y/y"),
    ("CPI m/m", "PPI m/m"),
    ("CPI m/m", "Core PPI m/m"),
    ("CPI m/m", "ISM Manufacturing Prices"),
    ("CPI m/m", "ISM Services Prices"),
    ("CPI y/y", "PPI m/m"),
    ("CPI y/y", "Core PPI m/m"),
    ("Core CPI m/m", "Core PPI m/m"),
    ("Core CPI y/y", "Core PPI m/m"),
    ("Core PCE Price Index m/m", "CPI m/m"),
    ("Core PCE Price Index m/m", "Core CPI m/m"),
    ("Retail Sales m/m", "CB Consumer Confidence"),
    ("Retail Sales m/m", "Prelim UoM Consumer Sentiment"),
]

# Targets left with no links lose their key instead of keeping an empty list.
REMOVED_TARGETS = ["CPI y/y", "Core CPI m/m", "Core CPI y/y", "Core PCE Price Index m/m", "Retail Sales m/m"]

SURVIVING_LINKS = {
    "Non-Farm Employment Change": {"Unemployment Claims": 0.40},
    "Unemployment Rate": {"Unemployment Claims": 0.40},
    "CPI m/m": {"Import Prices m/m": 0.40},
    "FOMC Statement": {"Non-Farm Employment Change": 0.50, "CPI m/m": 0.60, "Core PCE Price Index m/m": 0.65},
    "Federal Funds Rate": {"Non-Farm Employment Change": 0.50, "CPI m/m": 0.60, "Core PCE Price Index m/m": 0.65},
    "Prelim GDP q/q": {
        "Retail Sales m/m": 0.35, "Durable Goods Orders m/m": 0.30, "Trade Balance": 0.20,
        "ISM Manufacturing PMI": 0.30, "ISM Services PMI": 0.30,
    },
    "ISM Manufacturing PMI": {"S&P Global Manufacturing PMI Flash": 0.45},
    "ISM Services PMI": {"S&P Global Services PMI Flash": 0.45},
    "Industrial Production m/m": {"ISM Manufacturing PMI": 0.40},
    "Durable Goods Orders m/m": {"ISM Manufacturing PMI": 0.30},
    "Housing Starts": {"Building Permits": 0.55},
    "Existing Home Sales": {"Building Permits": 0.30, "Housing Starts": 0.30},
    "New Home Sales": {"Building Permits": 0.30, "Housing Starts": 0.30},
}


def test_link_fidelity_deleted_pairs_are_gone_and_surviving_links_stay():
    print("=== EVENT_INFLUENCE_LINKS: no deleted pair remains, emptied targets lost their key, every surviving link keeps its weight ===")
    for target, precursor in DELETED_LINKS:
        assert precursor not in dict(EVENT_INFLUENCE_LINKS.get(target, [])), f"{precursor} -> {target}"
    for target in REMOVED_TARGETS:
        assert target not in EVENT_INFLUENCE_LINKS, target
    for target, expected in SURVIVING_LINKS.items():
        assert dict(EVENT_INFLUENCE_LINKS[target]) == expected, target
    print("PASS\n")


if __name__ == "__main__":
    test_event_registry_every_entry_has_impact_and_interval()
    test_event_registry_covers_every_event_surprise_direction_title()
    test_rejected_adp_is_no_precursor_and_claims_lead_nfp()
    test_get_approximate_next_occurrence_unregistered_title_returns_none()
    test_get_approximate_next_occurrence_no_sources_returns_none()
    test_get_approximate_next_occurrence_tier3_cadence_math()
    test_get_approximate_next_occurrence_tier3_fractional_interval()
    test_get_approximate_next_occurrence_macro_calendar_beats_cadence_math()
    test_get_approximate_next_occurrence_ff_snapshot_beats_everything()
    test_event_influence_links_every_title_is_registered()
    test_event_influence_links_drops_the_old_hardcoded_ppi_link()
    test_link_fidelity_deleted_pairs_are_gone_and_surviving_links_stay()
