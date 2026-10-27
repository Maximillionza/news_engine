"""
Tests for scoring/surprise_scale.py — B8 (2026-10-27) standardized surprise:
sigma of an indicator's own PRIOR USD surprises, a 6-prior minimum, a
one-rounding-step floor and a fail-open attach. Temp DBs only, no network.
"""
import sys
import os
import datetime as dt
import statistics
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer.calendar_feed import EconomicEvent
import scoring.surprise_scale as surprise_scale
from scoring.surprise_scale import prior_surprises, sigma_for_event, surprise_sigma, with_surprise_sigma
import webapp.store as store

UTC = dt.timezone.utc
EVENT_TIME = dt.datetime(2026, 10, 14, 12, 30, tzinfo=UTC)
# forecast 0.3% against these actuals -> surprises [0.1, -0.1, 0.0, 0.2, -0.1, 0.1]
CPI_PRIOR_ACTUALS = ["0.4%", "0.2%", "0.3%", "0.5%", "0.2%", "0.4%"]
CLAIMS_PRIORS = [("225K", "215K"), ("220K", "215K"), ("202K", "209K"), ("210K", "206K"), ("208K", "203K"), ("205K", "206K")]


@pytest.fixture
def conn(tmp_path: Path):
    c = store.get_connection(tmp_path / "d.db")
    yield c
    c.close()


def _row(conn, title: str, when: dt.datetime, forecast, actual, country="USD") -> None:
    store.insert_event_history_if_absent(
        conn, title, when, forecast, "0.1%", actual, None, "live", "High", country, when,
    )


def _monthly(k: int) -> dt.datetime:
    """k months before EVENT_TIME (k = 1 -> 2026-09-14)."""
    return dt.datetime(2026, 10 - k, 14, 12, 30, tzinfo=UTC)


def _cpi_priors(conn, n: int = 6) -> None:
    for k, actual in enumerate(CPI_PRIOR_ACTUALS[:n], start=1):
        _row(conn, "CPI m/m", _monthly(k), "0.3%", actual)


def _cpi_event(actual: str = "0.5%") -> EconomicEvent:
    return EconomicEvent("CPI m/m", "USD", "High", EVENT_TIME, forecast="0.3%", actual=actual)


def test_sigma_uses_only_strictly_prior_rows(conn):
    _cpi_priors(conn)
    assert sigma_for_event(conn, _cpi_event()) == pytest.approx(0.121106, abs=1e-6)
    # The event's own row (at exactly the event time) and three LATER rows with huge misses.
    _row(conn, "CPI m/m", EVENT_TIME, "0.3%", "0.5%")
    for days in (1, 30, 60):
        _row(conn, "CPI m/m", EVENT_TIME + dt.timedelta(days=days), "0.3%", "2.3%")
    # The same instant written with another offset is still "at the event time", not before it.
    _row(conn, "CPI m/m", EVENT_TIME.astimezone(dt.timezone(dt.timedelta(hours=2))), "0.3%", "2.3%")
    assert len(prior_surprises(conn, "CPI m/m", EVENT_TIME)) == 6
    assert sigma_for_event(conn, _cpi_event()) == pytest.approx(0.121106, abs=1e-6)


def test_fallback_below_six_prior_surprises(conn):
    _cpi_priors(conn, n=5)
    assert sigma_for_event(conn, _cpi_event()) is None
    event = with_surprise_sigma(conn, _cpi_event())
    assert event.surprise_sigma is None
    assert event.usd_surprise_score() == pytest.approx(0.964028, abs=1e-6)   # today's method: tanh((0.2/0.3)*3)

    _row(conn, "CPI m/m", _monthly(6), "0.3%", CPI_PRIOR_ACTUALS[5])
    event = with_surprise_sigma(conn, _cpi_event())
    assert event.surprise_sigma == pytest.approx(0.121106, abs=1e-6)
    assert 0.2 / event.surprise_sigma == pytest.approx(1.651446, abs=1e-6)
    assert event.usd_surprise_score() == pytest.approx(0.678173, abs=1e-6)


def test_claims_become_comparable(conn):
    for k, (forecast, actual) in enumerate(CLAIMS_PRIORS, start=1):
        _row(conn, "Unemployment Claims", EVENT_TIME - dt.timedelta(days=7 * k), forecast, actual)
    event = EconomicEvent("Unemployment Claims", "USD", "Medium", EVENT_TIME, forecast="225K", actual="219K")
    assert event.usd_surprise_score() == pytest.approx(0.079830, abs=1e-6)   # before B8
    assert sigma_for_event(conn, event) == pytest.approx(5887.84, abs=0.01)
    assert with_surprise_sigma(conn, event).usd_surprise_score() == pytest.approx(0.469575, abs=1e-6)


def test_sigma_floor_is_one_rounding_step(conn):
    assert surprise_sigma([0.0, 0.0, 0.0, 0.0, 0.0, 0.1], "0.3%") == pytest.approx(0.1)
    for k, actual in enumerate(["0.3%"] * 5 + ["0.4%"], start=1):
        _row(conn, "CPI m/m", _monthly(k), "0.3%", actual)
    assert statistics.stdev(prior_surprises(conn, "CPI m/m", EVENT_TIME)) == pytest.approx(0.0408, abs=1e-4)
    assert sigma_for_event(conn, _cpi_event()) == pytest.approx(0.1)
    # All-zero misses with no parseable forecast to floor on: no usable sigma.
    assert surprise_sigma([0.0] * 6, None) is None


def test_sigma_ignores_non_usd_and_null_country_rows(conn):
    _cpi_priors(conn)
    for k in range(1, 7):
        _row(conn, "CPI m/m", _monthly(k) + dt.timedelta(days=1), "0.3%", "1.3%", country="GBP")
        _row(conn, "CPI m/m", _monthly(k) + dt.timedelta(days=2), "0.3%", "1.3%", country=None)
    assert sigma_for_event(conn, _cpi_event()) == pytest.approx(0.121106, abs=1e-6)
    # A non-USD event is never given a sigma, whatever its history.
    gbp = EconomicEvent("CPI m/m", "GBP", "High", EVENT_TIME, forecast="0.3%", actual="0.5%")
    assert sigma_for_event(conn, gbp) is None


def test_unparseable_and_forecast_null_rows_skipped(conn):
    _cpi_priors(conn, n=5)
    _row(conn, "CPI m/m", _monthly(6), None, "0.6%")                       # seeded-style FRED row
    _row(conn, "CPI m/m", _monthly(7), "0.3%", "N/A")                      # unparseable actual
    assert len(prior_surprises(conn, "CPI m/m", EVENT_TIME)) == 5
    assert sigma_for_event(conn, _cpi_event()) is None


def test_history_capped_at_24(conn):
    recent = []
    for k in range(1, 31):
        if k <= 24:
            actual = "0.4%" if k % 2 else "0.2%"
        else:
            actual = "5.3%"                                                 # older misses that must not count
        _row(conn, "CPI m/m", EVENT_TIME - dt.timedelta(days=7 * k), "0.3%", actual)
    surprises = prior_surprises(conn, "CPI m/m", EVENT_TIME)
    assert len(surprises) == 24
    assert max(abs(s) for s in surprises) < 1.0
    expected = statistics.stdev([0.4 - 0.3, 0.2 - 0.3] * 12)
    assert sigma_for_event(conn, _cpi_event()) == pytest.approx(expected, abs=1e-9)


def test_untracked_title_has_no_sigma(conn):
    for k in range(1, 8):
        _row(conn, "JOLTS Job Openings", _monthly(k), "7.20M", "7.40M")
    jolts = EconomicEvent("JOLTS Job Openings", "USD", "Medium", EVENT_TIME, forecast="7.20M", actual="7.40M")
    assert sigma_for_event(conn, jolts) is None


def test_with_surprise_sigma_fails_open(tmp_path):
    c = store.get_connection(tmp_path / "d.db")
    _cpi_priors(c)
    c.close()
    event = _cpi_event()
    result = with_surprise_sigma(c, event)
    assert result is event
    assert result.surprise_sigma is None
    assert result.usd_surprise_score() == pytest.approx(0.964028, abs=1e-6)


def test_constants_match_plan():
    assert surprise_scale.MIN_PRIOR_SURPRISES_FOR_SIGMA == 6
    assert surprise_scale.SURPRISE_SIGMA_MAX_HISTORY == 24


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        c = store.get_connection(Path(tmp) / "d.db")
        _cpi_priors(c)
        print("CPI m/m sigma:", sigma_for_event(c, _cpi_event()))
        print("score:", with_surprise_sigma(c, _cpi_event()).usd_surprise_score())
        c.close()
