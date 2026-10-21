# alerting/source_backoff.py
"""
Pure backoff policy for the shock poller's RSS feeds (B4 O5). State lives in
alerting/store.py's source_health table; this module only decides.

A feed that keeps failing is skipped (not dropped): after 3 consecutive
failures it waits 10 minutes, doubling per further failure up to 6 hours.
A feed still failing after 2 weeks is only reported as a drop candidate --
the owner decides, nothing is removed automatically.
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

from alerting.store import SourceHealth

FEED_BACKOFF_AFTER_FAILURES = 3
FEED_BACKOFF_BASE = dt.timedelta(minutes=10)
FEED_BACKOFF_MAX = dt.timedelta(hours=6)
FEED_DROP_REVIEW_AFTER = dt.timedelta(days=14)


def backoff_delay(consecutive_failures: int) -> Optional[dt.timedelta]:
    """How long to skip the feed after this many consecutive failures; None while still polling every cycle."""
    if consecutive_failures < FEED_BACKOFF_AFTER_FAILURES:
        return None
    exponent = min(consecutive_failures - FEED_BACKOFF_AFTER_FAILURES, 20)  # cap the shift; MAX bites long before
    return min(FEED_BACKOFF_BASE * 2 ** exponent, FEED_BACKOFF_MAX)


def in_backoff(health: Optional[SourceHealth], now: dt.datetime) -> bool:
    return health is not None and health.backoff_until_utc is not None and now < health.backoff_until_utc


def is_drop_candidate(health: Optional[SourceHealth], now: dt.datetime) -> bool:
    """Failing continuously for 14+ days -- to be reported, never dropped automatically."""
    return (
        health is not None
        and health.failing_since_utc is not None
        and now - health.failing_since_utc >= FEED_DROP_REVIEW_AFTER
    )
