"""
Tests for data_layer/tier1_calendar.py (FIX Task 6): a Tier 1 release that Forex Factory has not listed yet is read
from macro_calendar (FRED's schedule) at the official New York release time, and the capture marks it unconfirmed.
Databases are in-memory; no network.
"""
import datetime as dt

from data_layer import tier1_calendar as cal
from data_layer.tier1_events import TIER1_FORMULA, TIER1_JUDGMENT, tier1_titles
from scripts import capture_nowcast_from_cleveland as cap
from webapp import store as ws

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 11, 9, 5, 0, tzinfo=UTC)
WINDOW = dt.timedelta(hours=48)


def _macro(dash, title, date, estimate="12:30", confirmed=0):
    """A macro_calendar row the way scripts/refresh_macro_calendar.py leaves it (estimate = history-derived UTC time)."""
    ws.upsert_macro_calendar_event(dash, title, date, f"{date}T{estimate}:00+00:00", "history_derived", NOW)
    if confirmed:
        dash.execute("UPDATE macro_calendar SET confirmed = 1 WHERE event_title = ? AND event_date = ?", (title, date))
        dash.commit()


def _event(dash, title, when, forecast="0.3%"):
    dash.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, surprise_direction, "
        "recorded_at_utc, updated_at_utc, source, impact, country) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (title, when.isoformat(), forecast, None, None, None, when.isoformat(), when.isoformat(), "t", "High", "USD"))
    dash.commit()


def test_release_time_is_the_official_new_york_time_in_utc():
    assert cal.release_utc_from_et("CPI m/m", dt.date(2026, 11, 10)) == dt.datetime(2026, 11, 10, 13, 30, tzinfo=UTC)
    assert cal.release_utc_from_et("CPI m/m", dt.date(2026, 10, 14)) == dt.datetime(2026, 10, 14, 12, 30, tzinfo=UTC)
    assert cal.release_utc_from_et("Not A Registered Title", dt.date(2026, 11, 10)) is None


def test_due_releases_falls_back_to_macro_calendar_for_cpi():
    dash = ws.get_connection(":memory:")
    _macro(dash, "CPI m/m", "2026-11-10")                 # the stored estimate is 12:30, the summer-time guess
    due = cap._due_releases(dash, NOW, WINDOW)
    assert [(d.title, d.release.isoformat(), d.forecast, d.unconfirmed) for d in due] == [
        ("CPI m/m", "2026-11-10T13:30:00+00:00", None, True)]


def test_before_dst_end_stays_1230():
    dash = ws.get_connection(":memory:")
    _macro(dash, "CPI m/m", "2026-10-14")
    now = dt.datetime(2026, 10, 13, 5, 0, tzinfo=UTC)
    due = cap._due_releases(dash, now, WINDOW)
    assert [d.release.isoformat() for d in due] == ["2026-10-14T12:30:00+00:00"]


def test_event_history_row_wins_over_macro_calendar():
    dash = ws.get_connection(":memory:")
    _macro(dash, "CPI m/m", "2026-11-10")
    _event(dash, "CPI m/m", dt.datetime(2026, 11, 10, 13, 30, tzinfo=UTC))
    due = cap._due_releases(dash, NOW, WINDOW)
    assert [(d.title, d.forecast, d.unconfirmed) for d in due] == [("CPI m/m", "0.3%", False)]
    # An event_history row a day off (FF moved the date) still wins: no second, unconfirmed copy.
    other = ws.get_connection(":memory:")
    _macro(other, "CPI m/m", "2026-11-10")
    _event(other, "CPI m/m", dt.datetime(2026, 11, 11, 13, 30, tzinfo=UTC))
    assert [d.unconfirmed for d in cap._due_releases(other, NOW, dt.timedelta(hours=72))] == [False]
    assert cal.unconfirmed_releases(other, ["CPI m/m"], NOW, NOW + WINDOW) == []


def test_prelim_gdp_phantom_dropped():
    dash = ws.get_connection(":memory:")
    _macro(dash, "Prelim GDP q/q", "2026-10-29")          # October is the advance estimate: not a Prelim GDP month
    _macro(dash, "Prelim GDP q/q", "2026-11-25")
    start = dt.datetime(2026, 10, 27, 5, 0, tzinfo=UTC)
    got = cal.unconfirmed_releases(dash, ["Prelim GDP q/q"], start, dt.datetime(2026, 12, 1, tzinfo=UTC))
    assert [(g.title, g.release_utc.isoformat()) for g in got] == [("Prelim GDP q/q", "2026-11-25T13:30:00+00:00")]
    assert cal.on_official_schedule("Prelim GDP q/q", dt.date(2026, 11, 25))
    assert not cal.on_official_schedule("Prelim GDP q/q", dt.date(2026, 10, 29))
    assert cal.on_official_schedule("CPI m/m", dt.date(2026, 10, 29))


def test_confirmed_macro_rows_ignored():
    dash = ws.get_connection(":memory:")
    _macro(dash, "CPI m/m", "2026-11-10", confirmed=1)
    assert cal.unconfirmed_releases(dash, ["CPI m/m"], NOW, NOW + WINDOW) == []


def test_window_and_title_filters():
    dash = ws.get_connection(":memory:")
    _macro(dash, "CPI m/m", "2026-11-10")                 # 13:30Z is 32.5 h out
    _macro(dash, "CPI m/m", "2026-11-13")                 # beyond 48 h
    _macro(dash, "Unemployment Rate", "2026-11-10")       # not a requested title
    got = cal.unconfirmed_releases(dash, ["CPI m/m"], NOW, NOW + WINDOW)
    assert [g.release_utc.isoformat() for g in got] == ["2026-11-10T13:30:00+00:00"]
    assert cal.unconfirmed_releases(dash, [], NOW, NOW + WINDOW) == []


def test_untimed_title_is_not_guessed():
    dash = ws.get_connection(":memory:")
    _macro(dash, "Some Unlisted Title", "2026-11-10")
    assert cal.unconfirmed_releases(dash, ["Some Unlisted Title"], NOW, NOW + WINDOW) == []
