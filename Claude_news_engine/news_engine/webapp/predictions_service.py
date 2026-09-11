"""
Assembles the /api/predictions response — extracted from webapp/app.py's
get_predictions() route (dashboard-review-2026-09-11.md: "app.py is a
800+ line file with one 230-line route function... hard to unit-test in
isolation"). The route itself now just opens/closes connections and calls
build_predictions_payload(); all the per-symbol/per-event enrichment,
reconciliation, and sorting logic lives here where it can be tested
without going through Flask's test client.

No behavior changed by this extraction — every comment and code path
below is moved verbatim from app.py, not rewritten.
"""
from __future__ import annotations

import datetime as dt
import logging
import sqlite3
from typing import Optional

from config.settings import EVENT_SURPRISE_DIRECTION, PREDICTIONS_RECENT_RESOLVED_RETENTION_DAYS
from data_layer.calendar_feed import EconomicEvent, IMPACT_RANK
from webapp.scoring_service import score_event_for_symbol
from webapp.store import (
    list_tracked_symbols, get_calendar_snapshot, get_event_history_bulk,
    get_latest_two_bulk, get_resolved_event_history, EventHistoryRow,
)
from webapp.trend import compute_trend_signal, MIN_CONFIRMED_ROWS_FOR_A_TREND
from webapp.symbols import classify_symbol
from scoring.backtest_store import (
    get_latest_two_predictions_bulk, get_latest_print_predictions_bulk,
    get_latest_kalshi_reads_bulk, get_latest_tier1_predictions_bulk,
    get_last_check_utc, Prediction,
)
from webapp.reconciliation import reconcile_group

logger = logging.getLogger(__name__)


def _article_prediction_dict(pred: "Prediction") -> dict:
    """
    The shared article_prediction/previous_article_prediction shape built
    from a scoring.backtest_store.Prediction row — direction, probability,
    article_count, and its "why did this call change" top_contributions
    (2026-08-17). Extracted (final whole-branch review, 2026-09-06 —
    Finding 4) so the per-title construction and the reconciliation
    agreement branch in build_predictions_payload() can't drift apart.
    """
    return {
        "direction": pred.direction,
        "probability": pred.probability,
        "article_count": pred.article_count,
        "top_contributions": pred.top_contributions,
    }


def _print_prediction_dict(print_call) -> dict:
    """
    The shared print_prediction shape built from a scoring.print_direction
    call — identical shape /api/calendar/date/<date> built inline
    (dashboard-review-2026-09-11.md: "duplicate serialization logic
    across three routes... only article_prediction got the shared-helper
    treatment"). Extracted so both routes share one definition instead of
    two copies that can silently drift apart.
    """
    return {"direction": print_call.predicted_vs_forecast, "confidence": print_call.confidence}


def _tier1_prediction_dict(tier1_row) -> dict:
    """The shared tier1_prediction shape built from a Tier1PredictionRow — same extraction reasoning as _print_prediction_dict() above."""
    return {
        "value": tier1_row.value,
        "confidence": tier1_row.confidence,
        "source": tier1_row.source,
        "predicted_direction": tier1_row.predicted_direction,
    }


def _trend_instrument_lean(event_title: str, trend_direction: str, usd_relationship: Optional[str]) -> Optional[str]:
    """
    Translates a trend streak's raw forecast-relative direction ('higher'/
    'lower') into a USD-bullish/bearish/neutral lean for THIS instrument —
    same EVENT_SURPRISE_DIRECTION + usd_relationship mapping score_bundle()
    uses internally, reimplemented here at display-only granularity (no
    score_bundle() call, no scoring-math change). Returns None — never
    fabricated — when event_title has no EVENT_SURPRISE_DIRECTION entry, or
    when usd_relationship is None (classify_symbol()'s fx_cross case — no
    USD exposure to derive a lean from).
    """
    surprise_mapping = EVENT_SURPRISE_DIRECTION.get(event_title)
    if surprise_mapping is None:
        return None
    # surprise_mapping is 'higher_bullish' or 'higher_bearish' — the sign
    # this event's "higher than forecast" carries for USD.
    higher_is_usd_bullish = surprise_mapping == "higher_bullish"
    usd_bullish = higher_is_usd_bullish if trend_direction == "higher" else not higher_is_usd_bullish

    if usd_relationship == "inverse":
        instrument_bullish = not usd_bullish
    elif usd_relationship == "direct":
        instrument_bullish = usd_bullish
    elif usd_relationship == "risk_sentiment":
        instrument_bullish = not usd_bullish  # dovish/USD-bearish -> risk-on -> equity-bullish, same simplification score_bundle() uses
    else:
        return None
    return "bullish" if instrument_bullish else "bearish"


def compute_tier1_sentiment_conflict(
    sentiment_direction: Optional[str], tier1_direction: Optional[str],
) -> Optional[dict]:
    """
    Shared by build_predictions_payload() (Dashboard card) and
    webapp/history.py (History tab) — the exact comparison rule
    build_predictions_payload() originally computed inline
    (fundamental-analysis-review-2026-09-11.md P0 #5), extracted so
    History can apply the identical rule instead of re-deriving it.
    "No call" on either side (None, or 'neutral') is never a conflict —
    only a REAL, opposing directional call from both sides counts, same
    convention scoring/backtest.py's BacktestCase.evaluate() already uses
    for Tier 1's own accuracy metric.
    """
    if sentiment_direction not in ("bullish", "bearish") or tier1_direction not in ("bullish", "bearish"):
        return None
    if sentiment_direction == tier1_direction:
        return None
    return {"sentiment_direction": sentiment_direction, "tier1_direction": tier1_direction}


def _recompute_stale_pending(
    event: dict, symbol_class, history_rows: list[EventHistoryRow],
):
    """
    R1 fix (docs/fundamental-analysis-swot-2026-08-14.md): webapp/store.py's
    prediction_runs is written once per webapp/scheduler.py cycle, against
    whatever the live calendar fetch showed AT THAT TIME. If the scheduler
    saw actual=None and persisted direction="pending", and a LATER process
    (scripts/fill_missing_actuals.py, or a scheduler cycle blocked by
    data_layer.calendar_feed's FF rate-limit cooldown) resolves the real
    actual into event_history without a fresh scheduler write ever
    following it, the dashboard's primary gauge is stuck showing a stale
    "pending" for an event that has genuinely resolved — a live,
    user-facing correctness bug, not a modeling limitation.

    Read-time merge, per the approach agreed with the user: when this
    happens, recompute the essence-only score on the fly from
    event_history's real actual — WITHOUT writing prediction_runs (that
    stays the scheduler's job/pattern; recomputing on every request read
    is cheap local arithmetic, not a live fetch).

    Returns None — never a fabricated score — if no matching resolved
    event_history row exists for this exact occurrence, or the recompute
    itself still comes back pending/inapplicable (e.g. the title has no
    EVENT_SURPRISE_DIRECTION entry). The caller then falls through to the
    existing "pending" display, unchanged.
    """
    match = next(
        (r for r in history_rows if r.event_time_utc == event["event_time_utc"] and r.actual is not None),
        None,
    )
    if match is None:
        return None
    enriched_event = EconomicEvent(
        title=event["title"], country="USD", impact=event.get("impact") or "High",
        event_time_utc=dt.datetime.fromisoformat(event["event_time_utc"]),
        forecast=match.forecast, previous=match.previous, actual=match.actual,
    )
    result = score_event_for_symbol(enriched_event, symbol_class)
    if not result.applicable or result.pending:
        return None
    return result


def build_predictions_payload(conn: sqlite3.Connection, backtest_conn: sqlite3.Connection) -> dict:
    """
    Builds the exact dict /api/predictions jsonify()s — moved verbatim out
    of webapp/app.py's get_predictions() route so it can be unit-tested
    without a Flask test client, and so the route function itself stays a
    thin open/call/close/serialize wrapper. Callers own the connections
    (open before calling, close after) — this function never opens or
    closes either one itself.
    """
    symbols = list_tracked_symbols(conn)
    # No live fetch here either — same reasoning as /api/calendar. `error`
    # means "nothing persisted yet," not "a live request just failed."
    snapshot = get_calendar_snapshot(conn)
    raw_events = snapshot.events if snapshot is not None else []
    # Medium+ only — the persisted snapshot is deliberately Low+ (it feeds
    # the Calendar tab's own /api/calendar route, which must keep seeing
    # every Low-impact event), but a Low-impact event must NEVER become a
    # dashboard card/gauge (Global Constraint). Impact-unknown (missing/
    # None) is also excluded — same fail-safe direction used below for the
    # recently-resolved backfill: when impact tier is unknown, treat it as
    # NOT card-worthy rather than risk showing a card for something that
    # might be Low-impact.
    events = [e for e in raw_events if IMPACT_RANK.get(e.get("impact"), 0) >= IMPACT_RANK["Medium"]]
    error = None if snapshot is not None else "Calendar data not yet available — waiting for the first background fetch."

    # Merge recently-resolved events back in even after FF's own live feed
    # has moved past them (config.settings.PREDICTIONS_RECENT_RESOLVED_RETENTION_DAYS,
    # 7 days) — investigated live 2026-08-16: CPI m/m and PPI m/m both had
    # real, resolved prediction_runs/event_history/accumulator rows that
    # were never lost, only stopped being SHOWN, the moment their dates
    # scrolled out of FF's current "thisweek" window — this route used to
    # build its event list ONLY from that live snapshot. Only events not
    # already present via FF's own snapshot are added; FF stays the
    # higher-trust, more complete source whenever it still has the
    # occurrence (same "FF always wins on a match" rule the macro-calendar
    # merge already uses).
    now = dt.datetime.now(dt.timezone.utc)
    retention_cutoff = now - dt.timedelta(days=PREDICTIONS_RECENT_RESOLVED_RETENTION_DAYS)
    existing_keys = {(e["title"], e["event_time_utc"]) for e in events}
    recently_resolved = [
        {
            "title": row.event_title, "country": "USD", "impact": None,
            "event_time_utc": row.event_time_utc,
            "forecast": row.forecast, "previous": row.previous, "actual": row.actual,
        }
        for row in get_resolved_event_history(conn)
        if dt.datetime.fromisoformat(row.event_time_utc) >= retention_cutoff
        and (row.event_title, row.event_time_utc) not in existing_keys
        # Medium+ only — IMPACT_RANK.get(row.impact, 0) is 0 for both a
        # genuinely Low-impact row and a legacy/impact-unknown row (impact
        # IS NULL, e.g. a row written before webapp/store.py's impact
        # column existed), and 0 is always below IMPACT_RANK["Medium"].
        # That's the deliberate fail-safe: when impact tier is unknown,
        # treat it as NOT card-worthy rather than risk showing one for
        # something that might be Low-impact (design doc: "recently
        # resolved backfill: scope to USD Medium+ only").
        and IMPACT_RANK.get(row.impact, 0) >= IMPACT_RANK["Medium"]
    ]
    events = events + recently_resolved

    # Batched, once per request — replaces what used to be up to 6 separate
    # DB round trips per (symbol, event) pair (an N+1 query pattern that
    # scaled with len(symbols) * len(events), re-run on every 60s poll).
    # Each dict below is keyed exactly the way its per-pair predecessor was
    # scoped, so every lookup inside the loop below is now a plain dict.get()
    # instead of a query.
    event_titles = list({event["title"] for event in events})
    latest_two_by_symbol_title = get_latest_two_bulk(conn, symbols, event_titles)
    event_history_by_title = get_event_history_bulk(conn, event_titles)
    accumulator_latest_two_by_title_symbol = get_latest_two_predictions_bulk(backtest_conn, event_titles, symbols)
    print_predictions_by_occurrence = get_latest_print_predictions_bulk(backtest_conn, event_titles)
    kalshi_reads_by_occurrence = get_latest_kalshi_reads_bulk(backtest_conn, event_titles)
    # Fail open (same reasoning as the per-occurrence try/except this
    # replaces, final whole-branch review 2026-09-07 — Finding 2): a
    # broken Tier 1 lookup must never take down the whole route.
    try:
        tier1_by_occurrence = get_latest_tier1_predictions_bulk(backtest_conn, event_titles, symbols)
    except Exception:
        logger.warning("get_latest_tier1_predictions_bulk failed for this cycle", exc_info=True)
        tier1_by_occurrence = {}

    predictions = []
    for ticker in symbols:
        symbol_class = classify_symbol(ticker)
        entry = {"symbol": ticker, "symbol_class": symbol_class.symbol_class, "events": []}
        accumulator_predictions_by_time_and_title: dict[str, dict[str, "Prediction"]] = {}
        for event in events:
            # Normalized via parse+isoformat, not the raw event_time_utc
            # string, before use as a dict key below — this codebase has
            # more than one producer of event_time_utc strings and their
            # formatting isn't guaranteed byte-identical for the same
            # instant (same "compare parsed datetimes" rule Finding 1,
            # 2026-09-06 already established a few lines below). Computed
            # once here (moved up from its old position, where it only fed
            # the trend signal) since print_call/kalshi/tier1 all need it now too.
            event_time = dt.datetime.fromisoformat(event["event_time_utc"])
            event_time_key = event_time.isoformat()
            runs = latest_two_by_symbol_title.get((ticker, event["title"]), [])
            latest = runs[0] if runs else None
            previous = runs[1] if len(runs) > 1 else None

            # R1 fix (docs/fundamental-analysis-swot-2026-08-14.md): fetched
            # here (moved up from its old position further below, where it
            # only fed the trend signal) so it can ALSO drive the
            # stale-pending recompute immediately below — one lookup serves
            # both, removing what used to be a duplicate fetch.
            prior_occurrences = event_history_by_title.get(event["title"], [])
            recomputed = None
            if latest is None or latest.direction == "pending":
                recomputed = _recompute_stale_pending(event, symbol_class, prior_occurrences)

            # The accumulator's own blind, article-based call — direction
            # and probability, not just how many articles backed it. This
            # is a REAL prediction the accumulator already made independently,
            # not derived from the essence-only score above; it can exist
            # (and disagree) even while the essence-only score is still
            # "pending," since the accumulator predicts BEFORE the event
            # resolves. Previously only article_count surfaced here, which
            # left the actual call itself invisible on the dashboard.
            #
            # Two rows, not one: scoring/backtest_accumulator.py only
            # RECORDS a snapshot on a material change (direction flip, or a
            # same-direction move past its threshold) — so unlike the
            # essence-only score's every-cycle rows, any two consecutive
            # article predictions represent a genuine shift, not noise.
            # That's exactly what the frontend's diff strip needs.
            accumulator_runs = accumulator_latest_two_by_title_symbol.get((event["title"], ticker), [])
            accumulator_prediction = accumulator_runs[0] if accumulator_runs else None
            accumulator_predictions_by_time_and_title.setdefault(event["event_time_utc"], {})
            # Finding 1 (final whole-branch review, 2026-09-06): the row
            # get_latest_two_predictions() returns is scoped only to
            # (event_title, instrument) — NOT to this occurrence's own
            # event_time_utc. scoring/backtest_accumulator.py only writes a
            # fresh predictions row on a "material change," so the newest
            # row for a title can still carry a PRIOR occurrence's
            # event_time_utc indefinitely. Admitting that stale row into
            # the reconciliation group would let it vote alongside genuinely
            # fresh co-released siblings, producing a false conflict or a
            # false agreement. Compare parsed datetimes, not raw strings —
            # this codebase has more than one producer of event_time_utc
            # strings and their formatting isn't guaranteed identical.
            if (accumulator_prediction is not None
                    and dt.datetime.fromisoformat(accumulator_prediction.event_time_utc)
                    == dt.datetime.fromisoformat(event["event_time_utc"])):
                accumulator_predictions_by_time_and_title[event["event_time_utc"]][event["title"]] = accumulator_prediction
            accumulator_previous = accumulator_runs[1] if len(accumulator_runs) > 1 else None
            article_prediction = None
            if accumulator_prediction is not None:
                # "Why did this call change" context (2026-08-17) —
                # top_contributions are up to TOP_CONTRIBUTIONS_LIMIT
                # article contributions ranked by weight share, computed
                # and persisted alongside this exact prediction row at
                # scoring time (scoring/backtest_accumulator.py's
                # _build_top_contributions()) — never recomputed here.
                article_prediction = _article_prediction_dict(accumulator_prediction)
            previous_article_prediction = None
            if accumulator_previous is not None:
                previous_article_prediction = _article_prediction_dict(accumulator_previous)
            print_call = print_predictions_by_occurrence.get((event["title"], event_time_key))
            print_prediction = _print_prediction_dict(print_call) if print_call is not None else None

            # Two more independently-computed signals, same read-only
            # pattern as article_prediction/print_prediction above.
            # compute_trend_signal() requires its input pre-filtered to
            # confirmed (non-None surprise_direction) rows and non-empty
            # (see webapp/trend.py's docstring) — unlike
            # scoring/backtest_accumulator.py's live-scoring caller, this
            # is a mere display, so no MIN_OCCURRENCES_FOR_TREND_PRIOR
            # gate is applied here. It DOES apply the same
            # MIN_CONFIRMED_ROWS_FOR_A_TREND floor summarize_trend() uses,
            # though — this is the one place a user actually sees the
            # numeric strength, and with exactly 1 confirmed row
            # _analyze_trend()'s tally branch saturates strength at 1.0
            # (maximum conviction from a single data point), same failure
            # summarize_trend() already guards against.
            confirmed_occurrences = [r for r in prior_occurrences if r.surprise_direction is not None]
            trend = (
                compute_trend_signal(confirmed_occurrences)
                if len(confirmed_occurrences) >= MIN_CONFIRMED_ROWS_FOR_A_TREND
                else None
            )
            trend_signal = None
            if trend is not None:
                trend_signal = {
                    "direction": trend.direction, "strength": trend.strength,
                    "instrument_lean": _trend_instrument_lean(event["title"], trend.direction, symbol_class.usd_relationship),
                }

            kalshi_row = kalshi_reads_by_occurrence.get((event["title"], event_time_key))
            kalshi_read = None
            if kalshi_row is not None:
                kalshi_read = {
                    "implied_direction": kalshi_row.implied_direction,
                    "implied_probability": kalshi_row.implied_probability,
                    "open_interest": kalshi_row.open_interest,
                }

            # tier1_by_occurrence was fetched in bulk above (with its own
            # fail-open try/except around the whole batch) — a plain lookup
            # here, no per-occurrence try/except needed any more.
            tier1_row = tier1_by_occurrence.get((event["title"], ticker, event_time_key))
            tier1_prediction = _tier1_prediction_dict(tier1_row) if tier1_row is not None else None

            # An event is only worth including in this symbol's list at
            # all if SOME layer has something to say about it — an event
            # with zero essence score AND zero article prediction AND zero
            # print call AND zero trend signal AND zero Kalshi read is
            # genuinely nothing-yet, same as before (extended here so
            # Task 9's two new signals can't be silently dropped by a
            # guard that never learned about them, and R1's read-time
            # recompute counts as "something to say" even when `latest`
            # itself is still the stale pending row).
            if (latest is None and recomputed is None and article_prediction is None and print_prediction is None
                    and trend_signal is None and kalshi_read is None and tier1_prediction is None):
                continue

            if recomputed is not None:
                direction_value = recomputed.direction.value
                probability_value = recomputed.probability
            else:
                direction_value = latest.direction if latest else "pending"
                probability_value = latest.probability if latest else None

            entry["events"].append({
                "event_title": event["title"],
                "event_time_utc": event["event_time_utc"],
                "probability": probability_value,
                "direction": direction_value,
                "recomputed_from_event_history": recomputed is not None,
                "previous_probability": previous.probability if previous else None,
                "previous_direction": previous.direction if previous else None,
                "article_count": accumulator_prediction.article_count if accumulator_prediction else None,
                "article_prediction": article_prediction,
                "article_prediction_conflict": None,
                "previous_article_prediction": previous_article_prediction,
                "print_prediction": print_prediction,
                "trend_signal": trend_signal,
                "kalshi_read": kalshi_read,
                "tier1_prediction": tier1_prediction,
                "tier1_sentiment_conflict": None,  # computed below, after reconciliation settles article_prediction's final value
            })

        for time_key, predictions_by_title in accumulator_predictions_by_time_and_title.items():
            if len(predictions_by_title) < 2:
                continue
            try:
                reconciled = reconcile_group(predictions_by_title)
            except Exception as exc:  # noqa: BLE001 — a reconciliation bug must not crash the whole route
                logger.warning("reconciliation failed for %s: %s", time_key, exc)
                continue
            if reconciled is None:
                continue
            for ev in entry["events"]:
                if ev["event_time_utc"] != time_key or ev["event_title"] not in predictions_by_title:
                    continue
                if reconciled.conflict:
                    ev["article_prediction"] = None
                    ev["article_prediction_conflict"] = {"titles": reconciled.conflicting_titles}
                else:
                    ev["article_prediction"] = _article_prediction_dict(reconciled.prediction)
                    ev["article_prediction_conflict"] = None
                    # Finding 2 (final whole-branch review, 2026-09-06): a
                    # non-dominant title's own previous_article_prediction
                    # is a DIFFERENT title's prior snapshot. Leaving it in
                    # place while article_prediction is overwritten with
                    # the dominant title's numbers lets the frontend's diff
                    # strip (buildDiffStripHtml) compare two different
                    # titles' predictions as if one title shifted between
                    # them — a fabricated "shift" that never happened.
                    # reconcile_group() doesn't expose the dominant title's
                    # own previous snapshot, so null it out for everyone
                    # except the dominant title itself, whose
                    # previous_article_prediction is already correctly its
                    # own prior snapshot and is left untouched.
                    if ev["event_title"] != reconciled.prediction.event_title:
                        ev["previous_article_prediction"] = None

        # Tier 1 vs. sentiment contradiction detection
        # (fundamental-analysis-review-2026-09-11.md P0 #5) — the Sep 10
        # PPI divergence (Tier 1 logged Certain/bullish, wrong; sentiment
        # called bearish, right) shipped to the dashboard with zero flag
        # anywhere, even though reconcile_group() already exists for
        # exactly this class of problem, just scoped to co-released
        # sentiment titles rather than a cross-system disagreement. This
        # REVISES the live-tier1-dashboard-display spec's original "no
        # agree/disagree computation on the live path" constraint
        # (2026-09-07) — kept BacktestReport.agreement_rate() itself
        # untouched (still backtest-only), but a live flag is now real
        # product intent, not scope creep.
        #
        # Computed here, AFTER reconciliation above, since reconciliation
        # can overwrite article_prediction for a co-released title — this
        # must compare the FINAL value the card actually shows, not a
        # pre-reconciliation snapshot. "No call" (neutral, or either side
        # simply absent) is never a conflict — same convention
        # scoring/backtest.py's BacktestCase.evaluate() already uses for
        # Tier 1's own accuracy metric: only a REAL, opposing directional
        # call from both sides counts as a contradiction.
        for ev in entry["events"]:
            article_pred = ev["article_prediction"]
            tier1_pred = ev["tier1_prediction"]
            if article_pred is None or tier1_pred is None:
                continue
            ev["tier1_sentiment_conflict"] = compute_tier1_sentiment_conflict(
                article_pred["direction"], tier1_pred["predicted_direction"],
            )

        # A FRESHLY resolved score outranks a still-pending one, regardless
        # of which is chronologically closer — a real BUY/SELL/HOLD call is
        # more useful to show than an "awaiting" placeholder for a nearer
        # event (confirmed: this is a deliberate product choice, not just a
        # same-timestamp tie-break — release days routinely publish several
        # sub-metrics at the IDENTICAL time, e.g. Core CPI m/m, Core CPI y/y,
        # CPI m/m, CPI y/y all at 12:30 UTC, and a naive proximity-only sort
        # would let a still-pending sibling mask one that has actually scored).
        #
        # "Freshly" is the key correction (2026-08-17): once
        # Pending events (what's still worth watching) always sort ahead of
        # resolved ones, full stop — not just within a freshness window.
        #
        # This is a 2026-08-26 reversal of the original rule ("a freshly
        # resolved score outranks a nearer pending event," bounded by
        # RESOLVED_PRIORITY_WINDOW_HOURS so a STALE resolved event wouldn't
        # permanently mask a genuinely imminent one — see git history for
        # that fix's own reasoning). Reversed after a live incident: a
        # resolved event's essence score can get recomputed from
        # event_history at ANY time — independent of the scheduler's own
        # cadence — e.g. scripts/fill_missing_actuals.py patching in a real
        # actual hours after release. That made "resolved" an unreliable
        # signal for "this is current" and it was burying a genuinely
        # upcoming pending event (Unemployment Claims) under an
        # already-resolved one (Core PCE Price Index m/m) purely because
        # the resolved one happened to get recomputed more recently.
        #
        # Within the pending tier, a genuinely UPCOMING pending event still
        # outranks one whose release time already passed but is still stuck
        # "pending" (observed live: the calendar feed can lag publishing an
        # actual for hours after the scheduled time) — abs(distance) alone
        # treats "6h48m ago, stuck" as closer than "11h from now, upcoming"
        # and would keep showing the stale event long after a real next
        # event exists to show instead.
        now = dt.datetime.now(dt.timezone.utc)

        def _sort_key(ev):
            event_time = dt.datetime.fromisoformat(ev["event_time_utc"])
            is_pending = ev["direction"] == "pending"
            return (
                0 if is_pending else 1,
                is_pending and event_time < now,
                abs((event_time - now).total_seconds()),
            )

        entry["events"].sort(key=_sort_key)
        predictions.append(entry)

    # How long since the article-based accumulator (scripts/run_accumulator.py
    # — a SEPARATE process from this Flask app, see its module docstring)
    # last actually completed a check. Same "None means no data yet, not
    # zero staleness" contract as /api/calendar's feed_staleness_seconds.
    # Exists because that separation is easy to get wrong operationally —
    # confirmed live 2026-08-19: the accumulator process was simply not
    # running for most of a session while this dashboard kept serving
    # stale article_prediction data with no visible sign anything was
    # wrong, discoverable only by noticing identical numbers across
    # requests. This field makes that visible instead of requiring that.
    last_check_utc = get_last_check_utc(backtest_conn)
    accumulator_staleness_seconds = (
        (dt.datetime.now(dt.timezone.utc) - last_check_utc).total_seconds()
        if last_check_utc is not None else None
    )

    return {
        "predictions": predictions, "error": error,
        "accumulator_staleness_seconds": accumulator_staleness_seconds,
    }
