"""
Background accumulator for the article-based backtest log — periodically
checks the calendar for high-impact USD events, and for tracked
instruments, runs the REAL article-based scoring pipeline
(scoring/probability_engine.py, not the essence-only dashboard path) and
persists each prediction to scoring/backtest_store.py's log — a genuine,
growing record of real predictions made blind, before the event, to be
confirmed against real outcomes later via scripts/confirm_backtest_outcomes.py.

Also blends in structured precursor data: already-released leading
indicators (e.g. PPI before CPI, ADP before NFP — see config.settings'
EVENT_INFLUENCE_LINKS and scoring.probability_engine.get_precursor_events_for())
get passed into score_bundle() alongside article sentiment, read from the
dashboard's persisted event_history — unaffected by any high-impact-only
filter, since precursors are typically Medium impact. Not every event has
a configured precursor, and a precursor with nothing released yet in the
target's pre-event window contributes nothing — both are normal, not a bug.

Deliberately NOT wired into webapp/ — the dashboard is essence-only by
design (no article fetching at all); this accumulator is article-based
and a distinct concern, run as its own standalone process.

CHECKS every instrument for every active (pre-event-window) event on
EVERY cycle — no separate per-pair check budget. Cadence is governed
entirely by the accumulator's own outer loop
(compute_accumulator_interval_seconds, below — its OWN tiers, decoupled
from webapp.scheduler's, see that function for why): hourly baseline once
an event enters its pre-event window, tighter (15min) the day of the
event, tightest (5min) in the final hour. A rolling-24h check-count
budget (DAILY_CHECK_BUDGET_THRESHOLD) throttles the hourly/day-of-event
tiers back to a 3-hour floor if checking gets too frequent for Alpha
Vantage's real 25/day quota — the final-hour tier is always exempt.
Whether a check actually gets WRITTEN to scoring/backtest_store.py's log
is a completely separate decision, gated purely by _is_material_change()
— a direction flip (contradicts), or a same-direction move of at least
MATERIAL_CHANGE_THRESHOLD_PROBABILITY (a stronger indication). Supporting
articles that just reinforce the existing read are checked, scored, and
discarded without a write — "current sentiment is the truth until
articles are found to contradict or change it," per explicit product
decision.

**Revised 2026-08-11 (twice)**: first to check every cycle instead of
just twice total per pair — the original design meant a genuine news
shift building over most of a multi-day pre-event window was never
picked up (observed live: CPI predictions sat unchanged with an
identical scored_at_utc for a full 24 hours). Then to add the hourly/
day-of-event/budget-fallback tiering above, once "check every cycle"
alone proved too blunt a knob — the accumulator's own outer loop used to
just reuse webapp.scheduler's 12h/1h/5min tiers, which doesn't match
"hourly baseline, tighter the day of the event, protected from
exhausting the article-fetch budget" on its own.
"""
from __future__ import annotations

import datetime as dt
import threading
import time
from pathlib import Path
from typing import Optional

from config.settings import (
    KALSHI_DATE_TICKETED_SERIES_BY_EVENT_TITLE, KALSHI_RATE_DECISION_SERIES,
    KALSHI_SERIES_BY_EVENT_TITLE,
    MIN_OCCURRENCES_FOR_TREND_PRIOR, POST_RELEASE_GRACE_MINUTES, PRE_EVENT_WINDOW_HOURS,
    EVENT_SURPRISE_DIRECTION, ACCUMULATOR_MEDIUM_ALLOWLIST,
    THIN_SAMPLE_SIGNAL_THRESHOLD,
)
from data_layer.calendar_feed import (
    EconomicEvent, fetch_calendar, filter_relevant_events, events_in_pre_window,
    _parse_numeric,
)
from data_layer.event_context import build_event_news_bundle
from data_layer.rss_sources import build_all_preview_sources
from data_layer.kalshi_feed import KalshiRead, get_market_read, get_market_read_by_date
from data_layer.macro_backdrop import get_macro_backdrop_read
from data_layer.cot_positioning import get_cot_positioning_read
from scoring.probability_engine import score_bundle, get_precursor_events_for
from scoring.print_direction import score_print_direction
from scoring.backtest_store import (
    get_connection, record_prediction, get_latest_prediction, record_check, count_recent_checks,
    record_print_prediction_if_changed, record_kalshi_read_if_changed,
)
from webapp.store import get_connection as get_dashboard_connection, get_event_history, DB_PATH as DASHBOARD_DB_PATH
from webapp.trend import compute_trend_signal

# A same-direction probability move smaller than this is "supporting" the
# current sentiment, not changing it — no write. 0.10 = 10 percentage
# points (e.g. stored BULLISH 65% -> new read BULLISH 71% is NOT material;
# BULLISH 65% -> BULLISH 76% IS). A direction flip is always material,
# regardless of this threshold — see _is_material_change().
MATERIAL_CHANGE_THRESHOLD_PROBABILITY = 0.10
# Used when a calendar fetch fails and there's no fresh event list to
# reason an adaptive interval from — same fallback pattern as
# webapp/scheduler.py's SCHEDULER_INTERVAL_SECONDS.
ACCUMULATOR_FALLBACK_INTERVAL_SECONDS = 15 * 60

# The accumulator's OWN polling cadence — deliberately decoupled from
# webapp.scheduler's adaptive interval, which answers "how urgent is the
# DASHBOARD's calendar polling," a different question from "how often
# should the accumulator re-check ARTICLES for an active event."
FAR_INTERVAL_SECONDS = 12 * 60 * 60      # nothing within any tracked event's pre-event window
HOURLY_INTERVAL_SECONDS = 60 * 60        # baseline once at least one event is active (within its pre-event window)
DAY_OF_EVENT_INTERVAL_SECONDS = 15 * 60  # tighter once an active event is within 24h
FINAL_INTERVAL_SECONDS = 5 * 60          # tightest, within the final hour (or post-release grace)

DAY_OF_EVENT_WINDOW_HOURS = 24
FINAL_WINDOW_HOURS = 1
# Moved to config/settings.py (2026-08-26) so data_layer.calendar_feed's
# events_in_pre_window() can share the exact same constant — it previously
# had no post-release grace period of its own, disagreeing with this
# interval logic's assumption that scoring would continue for
# POST_RELEASE_GRACE_MINUTES after a release. See that constant's comment
# in config/settings.py for the live bug this caused.

# Budget protection: hourly/day-of-event checking is a real, deliberate
# increase in article-fetch volume (see module docstring). If the rolling
# 24h check count gets close to Alpha Vantage's real 25/day quota, fall
# back to a slower cadence rather than either exhausting the quota outright
# or (worse) going fully silent — "spare a small %": reserve ~20% (5 of 25)
# as a floor. Once DAILY_CHECK_BUDGET_THRESHOLD checks have happened in the
# last 24h, further hourly/day-of-event checks back off to
# BUDGET_FALLBACK_INTERVAL_SECONDS until the rolling window frees up
# capacity again. Never applied to FINAL_INTERVAL_SECONDS — missing the
# check right before an actual release is worse than a little extra spend.
DAILY_CHECK_BUDGET_THRESHOLD = 20
BUDGET_FALLBACK_INTERVAL_SECONDS = 3 * 60 * 60

# How many article contributions get attached to a recorded prediction as
# "why did this call change" context (2026-08-17) — see
# _build_top_contributions() and scoring.backtest_store.record_prediction()'s
# top_contributions param. Requested as "top 3 only".
TOP_CONTRIBUTIONS_LIMIT = 3


def _build_top_contributions(contributions: list, limit: int = TOP_CONTRIBUTIONS_LIMIT) -> list[dict]:
    """
    The `limit` article contributions with the largest weight share, for
    display context alongside a recorded prediction — "which articles
    actually drove this call." Ranked by combined_weight (trust x time
    decay), which is each article's real, already-computed share of the
    weighted vote — not re-derived or guessed here. weight_pct is that
    article's share of the TOTAL ARTICLE weight specifically (not the
    full aggregate including precursor/Kalshi/trend/macro-backdrop
    contributions — those are structured signals, not "articles", and
    this feature is scoped to "which article changed this call").

    Returns [] — never fabricated — when there are no article
    contributions at all, or their total weight is zero (e.g. every
    article scored exactly neutral, contributing nothing to weigh).
    `contributions` is expected to be ProbabilityResult.contributions
    (scoring/probability_engine.py's ArticleContribution list — already
    post redundancy-discount, R 2026-08-16), passed in rather than
    recomputed, so this stays a pure display-formatting step with no
    scoring logic of its own.
    """
    total_weight = sum(c.combined_weight for c in contributions)
    if total_weight <= 0:
        return []
    ranked = sorted(contributions, key=lambda c: c.combined_weight, reverse=True)[:limit]
    return [
        {
            "title": c.article.title,
            "url": c.article.url,
            "source": c.article.source,
            "published_utc": c.article.published_utc.isoformat(),
            "usd_sentiment": c.usd_sentiment,
            "weight_pct": round(c.combined_weight / total_weight * 100, 1),
        }
        for c in ranked
    ]


def _is_material_change(
    new_direction: str, new_probability: float, new_article_count: int,
    current_direction: str, current_probability: float, current_article_count: int,
) -> bool:
    """
    True if a freshly-scored read is different ENOUGH from the current
    latest recorded prediction to be worth writing a new snapshot for —
    "current sentiment is the truth until articles are found to contradict
    or change it." A direction flip (including into/out of neutral) is
    always material, regardless of magnitude — that's a contradiction of
    the current read, not a matter of degree. Within the same direction,
    only a move of at least MATERIAL_CHANGE_THRESHOLD_PROBABILITY counts —
    supporting articles that just reinforce the existing call add to its
    validity without triggering a rewrite.

    Also material: crossing THIN_SAMPLE_SIGNAL_THRESHOLD in article_count,
    regardless of direction/probability. Real, live-observed case
    (2026-08-17): "FOMC Meeting Minutes" read NEUTRAL 50% on 0 articles,
    then NEUTRAL 51% on 130 articles roughly a day later — the point
    estimate barely moved, but the evidentiary basis for that call went
    from "no real basis at all" to "genuinely covered," and the Dashboard
    kept showing "0 articles" long after real coverage existed because
    article_count alone was never part of this comparison. A read's
    confidence basis changing qualitatively is itself worth a new
    snapshot, even when the direction/probability stayed put.
    """
    if new_direction != current_direction:
        return True
    was_thin = current_article_count < THIN_SAMPLE_SIGNAL_THRESHOLD
    is_thin = new_article_count < THIN_SAMPLE_SIGNAL_THRESHOLD
    if was_thin != is_thin:
        return True
    # 1e-9 tolerance for float imprecision — e.g. 0.75 - 0.65 == 0.09999999999999998
    # in IEEE754, which would otherwise fail an exact-boundary >= comparison
    # for what's really a value AT the threshold.
    return abs(new_probability - current_probability) >= MATERIAL_CHANGE_THRESHOLD_PROBABILITY - 1e-9


def _read_trend_signal(event_title: str):
    """
    Reads webapp/store.py's event_history for this event title via a
    short-lived READ-ONLY connection to the dashboard's own DB — the
    accumulator writes nothing there, mirroring the existing reverse
    precedent (webapp/app.py already reads scoring/backtest_store.py's DB
    read-only for display). Returns None (fail open, never crashes the
    cycle) if the dashboard DB is unreachable OR if the read itself fails
    for any reason, or if fewer than MIN_OCCURRENCES_FOR_TREND_PRIOR
    confirmed occurrences exist yet —
    trusting a thin pattern enough to nudge a live prediction is a bigger
    claim than merely displaying it (see webapp/trend.py's own, looser
    MIN_CONFIRMED_ROWS_FOR_A_TREND=2 display-only gate for contrast).
    """
    conn = None
    try:
        conn = get_dashboard_connection(DASHBOARD_DB_PATH)
        rows = get_event_history(conn, event_title)
    except Exception as exc:  # noqa: BLE001 — ANY dashboard-DB failure (open OR read) must not crash the accumulator cycle
        print(f"[backtest_accumulator] WARNING: could not read dashboard event_history for {event_title}: {exc}")
        return None
    finally:
        if conn is not None:
            conn.close()

    confirmed = [r for r in rows if r.surprise_direction is not None]
    if len(confirmed) < MIN_OCCURRENCES_FOR_TREND_PRIOR:
        return None
    return compute_trend_signal(confirmed)


def _read_precursor_events(event: EconomicEvent) -> list[EconomicEvent]:
    """
    Reads config.settings.EVENT_INFLUENCE_LINKS-linked precursor events
    for `event` via a short-lived READ-ONLY connection to the dashboard's
    own DB — same pattern and same fail-open contract as
    _read_trend_signal() above. Replaces the old in-memory-calendar
    precursor lookup (removed from data_layer/calendar_feed.py), which
    searched the CURRENT WEEK's in-memory calendar fetch instead of the
    persisted event_history table.
    """
    conn = None
    try:
        conn = get_dashboard_connection(DASHBOARD_DB_PATH)
        return get_precursor_events_for(event.title, event.event_time_utc, conn)
    except Exception as exc:  # noqa: BLE001 — ANY dashboard-DB failure (open OR read) must not crash the accumulator cycle
        print(f"[backtest_accumulator] WARNING: could not read precursor events for {event.title}: {exc}")
        return []
    finally:
        if conn is not None:
            conn.close()


def _shift_back_one_month(d: dt.date) -> dt.date:
    """
    Kalshi's month-only-ticker series (CPI, PPI, NFP, ADP, unemployment
    rate, ISM PMI, PCE, retail sales, challenger job cuts, and their
    y/y and core variants) ticket the DATA/REFERENCE month, not the
    release month — confirmed live: the market titled "CPI in July"
    (ticker KXCPI-26JUL) is the market for the report that RELEASES in
    mid-August, one month later. Forex Factory's event_time_utc is the
    release date, so this shifts it back one month before building the
    expected Kalshi ticker suffix. Handles year rollover (January -> prior December).
    """
    if d.month == 1:
        return d.replace(year=d.year - 1, month=12, day=1)
    return d.replace(month=d.month - 1, day=1)


def _read_kalshi_signal(event: EconomicEvent) -> tuple[Optional[KalshiRead], Optional[str]]:
    """
    Looks up event.title in three mutually-exclusive dicts, in order:
    KALSHI_SERIES_BY_EVENT_TITLE (month-ticketed numeric events),
    KALSHI_DATE_TICKETED_SERIES_BY_EVENT_TITLE (date-ticketed numeric
    events — R4, docs/fundamental-analysis-swot-2026-08-14.md), then
    KALSHI_RATE_DECISION_SERIES (FOMC/Federal Funds Rate — also
    month-ticketed, see that constant's comment in config.settings for
    the live-verification that corrected its prior "date-ticketed"
    misclassification). Returns (kalshi_read, resolved_direction_value):

    - Numeric event (either ticketing style): resolved_direction_value is
      EVENT_SURPRISE_DIRECTION[event.title] verbatim ('higher_bullish' or
      'higher_bearish') — the standard convention every other structured
      contribution in this module already uses.
    - FOMC/Federal Funds Rate: resolved_direction_value is always
      'higher_bullish' — a HIGHER Fed funds rate is unambiguously
      USD-bullish, the same sign the numeric convention already encodes,
      so this reuses that convention rather than introducing a second
      one. (RATE_DECISION_DIRECTION itself, mapping a decision WORD like
      'hike'/'cut' to a sentiment, isn't used here — Kalshi's KXFED
      market already answers "will the rate be higher than X," the same
      shape as every numeric market, so the decision-word mapping isn't
      needed for this blend; it exists in config.settings for any future
      caller that has a decision word instead of a market read.)

    Returns (None, None) — never crashes the cycle — if no series
    mapping matches this title, the forecast (or, for the FOMC branch,
    forecast/previous fallback) can't be parsed to a strike target, or
    the market fetch fails for any reason.
    """
    month_series_ticker = KALSHI_SERIES_BY_EVENT_TITLE.get(event.title)
    if month_series_ticker is not None:
        surprise_direction_value = EVENT_SURPRISE_DIRECTION.get(event.title)
        if surprise_direction_value is None:
            return None, None
        target_strike = _parse_numeric(event.forecast)
        if target_strike is None:
            return None, None
        # Month-only-ticker series (this branch only — see
        # _shift_back_one_month()'s docstring): Kalshi tickets the
        # data/reference month, one month BEHIND the Forex Factory release
        # date, so the raw release date must be shifted back before it's
        # used to build the expected ticker suffix.
        event_month = _shift_back_one_month(event.event_time_utc.date())
        try:
            read = get_market_read(month_series_ticker, event_month, target_strike)
        except Exception as exc:  # noqa: BLE001 — a failed Kalshi fetch must not crash the accumulator cycle
            print(f"[backtest_accumulator] WARNING: Kalshi fetch failed for {event.title}: {exc}")
            return None, None
        if read is None:
            return None, None
        return read, surprise_direction_value

    date_series_ticker = KALSHI_DATE_TICKETED_SERIES_BY_EVENT_TITLE.get(event.title)
    if date_series_ticker is not None:
        surprise_direction_value = EVENT_SURPRISE_DIRECTION.get(event.title)
        if surprise_direction_value is None:
            return None, None
        target_strike = _parse_numeric(event.forecast)
        if target_strike is None:
            return None, None
        try:
            read = get_market_read_by_date(date_series_ticker, event.event_time_utc.date(), target_strike)
        except Exception as exc:  # noqa: BLE001 — a failed Kalshi fetch must not crash the accumulator cycle
            print(f"[backtest_accumulator] WARNING: Kalshi date-ticketed fetch failed for {event.title}: {exc}")
            return None, None
        if read is None:
            return None, None
        return read, surprise_direction_value

    rate_series_ticker = KALSHI_RATE_DECISION_SERIES.get(event.title)
    if rate_series_ticker is not None:
        surprise_direction_value = "higher_bullish"
        # A HOLD-expected FOMC meeting sometimes carries the current rate
        # only in `previous`, not `forecast`, on Forex Factory — fall back
        # so this branch isn't dead every time forecast is blank.
        target_strike = _parse_numeric(event.forecast)
        if target_strike is None:
            target_strike = _parse_numeric(event.previous)
        if target_strike is None:
            return None, None
        try:
            read = get_market_read(rate_series_ticker, event.event_time_utc.date(), target_strike)
        except Exception as exc:  # noqa: BLE001 — a failed Kalshi fetch must not crash the accumulator cycle
            print(f"[backtest_accumulator] WARNING: Kalshi fetch failed for {event.title}: {exc}")
            return None, None
        if read is None:
            return None, None
        return read, surprise_direction_value

    return None, None


def compute_accumulator_interval_seconds(
    events: Optional[list],
    now: Optional[dt.datetime] = None,
    recent_check_count: int = 0,
) -> int:
    """
    The accumulator's own polling cadence — how often its outer loop wakes
    up to run a cycle (which checks every tracked instrument for every
    active event that cycle, per the module docstring). `recent_check_count`
    is the rolling-24h check count from scoring.backtest_store.count_recent_checks() —
    see DAILY_CHECK_BUDGET_THRESHOLD above for how it throttles the result.
    """
    if not events:
        return FAR_INTERVAL_SECONDS

    now = now or dt.datetime.now(dt.timezone.utc)
    tightest = FAR_INTERVAL_SECONDS
    for event in events:
        if event.actual:
            continue  # already resolved — doesn't need tight polling anymore
        hours_until = (event.event_time_utc - now).total_seconds() / 3600.0
        if -POST_RELEASE_GRACE_MINUTES / 60.0 <= hours_until <= FINAL_WINDOW_HOURS:
            return FINAL_INTERVAL_SECONDS  # tightest possible, always exempt from the budget fallback below
        if hours_until <= DAY_OF_EVENT_WINDOW_HOURS:
            tightest = min(tightest, DAY_OF_EVENT_INTERVAL_SECONDS)
        elif hours_until <= PRE_EVENT_WINDOW_HOURS:
            tightest = min(tightest, HOURLY_INTERVAL_SECONDS)

    if tightest in (DAY_OF_EVENT_INTERVAL_SECONDS, HOURLY_INTERVAL_SECONDS) and recent_check_count >= DAILY_CHECK_BUDGET_THRESHOLD:
        tightest = max(tightest, BUDGET_FALLBACK_INTERVAL_SECONDS)
    return tightest


def score_and_record_event(
    conn,
    event: EconomicEvent,
    all_events: list[EconomicEvent],
    instruments: list[str],
    sources,
    now: Optional[dt.datetime] = None,
    macro_backdrop=None,  # MacroBackdropRead | None — duck-typed, see scoring/probability_engine.py's _check_macro_backdrop()/_check_equity_risk_sentiment()/_check_oil_shock()
    cot_positioning=None,  # CotPositioningRead | None — duck-typed, see scoring/probability_engine.py's _check_cot_crowding()
) -> dict:
    """
    Runs the FULL article-based scoring pipeline for ONE event, across
    every instrument in `instruments` — real article fetch, precursors,
    print call, trend signal, Kalshi read, macro-backdrop cross-check,
    score_bundle() per instrument — recording a new scoring/backtest_store
    row ONLY on a material change (_is_material_change()), same "current
    sentiment is the truth until articles are found to contradict or
    change it" rule the normal windowed cycle already follows. This is
    the shared body extracted from run_accumulator_cycle()'s per-event
    loop (2026-08-16) so a manual once-off check
    (scripts/run_manual_sentiment_check.py) for an event NOT yet in its
    automatic pre-event window can reuse the exact same real pipeline and
    persistence semantics, rather than a parallel/duplicated
    implementation.

    `sources` is passed in (not built here) so a caller scoring multiple
    events in one process only builds the RSS/API source list once — same
    reasoning run_accumulator_cycle()'s own lazy `sources` build already
    used. `macro_backdrop` is passed in for the same reason (R5,
    docs/fundamental-analysis-swot-2026-08-14.md) — it's a USD-level read,
    not event-specific, so a caller scoring multiple events in one cycle
    should fetch it once, not once per event.

    `cot_positioning` is passed in for the same reason as `macro_backdrop`
    — it's a USD-level positioning read (weekly CFTC data, not
    event-specific), so a caller scoring multiple events in one cycle
    should fetch it once, not once per event.

    Returns {instrument: ProbabilityResult} for instruments that were
    actually scored (a failed article fetch for the whole event, or a
    per-instrument scoring exception, is logged and simply absent from
    the returned dict — never crashes the caller).
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    results: dict = {}

    try:
        bundle = build_event_news_bundle(event, sources, query="", mode="live")
    except Exception as exc:  # noqa: BLE001 — a failed fetch must not crash the caller
        print(f"[backtest_accumulator] WARNING: article fetch failed for {event.title}: {exc}")
        return results

    # Logged on a successful fetch only — roughly one Alpha Vantage
    # credit spent, in the worst case. Feeds compute_accumulator_interval_seconds()'s
    # budget-fallback check on the NEXT cycle (see module docstring).
    record_check(conn, now)

    # Graph-driven (config.settings.EVENT_INFLUENCE_LINKS) precursor
    # lookup against the dashboard's persisted event_history — replaces
    # the old in-memory calendar search (removed from
    # data_layer/calendar_feed.py). `all_events` is still accepted as a
    # parameter for signature stability (scripts/run_manual_sentiment_check.py
    # still passes it) but is no longer used for precursor lookup.
    precursors = _read_precursor_events(event)
    if precursors:
        print(f"[backtest_accumulator] precursors for {event.title}: {[p.title for p in precursors]}")

    print_call = score_print_direction(bundle)
    if print_call is not None:
        written = record_print_prediction_if_changed(conn, event.title, event.event_time_utc, print_call, now=now)
        if written:
            print(f"[backtest_accumulator] print call for {event.title}: {print_call.direction} ({print_call.confidence:.0%} confidence, {print_call.article_count} articles)")

    trend_signal = _read_trend_signal(event.title)
    if trend_signal is not None:
        print(f"[backtest_accumulator] trend signal for {event.title}: {trend_signal.direction} (strength {trend_signal.strength:.2f})")

    kalshi_read, kalshi_direction_value = _read_kalshi_signal(event)
    if kalshi_read is not None:
        record_kalshi_read_if_changed(conn, event.title, event.event_time_utc, kalshi_read, now=now)
        print(f"[backtest_accumulator] Kalshi read for {event.title}: {kalshi_read.implied_direction} ({kalshi_read.implied_probability:.0%} implied, {kalshi_read.open_interest:.0f} open interest)")

    for instrument in instruments:
        # Fetched BEFORE score_bundle() (not just for the material-change
        # check afterward, as before) so its direction can be passed in as
        # current_direction — enables score_bundle()'s direction hysteresis
        # (see _direction_for_score()), which is what actually stops a
        # flip-flopping read from ever reaching `result.direction` in the
        # first place, rather than filtering it out after the fact.
        latest = get_latest_prediction(conn, event.title, instrument)
        try:
            result = score_bundle(
                bundle, instrument, precursor_events=precursors,
                print_call=print_call, trend_signal=trend_signal,
                kalshi_read=kalshi_read, kalshi_direction_override=kalshi_direction_value,
                macro_backdrop=macro_backdrop,
                cot_positioning=cot_positioning,
                current_direction=latest.direction if latest is not None else None,
            )
        except Exception as exc:  # noqa: BLE001 — one pair's failure must not stop the others
            print(f"[backtest_accumulator] WARNING: scoring failed for {instrument}/{event.title}: {exc}")
            continue

        results[instrument] = result
        if latest is not None and not _is_material_change(
            result.direction.value, result.probability, result.article_count,
            latest.direction, latest.probability, latest.article_count,
        ):
            print(
                f"[backtest_accumulator] checked {instrument} / {event.title}: "
                f"{result.summary()} — unchanged from current, not recorded"
            )
            continue

        record_prediction(
            conn, event.title, instrument, event.event_time_utc,
            result.probability, result.direction.value, result.confidence,
            result.article_count, result.contradiction_flag,
            top_contributions=_build_top_contributions(result.contributions),
        )
        print(f"[backtest_accumulator] recorded {instrument} / {event.title}: {result.summary()}")

    return results


def run_accumulator_cycle(
    instruments: list[str],
    db_path: Optional[Path] = None,
    now: Optional[dt.datetime] = None,
) -> Optional[list]:
    """
    Returns the fetched high-impact events on success (the caller uses
    this to pick the next adaptive poll interval), or None if the
    calendar fetch failed.
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    conn = get_connection(db_path)
    try:
        try:
            all_events = fetch_calendar("thisweek")
        except Exception as exc:  # noqa: BLE001 — a failed fetch must not crash the loop
            print(f"[backtest_accumulator] WARNING: calendar fetch failed: {exc}")
            return None

        # High-impact only (default), plus a curated allowlist of specific
        # Medium-impact titles worth the article-fetch budget (see
        # config.settings.ACCUMULATOR_MEDIUM_ALLOWLIST) — NOT a blanket
        # Medium+ threshold like the dashboard's free essence-only scoring,
        # which would dilute this pipeline's tuned signal budget.
        events = filter_relevant_events(all_events, extra_titles=ACCUMULATOR_MEDIUM_ALLOWLIST)
        active = events_in_pre_window(events, now_utc=now)

        sources = None  # lazily built, only if at least one event is actually active this cycle
        macro_backdrop = None
        macro_backdrop_fetched = False
        cot_positioning = None
        cot_positioning_fetched = False
        for event in active:
            # Every tracked instrument is checked for every active event on
            # every cycle — no per-pair check budget (see module docstring
            # for why, and the real fetch-volume cost of this). The article
            # bundle is still fetched at most once per EVENT, not once per
            # instrument — identical across instruments for a given event.
            if sources is None:
                sources = build_all_preview_sources()
            # R5: fetched once per CYCLE, not once per event — it's a
            # USD-level read (dollar index / real yields), not specific to
            # any one event, same "build once, reuse" reasoning as `sources`
            # above. macro_backdrop_fetched (not `macro_backdrop is None`)
            # is the actual gate — a real fetch that legitimately returns
            # None (e.g. FRED_API_KEY unset) must not retry every event.
            if not macro_backdrop_fetched:
                macro_backdrop = get_macro_backdrop_read()
                macro_backdrop_fetched = True
            # Same once-per-cycle reasoning as macro_backdrop above — COT
            # is weekly data, not event-specific.
            if not cot_positioning_fetched:
                cot_positioning = get_cot_positioning_read()
                cot_positioning_fetched = True
            score_and_record_event(
                conn, event, all_events, instruments, sources, now=now,
                macro_backdrop=macro_backdrop, cot_positioning=cot_positioning,
            )

        return events
    finally:
        conn.close()


def start_accumulator(instruments: list[str]) -> None:
    def _loop():
        while True:
            try:
                events = run_accumulator_cycle(instruments)
                if events is None:
                    interval = ACCUMULATOR_FALLBACK_INTERVAL_SECONDS
                else:
                    now = dt.datetime.now(dt.timezone.utc)
                    conn = get_connection()
                    try:
                        recent_checks = count_recent_checks(conn, since=now - dt.timedelta(hours=24))
                    finally:
                        conn.close()
                    interval = compute_accumulator_interval_seconds(events, now=now, recent_check_count=recent_checks)
                    if interval >= BUDGET_FALLBACK_INTERVAL_SECONDS:
                        print(f"[backtest_accumulator] check budget: {recent_checks} in the last 24h — backing off to {interval}s")
            except Exception as exc:  # noqa: BLE001 — the loop must survive any unhandled error
                print(f"[backtest_accumulator] ERROR: cycle failed, will retry next interval: {exc}")
                interval = ACCUMULATOR_FALLBACK_INTERVAL_SECONDS
            time.sleep(interval)

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()


if __name__ == "__main__":
    from config.settings import INSTRUMENTS
    tracked = list(INSTRUMENTS.keys())
    print(f"Running one accumulator cycle for: {tracked}")
    run_accumulator_cycle(tracked)
    print("Done. For continuous operation, run scripts/run_accumulator.py instead.")
