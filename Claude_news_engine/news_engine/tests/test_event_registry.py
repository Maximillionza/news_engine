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


def test_event_influence_links_absorbs_the_old_hardcoded_adp_ppi_links():
    print("=== EVENT_INFLUENCE_LINKS: the two previously-hardcoded links (ADP->NFP, PPI->CPI) are present ===")
    nfp_precursors = dict(EVENT_INFLUENCE_LINKS.get("Non-Farm Employment Change", []))
    assert "ADP Nonfarm Employment Change" in nfp_precursors
    cpi_precursors = dict(EVENT_INFLUENCE_LINKS.get("CPI m/m", []))
    assert "PPI m/m" in cpi_precursors
    print("PASS\n")


if __name__ == "__main__":
    test_event_registry_every_entry_has_impact_and_interval()
    test_event_registry_covers_every_event_surprise_direction_title()
    test_get_approximate_next_occurrence_unregistered_title_returns_none()
    test_get_approximate_next_occurrence_no_sources_returns_none()
    test_get_approximate_next_occurrence_tier3_cadence_math()
    test_get_approximate_next_occurrence_tier3_fractional_interval()
    test_get_approximate_next_occurrence_macro_calendar_beats_cadence_math()
    test_get_approximate_next_occurrence_ff_snapshot_beats_everything()
    test_event_influence_links_every_title_is_registered()
    test_event_influence_links_absorbs_the_old_hardcoded_adp_ppi_links()
