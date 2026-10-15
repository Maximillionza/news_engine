"""
Tests for data_layer/brent_feed.py (FRED DCOILBRENTEU). No live network: the HTTP getter and the clock are
injected. Brent is information only on the Stats tab, so every failure path must return None, never raise.
"""
import datetime as dt
from unittest.mock import MagicMock

import pytest

from data_layer import brent_feed as bf


def _resp(observations, ok=True):
    resp = MagicMock()
    resp.json.return_value = {"observations": observations}
    if ok:
        resp.raise_for_status.return_value = None
    else:
        resp.raise_for_status.side_effect = RuntimeError("HTTP 500")
    return resp


def _obs(day, value):
    return {"date": day, "value": value}


class Clock:
    def __init__(self, start=1000.0):
        self.now = start

    def __call__(self):
        return self.now


@pytest.fixture(autouse=True)
def fresh_cache():
    bf.clear_cache()
    yield
    bf.clear_cache()


# --- parsing ----------------------------------------------------------------------------------

def test_parse_skips_fred_missing_markers_and_sorts_ascending():
    rows = [_obs("2026-10-13", "91.5"), _obs("2026-10-12", "."), _obs("2026-10-09", "90.25"), _obs("2026-10-10", ".")]
    assert bf.parse_observations(rows) == [(dt.date(2026, 10, 9), 90.25), (dt.date(2026, 10, 13), 91.5)]


@pytest.mark.parametrize("bad", [
    {"date": "2026-10-13", "value": None}, {"date": "2026-10-13"}, {"date": "not-a-date", "value": "9"},
    {"date": "2026-10-13", "value": "abc"}, {"date": "2026-10-13", "value": "nan"},
    {"date": "2026-10-13", "value": "inf"}, {"date": "2026-10-13", "value": "-5"}, {"date": "2026-10-13", "value": "0"},
    "not a dict", None,
])
def test_parse_drops_unusable_observations_without_raising(bad):
    good = _obs("2026-10-09", "90.0")
    assert bf.parse_observations([bad, good]) == [(dt.date(2026, 10, 9), 90.0)]


def test_parse_of_a_non_list_is_empty():
    assert bf.parse_observations(None) == []
    assert bf.parse_observations("oops") == []


# --- brent_on_or_before: no lookahead ---------------------------------------------------------

SERIES = [(dt.date(2026, 10, 8), 88.0), (dt.date(2026, 10, 9), 89.0), (dt.date(2026, 10, 13), 91.0)]


def test_on_or_before_returns_the_exact_day_when_present():
    assert bf.brent_on_or_before(SERIES, dt.date(2026, 10, 9)) == (dt.date(2026, 10, 9), 89.0)


def test_on_or_before_falls_back_to_the_latest_earlier_day_never_a_later_one():
    # 10-11 and 10-12 are a weekend: the 10-09 value is the latest on or before, NOT the 10-13 one.
    assert bf.brent_on_or_before(SERIES, dt.date(2026, 10, 12)) == (dt.date(2026, 10, 9), 89.0)


def test_on_or_before_is_none_when_everything_is_later():
    assert bf.brent_on_or_before(SERIES, dt.date(2026, 10, 7)) is None


def test_on_or_before_handles_empty_and_none_and_unsorted_input():
    assert bf.brent_on_or_before([], dt.date(2026, 10, 9)) is None
    assert bf.brent_on_or_before(None, dt.date(2026, 10, 9)) is None
    assert bf.brent_on_or_before(list(reversed(SERIES)), dt.date(2026, 10, 12)) == (dt.date(2026, 10, 9), 89.0)


def test_on_or_before_accepts_a_datetime_by_its_date():
    when = dt.datetime(2026, 10, 9, 23, 59, tzinfo=dt.timezone.utc)
    assert bf.brent_on_or_before(SERIES, when) == (dt.date(2026, 10, 9), 89.0)


# --- get_brent_series: fetch, cache, fail-open ------------------------------------------------

def test_fetch_uses_the_fred_key_series_and_returns_parsed_ascending_series():
    get = MagicMock(return_value=_resp([_obs("2026-10-13", "91.0"), _obs("2026-10-12", "."), _obs("2026-10-09", "89.0")]))
    series = bf.get_brent_series(api_key="test-key", http_get=get, clock=Clock())
    assert series == [(dt.date(2026, 10, 9), 89.0), (dt.date(2026, 10, 13), 91.0)]
    url = get.call_args.args[0]
    params = get.call_args.kwargs["params"]
    assert url == "https://api.stlouisfed.org/fred/series/observations"
    assert params["series_id"] == "DCOILBRENTEU" and params["api_key"] == "test-key" and params["file_type"] == "json"
    assert get.call_args.kwargs["timeout"] <= 15


def test_default_key_comes_from_settings_never_hard_coded(monkeypatch):
    monkeypatch.setattr(bf, "FRED_API_KEY", "")
    get = MagicMock()
    assert bf.get_brent_series(http_get=get, clock=Clock()) is None
    get.assert_not_called()
    monkeypatch.setattr(bf, "FRED_API_KEY", "from-settings")
    get = MagicMock(return_value=_resp([_obs("2026-10-09", "89.0")]))
    assert bf.get_brent_series(http_get=get, clock=Clock()) == [(dt.date(2026, 10, 9), 89.0)]
    assert get.call_args.kwargs["params"]["api_key"] == "from-settings"


def test_missing_key_is_none_without_a_request():
    get = MagicMock()
    assert bf.get_brent_series(api_key="", http_get=get, clock=Clock()) is None
    get.assert_not_called()


def test_http_error_is_none_not_a_raise():
    get = MagicMock(return_value=_resp([], ok=False))
    assert bf.get_brent_series(api_key="k", http_get=get, clock=Clock()) is None


def test_network_exception_is_none_not_a_raise():
    get = MagicMock(side_effect=ConnectionError("down"))
    assert bf.get_brent_series(api_key="k", http_get=get, clock=Clock()) is None


def test_bad_json_is_none_not_a_raise():
    bad = MagicMock()
    bad.raise_for_status.return_value = None
    bad.json.side_effect = ValueError("not json")
    assert bf.get_brent_series(api_key="k", http_get=MagicMock(return_value=bad), clock=Clock()) is None


@pytest.mark.parametrize("observations", [[], [_obs("2026-10-09", ".")]])
def test_no_usable_observations_is_none_never_an_invented_value(observations):
    assert bf.get_brent_series(api_key="k", http_get=MagicMock(return_value=_resp(observations)), clock=Clock()) is None


def test_cache_serves_a_second_call_inside_the_ttl_without_a_request():
    clock = Clock()
    get = MagicMock(return_value=_resp([_obs("2026-10-09", "89.0")]))
    first = bf.get_brent_series(api_key="k", http_get=get, clock=clock)
    clock.now += bf.CACHE_TTL_SECONDS - 1
    second = bf.get_brent_series(api_key="k", http_get=get, clock=clock)
    assert first == second and get.call_count == 1


def test_cache_expires_after_six_hours():
    assert bf.CACHE_TTL_SECONDS == 6 * 60 * 60
    clock = Clock()
    get = MagicMock(side_effect=[_resp([_obs("2026-10-09", "89.0")]), _resp([_obs("2026-10-09", "89.0"), _obs("2026-10-13", "91.0")])])
    bf.get_brent_series(api_key="k", http_get=get, clock=clock)
    clock.now += bf.CACHE_TTL_SECONDS
    refreshed = bf.get_brent_series(api_key="k", http_get=get, clock=clock)
    assert get.call_count == 2 and refreshed[-1] == (dt.date(2026, 10, 13), 91.0)


def test_failed_refresh_keeps_serving_the_stale_series_rather_than_dropping_the_line():
    clock = Clock()
    get = MagicMock(side_effect=[_resp([_obs("2026-10-09", "89.0")]), ConnectionError("down")])
    bf.get_brent_series(api_key="k", http_get=get, clock=clock)
    clock.now += bf.CACHE_TTL_SECONDS + 1
    assert bf.get_brent_series(api_key="k", http_get=get, clock=clock) == [(dt.date(2026, 10, 9), 89.0)]


def test_a_failure_is_remembered_briefly_so_a_dead_feed_is_not_hammered():
    clock = Clock()
    get = MagicMock(side_effect=ConnectionError("down"))
    assert bf.get_brent_series(api_key="k", http_get=get, clock=clock) is None
    clock.now += 10
    assert bf.get_brent_series(api_key="k", http_get=get, clock=clock) is None
    assert get.call_count == 1
    clock.now += bf.FAILURE_RETRY_SECONDS
    bf.get_brent_series(api_key="k", http_get=get, clock=clock)
    assert get.call_count == 2


def test_cached_result_is_not_mutable_by_callers():
    clock = Clock()
    get = MagicMock(return_value=_resp([_obs("2026-10-09", "89.0")]))
    series = bf.get_brent_series(api_key="k", http_get=get, clock=clock)
    series.clear()
    assert bf.get_brent_series(api_key="k", http_get=get, clock=clock) == [(dt.date(2026, 10, 9), 89.0)]
