"""Freshness helpers (B2 K7): age floor/clamp, band edges, the SAST line."""
from __future__ import annotations

import datetime as dt

import pytest

from alerting.freshness import age_minutes, freshness_band, freshness_line

UTC = dt.timezone.utc


@pytest.mark.parametrize("age,band", [
    (0, "Fresh"), (5, "Fresh"), (6, "Delayed"), (15, "Delayed"),
    (16, "Stale"), (60, "Stale"), (61, "Very stale"), (465, "Very stale"),
])
def test_bands_at_their_edges(age, band):
    assert freshness_band(age) == band


def test_band_of_unknown_age_is_none():
    assert freshness_band(None) is None


def test_age_is_floored_clamped_and_naive_means_utc():
    published = dt.datetime(2026, 10, 21, 12, 40, 0, tzinfo=UTC)
    assert age_minutes(published, dt.datetime(2026, 10, 21, 12, 45, 59, tzinfo=UTC)) == 5
    assert freshness_band(5) == "Fresh"
    # Feed clock ahead of ours: never a negative age.
    assert age_minutes(dt.datetime(2026, 10, 21, 12, 50, tzinfo=UTC),
                       dt.datetime(2026, 10, 21, 12, 45, tzinfo=UTC)) == 0
    naive = dt.datetime(2026, 10, 21, 12, 40)
    assert age_minutes(naive, dt.datetime(2026, 10, 21, 12, 45, tzinfo=UTC)) == \
        age_minutes(published, dt.datetime(2026, 10, 21, 12, 45, tzinfo=UTC))
    assert age_minutes(None, dt.datetime(2026, 10, 21, 12, 45, tzinfo=UTC)) is None


def test_line_shows_published_time_in_sast_minutes_and_band():
    line = freshness_line(dt.datetime(2026, 10, 21, 12, 40, tzinfo=UTC),
                          dt.datetime(2026, 10, 21, 12, 42, tzinfo=UTC))
    assert line == "Published 14:40 SAST · +2 min · Fresh"


def test_line_adds_the_date_when_the_story_is_from_an_earlier_day():
    line = freshness_line(dt.datetime(2026, 10, 20, 12, 42, tzinfo=UTC),
                          dt.datetime(2026, 10, 21, 12, 27, tzinfo=UTC))
    assert line == "Published 20 Oct 14:42 SAST · +1425 min · Very stale"


def test_line_date_is_judged_in_sast_not_utc():
    # 22:30Z on the 20th is 00:30 SAST on the 21st: same SAST day as detection, so no date.
    line = freshness_line(dt.datetime(2026, 10, 20, 22, 30, tzinfo=UTC),
                          dt.datetime(2026, 10, 20, 22, 40, tzinfo=UTC))
    assert line == "Published 00:30 SAST · +10 min · Delayed"


def test_no_first_published_means_no_line():
    assert freshness_line(None, dt.datetime(2026, 10, 21, 12, 42, tzinfo=UTC)) is None
