# tests/test_alerting_source_backoff.py
from __future__ import annotations

import datetime as dt

from alerting import source_backoff as sb
from alerting.store import SourceHealth

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 10, 21, 8, 0, tzinfo=UTC)


def _health(**kw) -> SourceHealth:
    base = dict(
        source="feed_a", consecutive_failures=0, failing_since_utc=None, backoff_until_utc=None,
        last_success_utc=None, last_failure_utc=None, last_error=None,
    )
    base.update(kw)
    return SourceHealth(**base)


def test_backoff_delay_doubles_from_10_minutes_and_caps_at_6_hours():
    assert sb.backoff_delay(1) is None
    assert sb.backoff_delay(2) is None
    assert sb.backoff_delay(3) == dt.timedelta(minutes=10)
    assert sb.backoff_delay(4) == dt.timedelta(minutes=20)
    assert sb.backoff_delay(5) == dt.timedelta(minutes=40)
    assert sb.backoff_delay(8) == dt.timedelta(minutes=320)
    assert sb.backoff_delay(9) == dt.timedelta(hours=6)
    assert sb.backoff_delay(20) == dt.timedelta(hours=6)


def test_in_backoff_only_before_the_stored_instant():
    assert not sb.in_backoff(None, NOW)
    assert not sb.in_backoff(_health(), NOW)
    h = _health(consecutive_failures=3, backoff_until_utc=NOW + dt.timedelta(minutes=1))
    assert sb.in_backoff(h, NOW)
    assert not sb.in_backoff(h, NOW + dt.timedelta(minutes=1))


def test_drop_candidate_after_14_days_of_failing():
    assert not sb.is_drop_candidate(_health(failing_since_utc=NOW - dt.timedelta(days=13, hours=23)), NOW)
    assert sb.is_drop_candidate(_health(failing_since_utc=NOW - dt.timedelta(days=14)), NOW)
    assert not sb.is_drop_candidate(None, NOW)
    assert not sb.is_drop_candidate(_health(), NOW)
