"""
Forex Factory economic calendar fetcher.

Forex Factory doesn't publish an official developer API. The calendar widget
embedded on partner sites is backed by a public JSON feed hosted by
FairEconomy (the data provider behind FF's widget). This is the same feed
used by countless retail trading tools — no login/auth required, no ToS
violation, it's a public read-only data endpoint.

Feed: https://nfs.faireconomy.media/ff_calendar_thisweek.json — the only
period that actually exists. "lastweek"/"nextweek" variants were assumed
to exist here (comment predating this investigation) but were confirmed,
live and via research, to be nonexistent — a plain nginx 404, not an
auth/permission response, and no documentation anywhere (retail trading
tool forums, MQL5/MT4 EA discussions that all consume this same feed)
references them either. There is no way to fetch historical or future-week
calendar data from this feed at all — "thisweek" is genuinely all there is.
The only workaround for historical events (e.g. backtesting) is manual
reconstruction from real researched data — see
tests/run_historical_backtest.py for the established pattern.

Rate limit, per Forex Factory's own published guidance: max 2 downloads
per 5 minutes across ALL formats (json/xml/ics/csv) combined, and their
explicit recommendation is to fetch once a week and cache it, not poll on
an interval. This project got rate-limited (429) twice in the same
session before this was known — see webapp/scheduler.py's adaptive poll
interval and webapp/app.py's shared cache, both added specifically to
respect this.
"""
from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import requests

from config.settings import (
    EVENT_HISTORY_IN_LINE_TOLERANCE,
    EVENT_SURPRISE_DIRECTION,
    LOCAL_TZ,
    PRE_EVENT_WINDOW_HOURS,
    PRECURSOR_EVENTS,
    SURPRISE_SENSITIVITY,
    UTC_TZ,
)

FF_BASE_URL = "https://nfs.faireconomy.media/ff_calendar_{period}.json"

# Real, self-enforced cooldown between live fetch_calendar() calls, shared
# across EVERY caller and EVERY process (webapp/scheduler.py AND
# scoring/backtest_accumulator.py both call this function independently —
# scheduler.py's own comment claiming to be the "ONLY" live caller is
# stale). Backed by a file, not an in-memory timestamp, specifically
# because a process restart (which happens routinely during development)
# would otherwise reset an in-memory guard to zero and defeat the whole
# point — this project has been rate-limited (429) three separate times
# this session, the last time from repeated restarts within a single day
# each triggering two near-simultaneous fetches. FF's hard limit is 2
# downloads per 5 minutes across all formats combined, with an explicit
# recommendation to fetch once a week; 600s (10 minutes) is a conservative
# floor well under the hard limit while still keeping the dashboard
# reasonably fresh multiple times an hour.
MIN_FETCH_INTERVAL_SECONDS = 600
_LAST_FETCH_TIMESTAMP_FILE = Path(__file__).parent / ".last_ff_fetch_at"


class FetchCooldownError(Exception):
    """
    Raised instead of making a live request when the last fetch (from ANY
    caller/process) was too recent. Callers that already wrap fetch_calendar()
    in a broad `except Exception` (webapp/scheduler.py, scoring/backtest_accumulator.py)
    catch this the same way they catch a real network failure — fail open,
    keep existing data — but the log message here says WHY, distinguishing
    a self-imposed cooldown from an actual outage.
    """


def _seconds_since_last_fetch() -> Optional[float]:
    """None if no prior fetch has been recorded (fresh install / file never written)."""
    if not _LAST_FETCH_TIMESTAMP_FILE.exists():
        return None
    try:
        last = dt.datetime.fromisoformat(_LAST_FETCH_TIMESTAMP_FILE.read_text().strip())
    except (ValueError, OSError):
        return None  # corrupt/unreadable timestamp file — fail open to "no recent fetch known", not a crash
    return (dt.datetime.now(dt.timezone.utc) - last).total_seconds()


def _record_fetch_attempt(now: dt.datetime) -> None:
    """
    Records the attempt BEFORE the network call (not just on success) —
    a failed/errored request still counted against FF's rate limit on
    their end, so a caller that retries immediately after a failure must
    still respect the cooldown, not treat a failure as a free retry.
    """
    _LAST_FETCH_TIMESTAMP_FILE.write_text(now.isoformat())

# Impact levels FF uses in the feed
IMPACT_LEVELS = {"Low", "Medium", "High", "Holiday"}


@dataclass
class EconomicEvent:
    title: str
    country: str          # e.g. "USD"
    impact: str            # Low / Medium / High
    event_time_utc: dt.datetime
    forecast: Optional[str] = None
    previous: Optional[str] = None
    actual: Optional[str] = None
    raw: dict = field(default_factory=dict, repr=False)

    @property
    def event_time_local(self) -> dt.datetime:
        """Event time converted to SAST (Masood's local time)."""
        return self.event_time_utc.astimezone(LOCAL_TZ)

    @property
    def watch_from_local(self) -> dt.datetime:
        """When the pre-event probability window should start, in SAST."""
        return self.event_time_local - dt.timedelta(hours=PRE_EVENT_WINDOW_HOURS)

    def is_high_impact_usd(self) -> bool:
        return self.country == "USD" and self.impact == "High"

    def usd_surprise_score(self) -> Optional[float]:
        """
        Structured leading-indicator signal: how far this event's actual
        print came in vs. forecast, mapped to the same -1.0..+1.0
        USD-directional axis the lexicon sentiment scorer uses (see
        scoring/sentiment.py's module docstring for that convention).

        Returns None — never a fabricated 0.0 — if forecast/actual are
        missing/unparseable, or if this event's title isn't in
        EVENT_SURPRISE_DIRECTION. "No data" and "no surprise" are
        different things; only the latter should ever score as neutral.
        """
        direction = EVENT_SURPRISE_DIRECTION.get(self.title)
        if direction is None:
            return None

        forecast = _parse_numeric(self.forecast)
        actual = _parse_numeric(self.actual)
        if forecast is None or actual is None:
            return None

        if abs(forecast) > 1e-9:
            pct_diff = (actual - forecast) / abs(forecast)
        else:
            # Forecast of ~0 makes a percent-diff undefined/explosive
            # (e.g. forecast 0.0%, actual 0.1% would be an "infinite"
            # surprise) — fall back to the raw absolute diff instead.
            pct_diff = actual - forecast

        raw = math.tanh(pct_diff * SURPRISE_SENSITIVITY)
        return raw if direction == "higher_bullish" else -raw

    def __repr__(self) -> str:
        return (
            f"<EconomicEvent {self.title!r} [{self.country}/{self.impact}] "
            f"local={self.event_time_local.strftime('%Y-%m-%d %H:%M %Z')}>"
        )


def classify_surprise(event: "EconomicEvent") -> Optional[str]:
    """
    Literal actual-vs-forecast comparison for this event — "did the print
    come in above, below, or in line with what was forecast." Distinct
    from usd_surprise_score()'s USD-bullish/bearish-mapped magnitude:
    that answers "was this good or bad for the dollar," this answers "was
    the number itself higher or lower than expected," which for a
    'higher_bearish' indicator (e.g. Unemployment Rate) point in OPPOSITE
    directions from the bullish/bearish read.

    Reuses EVENT_SURPRISE_DIRECTION only as an is-this-title-tracked gate
    (same set of titles usd_surprise_score() recognizes) — not for its
    higher_bullish/higher_bearish values, which don't apply here.

    Returns 'higher', 'lower', 'in_line', or None — never a fabricated
    guess — when the title isn't tracked or forecast/actual don't parse.
    """
    if event.title not in EVENT_SURPRISE_DIRECTION:
        return None

    forecast = _parse_numeric(event.forecast)
    actual = _parse_numeric(event.actual)
    if forecast is None or actual is None:
        return None

    if abs(forecast) > 1e-9:
        pct_diff = (actual - forecast) / abs(forecast)
    else:
        pct_diff = actual - forecast

    if abs(pct_diff) <= EVENT_HISTORY_IN_LINE_TOLERANCE:
        return "in_line"
    return "higher" if pct_diff > 0 else "lower"


def _parse_numeric(value: Optional[str]) -> Optional[float]:
    """
    Parses FF's forecast/actual strings ('0.2%', '-23K', '158.4', '3.4%')
    into a float. Handles %, K/M/B suffixes and thousands commas. Returns
    None for missing/unparseable values — never guesses.
    """
    if not value:
        return None
    s = value.strip().replace(",", "")
    if not s:
        return None

    multiplier = 1.0
    if s.endswith("%"):
        s = s[:-1]
    elif s and s[-1] in "Kk":
        multiplier = 1_000.0
        s = s[:-1]
    elif s and s[-1] in "Mm":
        multiplier = 1_000_000.0
        s = s[:-1]
    elif s and s[-1] in "Bb":
        multiplier = 1_000_000_000.0
        s = s[:-1]

    try:
        return float(s) * multiplier
    except ValueError:
        return None


def _parse_event_datetime(raw_date: str) -> dt.datetime:
    """
    FF feed timestamps come as ISO 8601 strings, already UTC-offset aware
    (e.g. '2026-08-07T12:30:00-04:00' during EDT). We normalize to UTC.
    """
    parsed = dt.datetime.fromisoformat(raw_date)
    if parsed.tzinfo is None:
        # Fallback: assume US Eastern if no offset present (shouldn't happen with this feed)
        from config.settings import NY_TZ
        parsed = parsed.replace(tzinfo=NY_TZ)
    return parsed.astimezone(UTC_TZ)


def fetch_calendar(period: str = "thisweek", timeout: int = 15) -> list[EconomicEvent]:
    """
    Fetch the raw FF calendar feed. "thisweek" is the only period that
    exists — confirmed live and via research (see this module's
    docstring); "lastweek"/"nextweek" are rejected here explicitly rather
    than left to fail as a generic 404 from the network call, so the
    error tells you WHY instead of just that the request failed.
    """
    if period != "thisweek":
        raise ValueError(
            f"period {period!r} is not available — this feed only ever serves 'thisweek', "
            "confirmed live (plain 404, not an auth error) and via research; "
            "there is no historical/future-week endpoint to fetch from. "
            "See this module's docstring for the reconstruction workaround."
        )

    elapsed = _seconds_since_last_fetch()
    if elapsed is not None and elapsed < MIN_FETCH_INTERVAL_SECONDS:
        raise FetchCooldownError(
            f"skipping live fetch — last fetch (any caller/process) was {elapsed:.0f}s ago, "
            f"under the {MIN_FETCH_INTERVAL_SECONDS}s self-imposed cooldown. This is not a "
            "network failure — it's this project respecting FF's own stated rate limit "
            "(2 downloads/5min) across every process that calls fetch_calendar()."
        )

    now = dt.datetime.now(dt.timezone.utc)
    _record_fetch_attempt(now)  # before the network call — a failed request still counts against FF's limit

    url = FF_BASE_URL.format(period=period)
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "news-fundamental-engine/0.1"})
    resp.raise_for_status()
    raw_events = resp.json()

    events: list[EconomicEvent] = []
    for item in raw_events:
        try:
            event_time = _parse_event_datetime(item["date"])
        except (KeyError, ValueError):
            continue  # skip malformed entries rather than crash the whole fetch

        events.append(
            EconomicEvent(
                title=item.get("title", "").strip(),
                country=item.get("country", "").strip(),
                impact=item.get("impact", "").strip(),
                event_time_utc=event_time,
                forecast=item.get("forecast") or None,
                previous=item.get("previous") or None,
                actual=item.get("actual") or None,
                raw=item,
            )
        )
    return events


def filter_relevant_events(
    events: list[EconomicEvent],
    countries: tuple[str, ...] = ("USD",),
    min_impact: str = "High",
    extra_titles: frozenset[str] = frozenset(),
) -> list[EconomicEvent]:
    """
    Narrow the full calendar down to the events that actually matter for
    gold / US30 directional analysis — high-impact USD releases by default
    (NFP, CPI, FOMC, PCE, ISM, retail sales, etc.), plus any event whose
    exact title is in extra_titles regardless of its impact tier (a
    curated allowlist, e.g. config.settings.ACCUMULATOR_MEDIUM_ALLOWLIST —
    never a blanket lower threshold, which would dilute callers that rely
    on this function's default High-only behavior).
    """
    impact_rank = {"Low": 1, "Medium": 2, "High": 3}
    min_rank = impact_rank.get(min_impact, 3)

    return [
        e for e in events
        if e.country in countries and (impact_rank.get(e.impact, 0) >= min_rank or e.title in extra_titles)
    ]


def events_in_pre_window(events: list[EconomicEvent], now_utc: Optional[dt.datetime] = None) -> list[EconomicEvent]:
    """
    Of the given events, return those whose pre-event probability window
    (event_time - PRE_EVENT_WINDOW_HOURS) has already started but the event
    itself hasn't passed yet — i.e. events we should currently be tracking.
    """
    now_utc = now_utc or dt.datetime.now(UTC_TZ)
    active = []
    for e in events:
        window_start = e.event_time_utc - dt.timedelta(hours=PRE_EVENT_WINDOW_HOURS)
        if window_start <= now_utc <= e.event_time_utc:
            active.append(e)
    return active


def find_precursor_events(
    target: EconomicEvent,
    all_events: list[EconomicEvent],
) -> list[EconomicEvent]:
    """
    Of `all_events`, returns the already-released USD events that are
    known leading indicators for `target` (per config.settings'
    PRECURSOR_EVENTS) and fall inside target's own pre-event window — e.g.
    an ADP miss 2 days before NFP.

    Only returns events with a real `actual` value — a precursor that
    hasn't printed yet has nothing to contribute (and would otherwise
    silently be excluded downstream anyway, since usd_surprise_score()
    needs both forecast and actual).
    """
    precursor_titles = set(PRECURSOR_EVENTS.get(target.title, []))
    if not precursor_titles:
        return []

    window_start = target.event_time_utc - dt.timedelta(hours=PRE_EVENT_WINDOW_HOURS)
    return [
        e for e in all_events
        if e.title in precursor_titles
        and e.country == "USD"
        and e.actual
        and window_start <= e.event_time_utc < target.event_time_utc
    ]


if __name__ == "__main__":
    # Quick manual smoke test — requires network access to nfs.faireconomy.media
    all_events = fetch_calendar("thisweek")
    high_impact_usd = filter_relevant_events(all_events)
    print(f"Fetched {len(all_events)} total events, {len(high_impact_usd)} high-impact USD events this week.\n")
    for ev in high_impact_usd:
        print(ev)
        print(f"   watch from (SAST): {ev.watch_from_local.strftime('%Y-%m-%d %H:%M %Z')}")
