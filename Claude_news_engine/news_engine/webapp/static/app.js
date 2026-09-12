import {
  escapeHtml, confidenceColorClass, formatEventDateTime, toIsoDateLocal,
  directionLabel, directionClass, directionPct, gaugeSvg, bullBearScaleSvg,
  buildDiffStripHtml, diffPieSvg, dayStripHtml, tier1DirectionLabel,
} from "./js/format.js";

const POLL_INTERVAL_MS = 60_000;

// Batch 10 (dashboard-review-2026-09-11.md live UI walkthrough): "1% and
// 100% render as identical plain text" — no threshold treatment
// distinguished a genuinely strong call from a noise-level one anywhere in
// the UI. Not a new scale — a visual rendering of the 3-tier split this
// codebase's own confidence language already uses elsewhere (Tier 1's
// Certain/Likely/Guessing tags).

const cardsEl = document.getElementById("cards");
const calendarGridEl = document.getElementById("calendar-grid");
const addForm = document.getElementById("add-symbol-form");
const addInput = document.getElementById("add-symbol-input");
const calendarStaleNoticeEl = document.getElementById("calendar-stale-notice");
const predictionsStaleNoticeEl = document.getElementById("predictions-stale-notice");
// Distinct from the two notices above (which mean "the backend has no
// data yet") — these mean "the browser itself failed to reach the server
// on the last poll" (dashboard-review-2026-09-11.md: a transient network
// blip used to throw an unhandled rejection and silently freeze the
// dashboard on stale data with no visible sign anything was wrong).
const predictionsPollErrorEl = document.getElementById("predictions-poll-error-notice");
const calendarPollErrorEl = document.getElementById("calendar-poll-error-notice");
const feedStalenessEl = document.getElementById("feed-staleness-indicator");
const accumulatorStalenessEl = document.getElementById("accumulator-staleness-indicator");

// Thresholds from docs/calendar-feed-staleness-policy.md's operational
// policy table — display-only, no scoring impact.
const FEED_STALENESS_FRESH_SECONDS = 3 * 60 * 60;
const FEED_STALENESS_AGING_SECONDS = 24 * 60 * 60;

function renderFeedStaleness(seconds) {
  if (feedStalenessEl == null) return;
  if (seconds == null) {
    feedStalenessEl.textContent = "Calendar feed: never fetched yet";
    feedStalenessEl.className = "feed-staleness stale";
    return;
  }
  const minutes = Math.round(seconds / 60);
  const label = minutes < 60 ? `${minutes}m ago` : `${(seconds / 3600).toFixed(1)}h ago`;
  const level = seconds < FEED_STALENESS_FRESH_SECONDS ? "fresh" : seconds < FEED_STALENESS_AGING_SECONDS ? "aging" : "stale";
  feedStalenessEl.textContent = `Forex Factory feed last checked: ${label}`;
  feedStalenessEl.className = `feed-staleness ${level}`;
}

// The article-based accumulator (scripts/run_accumulator.py) is a
// SEPARATE process from this Flask app — it can silently stop running
// (crash, never started, sandbox reset) while the dashboard keeps
// serving whatever article_prediction it last computed, with nothing
// otherwise distinguishing that from a healthy "no new articles" quiet
// period. Tighter thresholds than the calendar feed's — this pipeline is
// meant to poll far more frequently near a live event (down to 5-minute
// intervals, see webapp/scheduler.py's FINAL_INTERVAL_SECONDS), so an
// hour of silence is already a real signal something's wrong, not routine.
const ACCUMULATOR_STALENESS_FRESH_SECONDS = 20 * 60;
const ACCUMULATOR_STALENESS_AGING_SECONDS = 60 * 60;

function renderAccumulatorStaleness(seconds) {
  if (accumulatorStalenessEl == null) return;
  if (seconds == null) {
    accumulatorStalenessEl.textContent = "Article accumulator: never run — start scripts/run_accumulator.py";
    accumulatorStalenessEl.className = "feed-staleness stale";
    return;
  }
  const minutes = Math.round(seconds / 60);
  const label = minutes < 60 ? `${minutes}m ago` : `${(seconds / 3600).toFixed(1)}h ago`;
  const level = seconds < ACCUMULATOR_STALENESS_FRESH_SECONDS ? "fresh" : seconds < ACCUMULATOR_STALENESS_AGING_SECONDS ? "aging" : "stale";
  accumulatorStalenessEl.textContent = `Article accumulator last checked: ${label}`;
  accumulatorStalenessEl.className = `feed-staleness ${level}`;
}

// Local-calendar-date ISO string (YYYY-MM-DD). NOT Date.toISOString() —
// that converts to UTC first, which would shift the date for any
// non-UTC+0 local timezone (e.g. SAST/UTC+2 local midnight becomes the
// previous day at 22:00 UTC) and desync the cell's data-date from the
// cell's own displayed day number.

document.getElementById("tab-dashboard").addEventListener("click", () => showView("dashboard"));
document.getElementById("tab-calendar").addEventListener("click", () => showView("calendar"));
document.getElementById("tab-history").addEventListener("click", () => {
  showView("history");
  loadHistoryIfNeeded();
});

function showView(name) {
  document.getElementById("view-dashboard").style.display = name === "dashboard" ? "" : "none";
  document.getElementById("view-calendar").style.display = name === "calendar" ? "" : "none";
  document.getElementById("view-history").style.display = name === "history" ? "" : "none";
  document.getElementById("tab-dashboard").classList.toggle("active", name === "dashboard");
  document.getElementById("tab-calendar").classList.toggle("active", name === "calendar");
  document.getElementById("tab-history").classList.toggle("active", name === "history");
}

addForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const ticker = addInput.value.trim().toUpperCase();
  if (!ticker) return;
  const resp = await fetch("/api/symbols", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker }),
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    alert(body.error || "Could not add symbol");
    return;
  }
  addInput.value = "";
  await refreshDashboard();
});

async function removeSymbol(ticker) {
  await fetch(`/api/symbols/${ticker}`, { method: "DELETE" });
  await refreshDashboard();
}

// `probability` is P(bullish) throughout this whole system (0-100%, 50%
// = neutral) - the SAME single number for either direction, which is
// exactly what made "SELL 39%" ambiguous (is 39% the sell confidence, or
// the leftover bullish reading?). This returns P(that specific direction)
// instead: BUY shows the raw number as-is, SELL shows its complement
// (100 - raw) - e.g. a raw 39% BUY-probability reads as "SELL 61%", each
// direction now genuinely "out of its own 100," never sharing one scale.



// Shared by the essence-only gauge and the article-based read — both
// compare a previous (direction, probability) pair against a current one.
// previous_probability/probability are remapped onto THEIR OWN direction's
// basis via directionPct(), same as everywhere else — comparing
// "confidence within the same call" only makes sense when the direction
// didn't change. A flip (e.g. previous BUY -> now SELL) isn't a numeric
// delta at all; showing "-9pp" for a full reversal would misrepresent it
// as a minor wobble instead of the call flipping entirely. Returns '' if
// there's nothing meaningful to show (identical direction+probability).

function renderCard(symbolEntry) {
  const { symbol, symbol_class, events } = symbolEntry;
  const el = document.createElement("div");
  el.className = "card";

  // Click-the-symbol-to-flip context feature (2026-08-17): "why did this
  // call change" — the back face shows the article-based prediction's
  // recorded progression (e.g. 51% indecisive -> 52% Sell) with the
  // top-3 articles that drove each step. Only meaningful once real
  // `events` exist with a `next` article_prediction to explain — the
  // fx_cross/no-events early returns below stay simple, unflippable.
  // dashboard-review-2026-09-11.md: symbol is server-validated via
  // classify_symbol() today (not currently exploitable), but escaping it
  // here anyway makes the discipline structural rather than incidental —
  // every other interpolated string in this file goes through
  // escapeHtml(), and `symbol` was the one exception.
  const safeSymbol = escapeHtml(symbol);
  let body = `<div class="card-header"><h3 class="symbol-flip-trigger" data-symbol="${safeSymbol}" title="Click for why this call changed">${safeSymbol}</h3><button class="remove-btn" data-symbol="${safeSymbol}">Remove</button></div>`;

  if (symbol_class === "fx_cross") {
    body += `<div class="not-applicable">No USD exposure for tracked events</div>`;
    el.innerHTML = body;
    el.querySelector(".remove-btn").addEventListener("click", () => removeSymbol(symbol));
    return el;
  }

  if (!events || events.length === 0) {
    body += `<div class="pending">Awaiting next tracked event</div>`;
    el.innerHTML = body;
    el.querySelector(".remove-btn").addEventListener("click", () => removeSymbol(symbol));
    return el;
  }

  const next = events[0];

  // article_prediction is the accumulator's own REAL prediction (direction
  // + probability), made BLIND from real articles BEFORE the event
  // resolves — it's independent of the essence-only score above and can
  // exist (and disagree) even while that score is still "pending". This is
  // the actual answer to "which way will this move" that the article-based
  // pipeline exists to produce — showing only the article COUNT and hiding
  // the call itself defeats the point, so this renders as a real headline,
  // not a footnote. Only present for events the accumulator has
  // independently processed (High-impact XAUUSD/US30 only, budget-capped) —
  // absent for everything else, which is expected.
  function articlePredictionHtml(pred, prevPred) {
    if (!pred) return '';
    const pct = directionPct(pred.probability, pred.direction);
    const dClass = directionClass(pred.direction);
    // Unlike the essence-only score (a fresh row most cycles),
    // scoring/backtest_accumulator.py only records a snapshot on a
    // material change — so any previous_article_prediction present here
    // is a genuine shift worth showing, never noise.
    const diffHtml = prevPred
      ? buildDiffStripHtml(prevPred.direction, prevPred.probability, pred.direction, pred.probability)
      : '';
    return `<div class="article-prediction ${dClass}">
      📰 Article-based read: <b>${directionLabel(pred.direction)} ${pct}%</b>
      <span style="font-size:12px;color:#888">(backed by ${pred.article_count} article${pred.article_count === 1 ? '' : 's'})</span>
      <div class="bull-bear-scale">${bullBearScaleSvg(pred.probability)}</div>
      ${diffHtml}
    </div>`;
  }
  // article_prediction_conflict (2026-09-04): set when co-released
  // titles (same event_time_utc, e.g. NFP + Unemployment Rate + AHE
  // from one BLS report) did NOT unanimously agree on direction for
  // this instrument -- webapp/reconciliation.py's reconcile_group()
  // requires every non-neutral co-released title to point the same way;
  // even one real dissenter is a conflict, no confidence contest
  // decides a winner. Renders as a distinct warning state, never as "no
  // data" (the plain absent-article_prediction case) and never as a
  // real directional read -- a contradictory signal is worth
  // surfacing, not hiding or silently resolving.
  function articlePredictionConflictHtml(conflict) {
    if (!conflict) return '';
    const titles = conflict.titles.map(escapeHtml).join(', ');
    return `<div class="article-prediction-conflict">
      ⚠ Conflicting signals across co-released events
      <span style="font-size:12px;color:#888">(${titles})</span>
    </div>`;
  }
  const articlePredictionLine = next.article_prediction
    ? articlePredictionHtml(next.article_prediction, next.previous_article_prediction)
    : articlePredictionConflictHtml(next.article_prediction_conflict);

  // tier1_prediction (2026-09-07): a Causation-Matrix Tier 1 causation-
  // matrix prediction for this exact occurrence, if one has been
  // manually researched and logged (webapp/reconciliation.py has no
  // role here -- this is a separate, independently-populated signal,
  // currently CPI/PPI only). Rendered directly beneath whatever the
  // sentiment line above already shows, using the SAME bullish/bearish/
  // neutral color classes -- shared color language is what makes "do
  // these two calls visually agree" readable at a glance even before
  // the explicit conflict badge below. confidence is rendered as its
  // own plain text tag (Certain/Likely/Guessing), never turned into a
  // percentage or a bar -- doing that would recreate exactly the
  // flattening Tier1Prediction's own design exists to avoid.
  //
  // tier1_sentiment_conflict (2026-09-11, fundamental-analysis-review
  // P0 #5): revises this feature's original "no agree/disagree
  // computation on the live path" constraint (2026-09-07 spec) — the
  // Sep 10 2026 PPI divergence (Tier 1 Certain/wrong vs. sentiment
  // right) shipped with zero flag anywhere, so a live badge is now real
  // product intent. BacktestReport.agreement_rate() itself stays
  // untouched (still backtest-only); this is a separate, additive
  // signal computed server-side in webapp/predictions_service.py.
  // tier1DirectionLabel (final whole-branch review, 2026-09-07 — Finding
  // 5): a Tier 1 row with confidence "Guessing" and direction "neutral"
  // means NO confident call was ever attempted (e.g. the logged CPI m/m
  // case) -- a genuinely different claim from sentiment's own
  // directionLabel('neutral') = "INDECISIVE", which means a call WAS
  // computed and it came out balanced. directionLabel() itself stays
  // untouched (shared with sentiment's rendering); this special-cases
  // just the Tier 1 line, in both places it renders.
  function tier1PredictionHtml(tier1, symbolForCard) {
    if (!tier1) return '';
    const dClass = directionClass(tier1.predicted_direction);
    return `<div class="tier1-prediction ${dClass}">
      🧮 Tier 1 (${escapeHtml(symbolForCard)}): <b>${tier1DirectionLabel(tier1)}</b>
      <span style="font-size:12px;color:#888">(${escapeHtml(tier1.confidence)})</span>
      <div style="font-size:12px;margin-top:4px">${escapeHtml(tier1.value)}</div>
      <div style="font-size:11px;color:#888;margin-top:2px">${escapeHtml(tier1.source)}</div>
    </div>`;
  }
  // tier1_sentiment_conflict (2026-09-11): a real, opposing directional
  // call from both sides for the SAME occurrence — never rendered for a
  // no-call on either side (server already excludes that case, see
  // webapp/predictions_service.py). Distinct styling from
  // article-prediction-conflict (that one's about co-released SENTIMENT
  // titles disagreeing with each other; this one's about Tier 1
  // disagreeing with sentiment itself) — same warning-badge visual
  // language, different underlying question.
  function tier1SentimentConflictHtml(conflict) {
    if (!conflict) return '';
    return `<div class="tier1-sentiment-conflict">
      ⚠ Tier 1 vs. sentiment disagree: <b>${directionLabel(conflict.tier1_direction)}</b> vs <b>${directionLabel(conflict.sentiment_direction)}</b>
    </div>`;
  }
  // tier1_confidence_downgrade (Tier 2/3 exogenous-context spec,
  // 2026-09-11): a real, detected market-wide anomaly (DXY/UST_BOND/
  // XAUUSD/US30) with no calendar event explaining it downgrades this
  // Tier 1 row's DISPLAYED confidence one tier — never its direction,
  // never the stored value (original_confidence is shown alongside so
  // nothing is silently hidden).
  function tier1ConfidenceDowngradeHtml(downgrade) {
    if (!downgrade) return '';
    const reasonText = downgrade.reason ? `: ${escapeHtml(downgrade.reason)}` : '';
    return `<div class="tier1-confidence-downgrade">
      ⚠ Confidence downgraded to <b>${escapeHtml(downgrade.displayed_confidence)}</b>
      (was ${escapeHtml(downgrade.original_confidence)}) — unexplained ${escapeHtml(downgrade.series)} move${reasonText}
    </div>`;
  }
  const tier1PredictionLine = tier1PredictionHtml(next.tier1_prediction, symbol)
    + tier1SentimentConflictHtml(next.tier1_sentiment_conflict)
    + tier1ConfidenceDowngradeHtml(next.tier1_confidence_downgrade);

  // print_prediction is the accumulator's separate "will THIS number beat
  // or miss forecast" call (scoring/print_direction.py), distinct from
  // article_prediction's price-direction call above. Absent (null) for
  // events with no PRINT_SURPRISE_LEXICON coverage or no call made yet —
  // rendered as nothing, never a fabricated placeholder.
  function printPredictionHtml(printPred) {
    if (!printPred) return '';
    const label = printPred.direction === 'higher' ? 'HIGHER than forecast'
      : printPred.direction === 'lower' ? 'LOWER than forecast' : 'IN LINE with forecast';
    const confPct = Math.round(printPred.confidence * 100);
    return `<div class="print-prediction">
      📊 Print call: likely <b>${label}</b> <span class="${confidenceColorClass(confPct)}">(${confPct}% confidence)</span>
    </div>`;
  }
  const printPredictionLine = printPredictionHtml(next.print_prediction);

  // kalshi_read is the highest-trust signal in the system (real money
  // priced on the exact event) -- absent (null) whenever no Kalshi
  // market covers this event or the read hasn't landed yet, rendered as
  // nothing, never a fabricated placeholder, same convention as every
  // other optional signal on this card.
  function kalshiReadHtml(kalshi) {
    if (!kalshi) return '';
    const label = kalshi.implied_direction === 'higher' ? 'HIGHER than forecast'
      : kalshi.implied_direction === 'lower' ? 'LOWER than forecast' : 'IN LINE with forecast';
    const pct = Math.round(kalshi.implied_probability * 100);
    return `<div class="kalshi-read">
      💰 Kalshi market: likely <b>${label}</b> <span style="font-size:12px;color:#888">(${pct}% implied, ${Math.round(kalshi.open_interest)} open interest)</span>
    </div>`;
  }
  const kalshiReadLine = kalshiReadHtml(next.kalshi_read);

  // trend_signal is a REAL structured signal (historical streak on this
  // exact event, computed by webapp/trend.py) that can — by itself, with
  // no essence score, article prediction, print call, or Kalshi read —
  // be the entire reason an event was admitted into the response (see
  // the Task-9 inclusion guard in webapp/app.py's /api/predictions
  // route). It must therefore be visible wherever a card can be shown
  // for that reason alone, not just in the resolved-score breakdown
  // panel. Absent (null) whenever too few confirmed rows exist, same
  // "absent, not fabricated" convention as every other optional signal.
  function trendSignalHtml(trend) {
    if (!trend) return '';
    const lean = trend.instrument_lean;
    const leanLabel = lean ? ` — lean: <b>${lean === 'bullish' ? 'BUY' : 'SELL'}</b>` : '';
    return `<div class="trend-signal">
      📈 Trend streak: <b>${escapeHtml(trend.direction)}</b> <span style="font-size:12px;color:#888">(strength ${trend.strength.toFixed(2)})</span>${leanLabel}
    </div>`;
  }
  const trendSignalLine = trendSignalHtml(next.trend_signal);

  // "Why this call" breakdown: every structured signal that fed the card,
  // pulled from the already-fetched `next` object -- no new network
  // request. Honest empty state when nothing fired, never silence.
  function breakdownPanelHtml(next) {
    const rows = [];
    if (next.article_prediction) {
      rows.push(`<div>📰 Article sentiment: ${directionLabel(next.article_prediction.direction)} (${next.article_prediction.article_count} articles)</div>`);
    }
    if (next.print_prediction) {
      rows.push(`<div>📊 Print-direction lexicon: ${next.print_prediction.direction} (${Math.round(next.print_prediction.confidence * 100)}% conf.)</div>`);
    }
    if (next.trend_signal) {
      const lean = next.trend_signal.instrument_lean;
      const leanLabel = lean ? ` — lean: <b>${lean === 'bullish' ? 'BUY' : 'SELL'}</b>` : '';
      rows.push(`<div>📈 Trend streak: ${next.trend_signal.direction} (strength ${next.trend_signal.strength.toFixed(2)})${leanLabel}</div>`);
    }
    if (next.kalshi_read) {
      rows.push(`<div>💰 Kalshi market: ${next.kalshi_read.implied_direction} (${Math.round(next.kalshi_read.implied_probability * 100)}% implied)</div>`);
    }
    if (rows.length === 0) {
      return '<div style="font-size:12px;color:#888">No structured signals fired for this event yet.</div>';
    }
    return rows.join('');
  }

  // Release days routinely publish several sub-metrics at the IDENTICAL
  // time (e.g. Core CPI m/m, Core CPI y/y, CPI m/m, CPI y/y all at 12:30
  // UTC — see webapp/app.py's /api/predictions sort-key comment). The
  // backend already returns every qualifying event for this symbol in
  // `events`, sorted; only `events[0]` (`next`, above) was ever rendered
  // — every other simultaneous event was computed and shipped in the API
  // response but never shown anywhere. This compact secondary list
  // surfaces the rest, one line each, deliberately NOT the full
  // article/print/trend/Kalshi breakdown `next` gets — that keeps a
  // 4-event cluster from ballooning the card, while still making the
  // other calls visible instead of silently invisible.
  // otherEventTier1MarkerHtml (final whole-branch review, 2026-09-07 —
  // Finding 1): a co-released sibling can carry its OWN logged Tier 1
  // row even when the featured event (events[0]) has none — confirmed
  // live on 2026-09-10, where "Core PPI m/m" is featured with no Tier 1
  // row, while its sibling "PPI m/m" has a real one that was otherwise
  // never rendered anywhere. Deliberately compact (icon + instrument +
  // direction label only, no source/value text) — this is a list of
  // sibling events, not a full card; tier1PredictionHtml() above stays
  // the full-detail rendering for the featured event only.
  function otherEventTier1MarkerHtml(tier1, symbolForCard) {
    if (!tier1) return '';
    const dClass = directionClass(tier1.predicted_direction);
    return `<span class="other-event-tier1 ${dClass}">🧮 Tier 1 (${escapeHtml(symbolForCard)}): <b>${tier1DirectionLabel(tier1)}</b></span>`;
  }
  // otherEventTier1ConflictMarkerHtml (2026-09-11): same reasoning as
  // otherEventTier1MarkerHtml above — the real Sep 10 2026 PPI conflict
  // is exactly this kind of sibling row (featured event "Core PPI m/m"
  // has no Tier 1 row; sibling "PPI m/m" does, and disagreed with
  // sentiment), so this badge must be visible here too, not only on a
  // featured card, or it recreates the same "only visible on the one
  // real occurrence that never happens to be featured" gap already
  // fixed once for tier1_prediction itself.
  function otherEventTier1ConflictMarkerHtml(conflict) {
    if (!conflict) return '';
    return `<span class="other-event-tier1-conflict">⚠ Tier 1 vs. sentiment disagree</span>`;
  }
  // otherEventTier1DowngradeMarkerHtml (final whole-branch review,
  // 2026-09-11 — Fix 2): same gap as otherEventTier1MarkerHtml/
  // otherEventTier1ConflictMarkerHtml above, for the SAME event shape --
  // tier1ConfidenceDowngradeHtml() was wired only into the featured
  // event's tier1PredictionLine, so a sibling event carrying its own
  // tier1_confidence_downgrade (a co-released sibling can have one even
  // when the featured event doesn't — the real Sep 10 2026 PPI/Core-PPI
  // incident already documented above is exactly this shape) never
  // rendered anywhere. Compact <span> marker, matching the sibling-row
  // convention the two functions above already use, not the full-card
  // <div> tier1ConfidenceDowngradeHtml uses for the featured event.
  function otherEventTier1DowngradeMarkerHtml(downgrade) {
    if (!downgrade) return '';
    return `<span class="other-event-tier1-downgrade">⚠ Confidence downgraded to <b>${escapeHtml(downgrade.displayed_confidence)}</b></span>`;
  }
  // otherEventEssenceArticleHtml (2026-09-11, user-reported confusion):
  // this row used to show ONE unlabeled number -- `e.direction`/
  // `e.probability`, which is webapp/scoring_service.py's essence/
  // surprise score (a pure forecast-vs-actual reflex that only exists
  // AFTER the print, computed live, never persisted) -- with nothing
  // distinguishing it from the featured card's separately-labeled
  // "Article-based read" line (the accumulator's real, pre-event,
  // article-based forecast). The two can flatly disagree (verified
  // live, Core CPI m/m 2026-09-11: essence read SELL, the article-based
  // accumulator had called BULLISH pre-event and was graded correct)
  // with no way to tell which was which. Explicit user decision: label
  // both, hide neither -- essence stays visible even where article_prediction
  // also exists, since it's real information, just previously mislabeled
  // as if it were the only number.
  function otherEventEssenceArticleHtml(e) {
    const essenceHtml = e.direction === "pending"
      ? `<span class="other-event-pending">Essence: Pending</span>`
      : (() => {
          const pct = directionPct(e.probability, e.direction);
          const dClass = directionClass(e.direction);
          return `<span class="other-event-call ${dClass}">Essence: ${directionLabel(e.direction)} ${pct}%</span>`;
        })();
    if (!e.article_prediction) return essenceHtml;
    const articlePct = directionPct(e.article_prediction.probability, e.article_prediction.direction);
    const articleClass = directionClass(e.article_prediction.direction);
    const articleHtml = `<span class="other-event-article ${articleClass}">Article: ${directionLabel(e.article_prediction.direction)} ${articlePct}%</span>`;
    return `${essenceHtml} ${articleHtml}`;
  }
  function otherEventsHtml(events, symbolForCard) {
    // Only genuinely SIMULTANEOUS events (identical event_time_utc to the
    // featured one) belong here — `events` also carries other upcoming/
    // recent events for this symbol that just happen to sort near the
    // top, which is a different concern and would make this list grow
    // unboundedly instead of reflecting an actual release-time cluster.
    const simultaneous = events.slice(1).filter((e) => e.event_time_utc === events[0].event_time_utc);
    if (simultaneous.length === 0) return '';
    const rows = simultaneous.map((e) => {
      const tier1Marker = otherEventTier1MarkerHtml(e.tier1_prediction, symbolForCard)
        + otherEventTier1ConflictMarkerHtml(e.tier1_sentiment_conflict)
        + otherEventTier1DowngradeMarkerHtml(e.tier1_confidence_downgrade);
      return `<div class="other-event-row">
        <span class="other-event-title">${escapeHtml(e.event_title)}</span>
        ${otherEventEssenceArticleHtml(e)}
        ${tier1Marker}
      </div>`;
    }).join('');
    return `<div class="other-events">
      <div class="other-events-heading">${simultaneous.length} more event${simultaneous.length === 1 ? '' : 's'} at this time</div>
      ${rows}
    </div>`;
  }
  const otherEventsLine = otherEventsHtml(events, symbol);

  // Batch 9 (2026-09-11 UI review): `events` also carries this symbol's
  // OTHER upcoming/recent tracked events — a different day/cluster, not
  // just same-instant siblings, which otherEventsHtml() above
  // deliberately excludes (see its own comment) to keep that list scoped
  // to a genuine release-time cluster. Those other events were always
  // computed and shipped in the API response but never shown anywhere —
  // confirmed live 2026-09-10: the real PPI Tier1-vs-sentiment conflict
  // had no visibility path on the Dashboard tab once CPI's cluster became
  // the featured one the next day. Bounded at OTHER_TRACKED_EVENTS_LIMIT,
  // same "don't let this grow unboundedly" reasoning otherEventsHtml()'s
  // own comment gives for staying simultaneous-only — this takes the next
  // few by the same proximity sort the backend already applies
  // (webapp/predictions_service.py's _sort_key()), not everything queued.
  const OTHER_TRACKED_EVENTS_LIMIT = 3;
  function otherTrackedEventsHtml(allEvents, symbolForCard) {
    const featuredTime = allEvents[0].event_time_utc;
    const candidates = allEvents.slice(1)
      .filter((e) => e.event_time_utc !== featuredTime);
    // Reviewer fix (2026-09-11): `candidates` is still in the backend's
    // pure temporal-proximity-to-now order (_sort_key() in
    // predictions_service.py), which only ever moves an already-resolved
    // event FARTHER from the top as time passes — it never comes back.
    // Slicing that order directly meant an aging resolved Tier1/sentiment
    // conflict (the real Sep 10 PPI case this task exists to surface)
    // would keep losing ground to newer resolved events and could go
    // permanently unseen once no longer featured, defeating the point of
    // this list. Promote conflict-flagged events to the front (preserving
    // their relative order) before bounding, so a real conflict outranks
    // recency; backend sort order is otherwise left untouched (out of
    // scope here — it also drives primary card selection elsewhere).
    const conflicts = candidates.filter((e) => e.tier1_sentiment_conflict);
    const nonConflicts = candidates.filter((e) => !e.tier1_sentiment_conflict);
    const rest = conflicts.concat(nonConflicts).slice(0, OTHER_TRACKED_EVENTS_LIMIT);
    if (rest.length === 0) return '';
    const rows = rest.map((e) => {
      const tier1Marker = otherEventTier1MarkerHtml(e.tier1_prediction, symbolForCard)
        + otherEventTier1ConflictMarkerHtml(e.tier1_sentiment_conflict)
        + otherEventTier1DowngradeMarkerHtml(e.tier1_confidence_downgrade);
      const whenLabel = formatEventDateTime(e.event_time_utc);
      return `<div class="other-event-row">
        <span class="other-event-title">${escapeHtml(e.event_title)} <span style="font-size:11px;color:#888">(${whenLabel})</span></span>
        ${otherEventEssenceArticleHtml(e)}
        ${tier1Marker}
      </div>`;
    }).join('');
    return `<div class="other-events">
      <div class="other-events-heading">Other tracked events</div>
      ${rows}
    </div>`;
  }
  const otherTrackedEventsLine = otherTrackedEventsHtml(events, symbol);

  if (next.direction === "pending") {
    // The event/when data is already in the response — showing it here
    // instead of a generic placeholder tells the user WHAT they're
    // actually waiting on, not just that something is pending.
    const hasAnySignal = articlePredictionLine || tier1PredictionLine || printPredictionLine || kalshiReadLine || trendSignalLine;
    const heading = hasAnySignal
      ? `Awaiting essence score: ${escapeHtml(next.event_title)}`
      : `Awaiting: ${escapeHtml(next.event_title)}`;
    body += `<div class="pending">${heading}<br>
      <span style="font-size:12px;color:#888">${formatEventDateTime(next.event_time_utc)}</span></div>
      ${articlePredictionLine}${tier1PredictionLine}${printPredictionLine}${kalshiReadLine}${trendSignalLine}${otherEventsLine}${otherTrackedEventsLine}`;
    // Real, live-observed case this branch must NOT skip (2026-08-17):
    // FOMC-style events whose essence-only score can never resolve
    // (title has no EVENT_SURPRISE_DIRECTION entry — see
    // webapp/scheduler.py) stay "pending" forever, yet the article-based
    // pipeline scores them independently and CAN flip (e.g. 51%
    // indecisive -> 52% Sell). Without the flip wrapper here too, the
    // "why did this change" feature would be unreachable for exactly the
    // events it matters most for. Same finalizeCardFlip() the resolved
    // branch below uses.
    finalizeCardFlip(el, body, symbol, next);
    return el;
  }

  const pct = directionPct(next.probability, next.direction);
  const dirClass = directionClass(next.direction);

  // A pending -> real transition is a first real score, not a diff — only
  // show the two-tone diff strip for real -> real changes.
  const hasPreviousChange = next.previous_probability !== null && next.previous_probability !== undefined
    && next.previous_direction !== "pending"
    && Math.abs(next.previous_probability - next.probability) > 1e-6;

  // The event just released this cycle (previous row was pending, this one
  // is a real score) — no percentage to diff against, but this is the
  // single most informative moment for a user, so call it out distinctly
  // instead of silently falling through to the plain gauge.
  const justReleased = next.previous_direction === "pending" && next.direction !== "pending";

  if (justReleased) {
    body += `<div class="just-released ${dirClass}">🎯 Just released — ${directionLabel(next.direction)} ${pct}%</div>`;
  }

  if (hasPreviousChange) {
    body += buildDiffStripHtml(next.previous_direction, next.previous_probability, next.direction, next.probability);
  }

  // Labeled explicitly (2026-09-11, user-reported confusion): this gauge
  // is webapp/scoring_service.py's essence/surprise score, distinct from
  // the separately-labeled "Article-based read" line below it -- leaving
  // this one unlabeled is what made the sibling-row version of the same
  // number look unexplained. See otherEventEssenceArticleHtml()'s comment.
  body += `<div class="gauge-row">${gaugeSvg(pct, next.direction)}
    <div><div class="gauge-label ${dirClass}">Essence: ${directionLabel(next.direction)} ${pct}%</div>
    <div style="font-size:12px;color:#888">${escapeHtml(next.event_title)}</div>
    ${articlePredictionLine}${tier1PredictionLine}${printPredictionLine}${kalshiReadLine}</div></div>
    <div class="bull-bear-scale">${bullBearScaleSvg(next.probability)}</div>`;
  body += otherEventsLine;
  body += otherTrackedEventsLine;
  body += dayStripHtml(next.event_time_utc);
  const historyToggleId = `history-${symbol}-${next.event_title.replace(/[^a-zA-Z0-9]/g, '')}`;
  body += `<div class="history-toggle">
    <button class="history-toggle-btn" data-event-title="${escapeHtml(next.event_title)}" data-target="${historyToggleId}">History ▾</button>
    <div class="history-panel" id="${historyToggleId}" style="display:none"></div>
  </div>`;

  // "Why this call" breakdown panel: a SEPARATE toggle class
  // (`.breakdown-toggle-btn`, not `.history-toggle-btn`) is deliberate --
  // el.querySelector(".history-toggle-btn") below only ever grabs the
  // FIRST match, and the History click-handler always fetches
  // /api/event_history on first expand. This panel's content is already
  // inline in `next`, so it gets its own, simpler handler that just
  // toggles display, wired independently so neither toggle can shadow or
  // misfire the other's fetch/no-fetch behavior.
  const breakdownToggleId = `breakdown-${symbol}-${next.event_title.replace(/[^a-zA-Z0-9]/g, '')}`;
  body += `<div class="history-toggle">
    <button class="breakdown-toggle-btn" data-target="${breakdownToggleId}">Why this call ▾</button>
    <div class="history-panel" id="${breakdownToggleId}" style="display:none">${breakdownPanelHtml(next)}</div>
  </div>`;

  finalizeCardFlip(el, body, symbol, next);

  const breakdownBtn = el.querySelector(".breakdown-toggle-btn");
  if (breakdownBtn) {
    breakdownBtn.addEventListener("click", () => {
      const panel = document.getElementById(breakdownBtn.dataset.target);
      panel.style.display = panel.style.display !== "none" ? "none" : "";
    });
  }

  const historyBtn = el.querySelector(".history-toggle-btn");
  if (historyBtn) {
    historyBtn.addEventListener("click", async () => {
      const panel = document.getElementById(historyBtn.dataset.target);
      if (panel.style.display !== "none") {
        panel.style.display = "none";
        return;
      }
      panel.style.display = "";
      if (panel.dataset.loaded === "true") {
        return;  // already fetched and rendered on an earlier expand — reuse it, don't re-fetch
      }
      panel.innerHTML = "Loading…";
      const resp = await fetch(`/api/event_history?title=${encodeURIComponent(historyBtn.dataset.eventTitle)}`);
      const data = await resp.json();
      panel.dataset.loaded = "true";
      if (!data.occurrences || data.occurrences.length === 0) {
        panel.innerHTML = "<div style=\"font-size:12px;color:#888\">No history recorded yet</div>";
        return;
      }
      const rows = data.occurrences.map((o) => {
        const dateLabel = new Date(o.event_time_utc).toLocaleDateString(undefined, { year: "numeric", month: "short" });
        const surpriseLabel = o.surprise_direction
          ? `(${escapeHtml(o.surprise_direction.replace("_", "-"))})`
          : (o.actual ? "(untracked)" : "(pending)");
        return `<div>${dateLabel}: forecast ${escapeHtml(o.forecast ?? "—")}, previous ${escapeHtml(o.previous ?? "—")}, actual ${escapeHtml(o.actual ?? "—")} ${surpriseLabel}</div>`;
      }).join("");
      panel.innerHTML = `${rows}<div style="margin-top:4px;font-weight:bold">→ ${escapeHtml(data.trend_summary)}</div>`;
    });
  }

  return el;
}

// Renders one progression entry — a recorded article-based snapshot plus
// (if any) the top-3 articles that drove it. Weight_pct/usd_sentiment
// come straight from scoring/backtest_accumulator.py's
// _build_top_contributions(), computed once at scoring time and stored
// alongside that exact prediction — never recomputed here.
function articleProgressionEntryHtml(entry, isLatest) {
  const dClass = directionClass(entry.direction);
  const pct = directionPct(entry.probability, entry.direction);
  const when = new Date(entry.scored_at_utc).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  const contribsHtml = (entry.top_contributions || []).map((c) => {
    const leanClass = c.usd_sentiment > 0 ? "bullish" : c.usd_sentiment < 0 ? "bearish" : "neutral";
    return `<div class="progression-article">
      <a href="${escapeHtml(c.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(c.title)}</a>
      <span class="progression-article-meta ${leanClass}">${escapeHtml(c.source)} · ${c.weight_pct}% weight</span>
    </div>`;
  }).join("");
  return `<div class="progression-entry ${isLatest ? "progression-entry-latest" : ""}">
    <div class="progression-entry-head">
      <span class="gauge-label ${dClass}">${directionLabel(entry.direction)} ${pct}%</span>
      <span class="progression-entry-when">${when} · ${entry.article_count} articles</span>
    </div>
    ${contribsHtml || '<div class="low-signal-warning">⚠ No individual article stood out — this read came from broad, low-signal coverage, not a genuinely on-topic signal.</div>'}
  </div>`;
}

// Wraps `body` (whatever this card's front-face content is — resolved
// score OR the "pending" branch, both call this) in the flip structure
// and wires the click-to-flip interaction. Extracted as its own function
// (2026-08-17) specifically because the "pending" branch used to return
// early WITHOUT this wrapper — meaning FOMC-style events, whose
// essence-only score can never resolve, could never be flipped even
// though their article-based read is real and does change over time.
// Every branch that reaches a `next` event must call this, not just the
// resolved-score path.
function finalizeCardFlip(el, body, symbol, next) {
  const safeSymbol = escapeHtml(symbol);
  const backBodyId = `card-back-${safeSymbol}-${next.event_title.replace(/[^a-zA-Z0-9]/g, '')}`;
  const backBody = `<div class="card-header">
      <h3>${safeSymbol} — why this changed</h3>
      <button class="flip-back-btn" data-symbol="${safeSymbol}">✕ Back</button>
    </div>
    <div class="article-progression" id="${backBodyId}" data-event-title="${escapeHtml(next.event_title)}" data-loaded="false">Loading…</div>`;

  el.classList.add("card-has-flip");
  el.innerHTML = `<div class="card-flip-inner">
    <div class="card-flip-front">${body}</div>
    <div class="card-flip-back">${backBody}</div>
  </div>`;
  el.querySelector(".remove-btn").addEventListener("click", () => removeSymbol(symbol));
  wireCardFlip(el, symbol);
}

// Click-the-symbol flip interaction. Lazily fetches the article-based
// progression on first flip only (data-loaded guard, same pattern as the
// History ▾ toggle above) — flipping back and forth afterward is free.
function wireCardFlip(el, symbol) {
  const trigger = el.querySelector(".symbol-flip-trigger");
  const backBtn = el.querySelector(".flip-back-btn");
  if (!trigger) return;

  async function flipTo(show) {
    if (show) {
      el.classList.add("flipped");
    } else {
      el.classList.remove("flipped");
      return;
    }
    const panel = el.querySelector(".article-progression");
    if (!panel || panel.dataset.loaded === "true") return;
    const eventTitle = panel.dataset.eventTitle;
    const resp = await fetch(`/api/predictions/${symbol}/article_history?event_title=${encodeURIComponent(eventTitle)}`);
    const data = await resp.json();
    panel.dataset.loaded = "true";
    const progression = data.progression || [];
    if (progression.length === 0) {
      panel.innerHTML = "<div style=\"font-size:12px;color:#888\">No article-based read recorded for this event yet.</div>";
      return;
    }
    panel.innerHTML = progression.map((entry, i) => articleProgressionEntryHtml(entry, i === 0)).join("");
  }

  trigger.addEventListener("click", () => flipTo(!el.classList.contains("flipped")));
  if (backBtn) {
    backBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      flipTo(false);
    });
  }
}

async function refreshDashboard() {
  // dashboard-review-2026-09-11.md: a transient network blip here used to
  // throw an unhandled rejection out of this function and silently freeze
  // the dashboard on stale data every subsequent poll, with no visible
  // sign anything was wrong (unlike the Add-Symbol form, which already
  // checked resp.ok). Caught here instead: leaves whatever's already
  // rendered in place (never wipes cardsEl on a failed poll) and surfaces
  // a visible, distinct-from-"no data yet" notice. Cleared on the next
  // successful poll, same as every other transient indicator in this file.
  let data;
  try {
    const resp = await fetch("/api/predictions");
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    data = await resp.json();
  } catch (err) {
    console.error("refreshDashboard: poll failed", err);
    predictionsPollErrorEl.textContent = "Couldn't reach the server — showing the last data received.";
    predictionsPollErrorEl.style.display = "";
    return;
  }
  predictionsPollErrorEl.style.display = "none";

  // "error" here means the background loop (webapp/scheduler.py) hasn't
  // completed its first successful fetch yet — not "a live request just
  // failed," since no route ever fetches live anymore. Once a snapshot
  // exists, it's shown as current until the background loop persists new
  // data — no per-request staleness, so this notice only ever appears
  // before the very first fetch (fresh install / recent restart).
  if (data.error) {
    predictionsStaleNoticeEl.textContent = data.error;
    predictionsStaleNoticeEl.style.display = "";
  } else {
    predictionsStaleNoticeEl.textContent = "";
    predictionsStaleNoticeEl.style.display = "none";
  }

  renderAccumulatorStaleness(data.accumulator_staleness_seconds);

  // Capture which History panels are currently expanded so a fresh
  // re-render below (which rebuilds every card from scratch, wiping
  // panel state and the data-loaded fetch cache) can restore them
  // afterward instead of silently collapsing them every 60s.
  const expandedHistoryIds = Array.from(cardsEl.querySelectorAll('.history-panel'))
    .filter((p) => p.style.display !== 'none')
    .map((p) => p.id);

  // Same idea for the flip-card feature — which symbols are currently
  // flipped, so a fresh re-render (which rebuilds every card, wiping
  // .flipped and the article_history fetch cache) can restore them
  // instead of silently flipping everything back to front every 60s.
  const flippedSymbols = Array.from(cardsEl.querySelectorAll('.card.flipped'))
    .map((c) => c.querySelector('.symbol-flip-trigger')?.dataset.symbol)
    .filter(Boolean);

  cardsEl.innerHTML = "";
  (data.predictions || []).forEach((entry) => cardsEl.appendChild(renderCard(entry)));

  // Re-expand (and re-fetch, since event_history may genuinely have
  // changed) any panel that survives under the same deterministic id —
  // i.e. this card's `next` event is still the same symbol+title.
  expandedHistoryIds.forEach((id) => {
    if (!document.getElementById(id)) return;  // that event is no longer this card's `next` — nothing to restore
    const btn = document.querySelector(`[data-target="${id}"]`);
    if (btn) btn.click();
  });

  flippedSymbols.forEach((symbol) => {
    const trigger = document.querySelector(`.symbol-flip-trigger[data-symbol="${symbol}"]`);
    if (trigger) trigger.click();  // re-fetches article_history fresh — a material change while flipped should show up
  });
}

async function refreshCalendar() {
  // Same reasoning as refreshDashboard()'s guard — a transient network
  // blip must not throw an unhandled rejection and silently freeze this
  // tab on stale data.
  let data;
  try {
    const resp = await fetch("/api/calendar");
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    data = await resp.json();
  } catch (err) {
    console.error("refreshCalendar: poll failed", err);
    calendarPollErrorEl.textContent = "Couldn't reach the server — showing the last data received.";
    calendarPollErrorEl.style.display = "";
    return;
  }
  calendarPollErrorEl.style.display = "none";
  const events = data.events || [];
  renderFeedStaleness(data.feed_staleness_seconds);

  if (data.error) {
    calendarStaleNoticeEl.textContent = data.error;
    calendarStaleNoticeEl.style.display = "";
  } else {
    calendarStaleNoticeEl.textContent = "";
    calendarStaleNoticeEl.style.display = "none";
  }

  // Macro view (docs/macro-calendar-design-2026-08-16.md): FRED-sourced
  // month-ahead dates for whatever FF's own "thisweek" feed hasn't
  // populated yet — fetched separately so a failure here never blocks
  // the FF-backed grid above from rendering. Only entries with
  // estimated===true are actually NEW information (a false one is
  // already a duplicate of something `events` already has, per
  // /api/calendar/monthahead's own dedup rule).
  let estimatedOnlyEvents = [];
  try {
    const monthAheadResp = await fetch("/api/calendar/monthahead");
    const monthAheadData = await monthAheadResp.json();
    estimatedOnlyEvents = (monthAheadData.events || []).filter((e) => e.estimated);
  } catch {
    estimatedOnlyEvents = [];  // macro view is a nice-to-have overlay — a fetch failure here must not break the calendar tab
  }

  const now = new Date();
  const upcoming = events
    .map((e) => new Date(e.event_time_utc))
    .filter((d) => d >= now)
    .sort((a, b) => a - b);
  const nearestUpcomingDateStr = upcoming.length > 0 ? upcoming[0].toDateString() : null;

  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth();
  const firstDay = new Date(year, month, 1);
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const startWeekday = firstDay.getDay();

  const eventsByDate = {};
  events.forEach((e) => {
    const d = new Date(e.event_time_utc).toDateString();
    (eventsByDate[d] = eventsByDate[d] || []).push(e);
  });
  const estimatedByDate = {};
  estimatedOnlyEvents.forEach((e) => {
    const d = new Date(e.event_time_utc).toDateString();
    (estimatedByDate[d] = estimatedByDate[d] || []).push(e);
  });

  let cells = "";
  for (let i = 0; i < startWeekday; i++) cells += `<div class="cal-cell"></div>`;
  for (let day = 1; day <= daysInMonth; day++) {
    const cellDate = new Date(year, month, day);
    const isToday = cellDate.toDateString() === today.toDateString();
    const isNearestUpcoming = cellDate.toDateString() === nearestUpcomingDateStr;
    const dayEvents = eventsByDate[cellDate.toDateString()] || [];
    const dayEstimated = estimatedByDate[cellDate.toDateString()] || [];
    const dots = dayEvents.map((e) => {
      const impactClass = e.impact === 'High' ? 'impact-high' : e.impact === 'Medium' ? 'impact-medium' : 'impact-low';
      return `<span class="cal-dot ${impactClass}" title="${escapeHtml(e.title)} (${escapeHtml(e.impact)})"></span>`;
    }).join("");
    // Estimated (FRED month-ahead, not FF-confirmed) dots — hollow style,
    // see .cal-dot-estimated in style.css. Rendered even when the day
    // already has real FF dots, in case a DIFFERENT title on the same
    // date is still macro-only (e.g. CPI confirmed by FF, PPI not yet).
    const estimatedDots = dayEstimated.map((e) =>
      `<span class="cal-dot cal-dot-estimated" title="${escapeHtml(e.title)} (estimated — not yet confirmed by Forex Factory)"></span>`
    ).join("");
    const classes = ["cal-cell"];
    if (isToday) classes.push("today");
    if (isNearestUpcoming) classes.push("nearest-upcoming");
    if (dayEvents.length === 0 && dayEstimated.length > 0) classes.push("has-estimated-only");
    cells += `<div class="${classes.join(" ")}" data-date="${toIsoDateLocal(cellDate)}">${day}<br>${dots}${estimatedDots}</div>`;
  }
  calendarGridEl.innerHTML = cells;
  calendarGridEl.querySelectorAll(".cal-cell[data-date]").forEach((cellEl) => {
    cellEl.addEventListener("click", () => showDatePanel(cellEl.dataset.date));
  });

  // Default view: nearest-upcoming date's own events + tracked-symbol
  // calls, via the same click-to-inspect panel (richer than a flat dump —
  // per-symbol essence/article/print calls, not just title+impact). Falls
  // back to today when nothing is upcoming, so the panel is never left
  // blank on initial load. Click any other cell to inspect it instead.
  //
  // refreshCalendar() re-runs every POLL_INTERVAL_MS — without this, each
  // poll would silently snap the panel back to the default date, discarding
  // whatever the user clicked, and would also re-open a panel the user just
  // closed. selectedCalendarDateStr/calendarPanelClosed make the choice
  // sticky across polls, same idea as expandedHistoryIds for dashboard cards.
  if (!calendarPanelClosed) {
    const defaultDateStr = upcoming.length > 0 ? toIsoDateLocal(upcoming[0]) : toIsoDateLocal(today);
    await showDatePanel(selectedCalendarDateStr || defaultDateStr);
  }
}

let selectedCalendarDateStr = null;
let calendarPanelClosed = false;

async function showDatePanel(dateStr) {
  selectedCalendarDateStr = dateStr;
  calendarPanelClosed = false;
  const panel = document.getElementById("calendar-date-panel");
  const title = document.getElementById("calendar-date-panel-title");
  const body = document.getElementById("calendar-date-panel-body");
  title.textContent = new Date(`${dateStr}T00:00:00`).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
  body.innerHTML = "Loading…";
  panel.style.display = "";

  const resp = await fetch(`/api/calendar/date/${dateStr}`);
  const data = await resp.json();
  if (!data.events || data.events.length === 0) {
    body.innerHTML = "<div style=\"color:#888\">No tracked events on this date.</div>";
    return;
  }
  body.innerHTML = data.events.map((e) => {
    const callsHtml = Object.entries(e.calls || {}).map(([symbol, call]) => {
      if (!call) return `<div class="date-panel-call">${escapeHtml(symbol)}: <span style="color:#888">no call recorded</span></div>`;
      // `call.direction`/`call.probability` is the essence-only score
      // (same as the dashboard card's gauge). `article_prediction` and
      // `print_prediction` are independent real calls from the other two
      // pipelines (Task 12's route) — surfaced as sub-lines rather than
      // dropped, same emoji convention as the dashboard cards, so this
      // panel doesn't hide detail the API already computed.
      // "pending" is a real PredictionRun row (scored, but not yet
      // bullish/bearish) — not the same as call.direction being absent.
      // Treated as "no essence score yet" here too, same as the dashboard
      // card's explicit `next.direction === "pending"` branch, so this
      // doesn't mislabel it "INDECISIVE 0%" as if it were a real neutral call.
      const essenceLine = call.direction != null && call.direction !== "pending"
        ? `<b>${directionLabel(call.direction)} ${directionPct(call.probability, call.direction)}%</b>`
        : `<span style="color:#888">no essence score yet</span>`;
      const articleLine = call.article_prediction
        ? `<div style="font-size:12px;color:#666">📰 ${directionLabel(call.article_prediction.direction)} ${directionPct(call.article_prediction.probability, call.article_prediction.direction)}% (${call.article_prediction.article_count} articles)</div>`
        : "";
      const printLine = call.print_prediction
        ? (() => {
            const pct = Math.round(call.print_prediction.confidence * 100);
            return `<div style="font-size:12px">📊 ${escapeHtml(call.print_prediction.direction)} <span class="${confidenceColorClass(pct)}">(${pct}% conf.)</span></div>`;
          })()
        : "";
      return `<div class="date-panel-call">${escapeHtml(symbol)}: ${essenceLine}${articleLine}${printLine}</div>`;
    }).join("");
    // Macro-only rows (docs/macro-calendar-design-2026-08-16.md) carry no
    // impact/forecast/previous/actual and no per-symbol calls — they're a
    // FRED-sourced date estimate, not a scored occurrence. estimated===true
    // also covers a confirmed-but-not-yet-FF-superseded macro row (rare —
    // FF normally supersedes it in the SAME cycle that confirms it).
    if (e.estimated) {
      return `<div class="date-panel-event">
        <b>${escapeHtml(e.title)}</b> <span class="estimated-badge" title="FRED month-ahead estimate — not yet confirmed by Forex Factory's own feed">ESTIMATED</span><br>
        <span style="font-size:12px;color:#888">Exact time not yet confirmed — Forex Factory hasn't reached this occurrence's week yet.</span>
      </div>`;
    }
    return `<div class="date-panel-event">
      <b>${escapeHtml(e.title)}</b> (${escapeHtml(e.impact ?? "")})<br>
      <span style="font-size:12px;color:#888">forecast ${escapeHtml(e.forecast ?? "—")}, previous ${escapeHtml(e.previous ?? "—")}, actual ${escapeHtml(e.actual ?? "—")}</span>
      ${callsHtml}
    </div>`;
  }).join("");
}

document.getElementById("calendar-date-panel-close").addEventListener("click", () => {
  calendarPanelClosed = true;
  document.getElementById("calendar-date-panel").style.display = "none";
});

async function refreshAll() {
  await refreshDashboard();
  await refreshCalendar();
}

refreshAll();
setInterval(refreshAll, POLL_INTERVAL_MS);

let historyLoaded = false;
// Batch 10: the whole table is small (~35 rows per the live review), so
// filter/sort stay entirely client-side against one fetched snapshot —
// no server round trip per filter change. allHistoryRows is the fetched,
// unfiltered set; renderHistoryTable() below always derives its view from
// it plus the current filter/sort state, never mutates it.
let allHistoryRows = [];
const historySort = { column: "event_time_utc", ascending: false };  // most recent first, matches the API's own default order

async function loadHistoryIfNeeded() {
  if (historyLoaded) return;  // fetched once per page load, not on the dashboard's poll cycle
  historyLoaded = true;
  const resp = await fetch("/api/history");
  const data = await resp.json();
  allHistoryRows = data.rows || [];
  _populateHistoryFilterOptions(allHistoryRows);
  renderHistoryTable(_filterAndSortHistoryRows(allHistoryRows));
  await loadHistoryStats();
}

function _populateHistoryFilterOptions(rows) {
  const titleSelect = document.getElementById("history-filter-title");
  const instrumentSelect = document.getElementById("history-filter-instrument");
  const titles = [...new Set(rows.map((r) => r.event_title))].sort();
  const instruments = [...new Set(rows.map((r) => r.instrument).filter(Boolean))].sort();
  for (const t of titles) {
    const opt = document.createElement("option");
    opt.value = t; opt.textContent = t;
    titleSelect.appendChild(opt);
  }
  for (const i of instruments) {
    const opt = document.createElement("option");
    opt.value = i; opt.textContent = i;
    instrumentSelect.appendChild(opt);
  }
}

// A row's "graded" outcome for filtering purposes — 'Correct'/'Wrong' map
// directly from the real backend outcome; every no-call/awaiting/not-
// comparable state (r.outcome === null) collapses to one 'no_call' filter
// value, since the History-tab controls this session added group them as
// one filter option (see index.html's #history-filter-outcome) rather
// than exposing the 3 separate unjudged_reason values as 3 more dropdown
// entries — the underlying data keeps the distinction (still shown per-row
// via unjudged_reason), only the FILTER groups them.
function _historyOutcomeFilterValue(row) {
  if (row.outcome === "Confirmed") return "Correct";
  if (row.outcome === "Missed") return "Wrong";
  return "no_call";
}

function _filterAndSortHistoryRows(rows) {
  const titleFilter = document.getElementById("history-filter-title").value;
  const instrumentFilter = document.getElementById("history-filter-instrument").value;
  const outcomeFilter = document.getElementById("history-filter-outcome").value;

  let filtered = rows.filter((r) =>
    (!titleFilter || r.event_title === titleFilter)
    && (!instrumentFilter || r.instrument === instrumentFilter)
    && (!outcomeFilter || _historyOutcomeFilterValue(r) === outcomeFilter)
  );

  const { column, ascending } = historySort;
  const direction = ascending ? 1 : -1;
  filtered = filtered.slice().sort((a, b) => {
    let av, bv;
    if (column === "event_time_utc") { av = a.event_time_utc; bv = b.event_time_utc; }
    else if (column === "event_title") { av = a.event_title; bv = b.event_title; }
    else if (column === "instrument") { av = a.instrument ?? ""; bv = b.instrument ?? ""; }
    else if (column === "ne_confidence") { av = a.ne_confidence; bv = b.ne_confidence; }
    else { av = a.event_time_utc; bv = b.event_time_utc; }
    if (av < bv) return -1 * direction;
    if (av > bv) return 1 * direction;
    return 0;
  });
  return filtered;
}

function _applyHistoryFilterAndSort() {
  renderHistoryTable(_filterAndSortHistoryRows(allHistoryRows));
}

for (const id of ["history-filter-title", "history-filter-instrument", "history-filter-outcome"]) {
  document.getElementById(id).addEventListener("change", _applyHistoryFilterAndSort);
}

// Column-header click-to-sort — toggles ascending/descending on repeat
// clicks of the same column, defaults to ascending on a new column. A
// small ▲/▼ arrow on the active column's own header is the only visual
// indicator (no separate sort-state UI needed).
const HISTORY_SORTABLE_COLUMNS = {
  "history-th-event": "event_title",
  "history-th-instrument": "instrument",
  "history-th-confidence": "ne_confidence",
};
for (const [id, column] of Object.entries(HISTORY_SORTABLE_COLUMNS)) {
  const th = document.getElementById(id);
  if (!th) continue;
  th.style.cursor = "pointer";
  th.addEventListener("click", () => {
    if (historySort.column === column) {
      historySort.ascending = !historySort.ascending;
    } else {
      historySort.column = column;
      historySort.ascending = true;
    }
    _renderHistorySortIndicators();
    _applyHistoryFilterAndSort();
  });
}

function _renderHistorySortIndicators() {
  for (const [id, column] of Object.entries(HISTORY_SORTABLE_COLUMNS)) {
    const th = document.getElementById(id);
    if (!th) continue;
    const base = th.dataset.label || th.textContent.replace(/ [▲▼]$/, "");
    th.dataset.label = base;
    th.textContent = column === historySort.column ? `${base} ${historySort.ascending ? "▲" : "▼"}` : base;
  }
}

function renderHistoryStats(stats) {
  const container = document.getElementById("history-stats");
  const overall = stats.overall;
  // Batch 9 final-review Minor finding, fixed here: an empty DB rendered
  // a placeholder ("Overall: 0 calls made, 0 no-call" + an empty
  // collapsed detail) instead of nothing — a real conflict with this
  // project's own "render nothing, not a placeholder, when absent"
  // convention every other optional signal on this dashboard follows.
  if (overall.correct + overall.wrong + overall.no_call === 0) {
    container.innerHTML = "";
    return;
  }
  const overallLabel = overall.accuracy === null
    ? `${overall.correct + overall.wrong} calls made, ${overall.no_call} no-call`
    : `${overall.correct}/${overall.correct + overall.wrong} correct (${Math.round(overall.accuracy * 100)}%), ${overall.no_call} no-call`;

  // Batch 9 final-review Minor finding, fixed here: this was re-sorted
  // client-side on top of an already server-sorted response
  // (webapp/app.py's /api/history/stats sorts by_event_title itself) —
  // redundant, and Python's sorted() vs JS's default Array.sort() can
  // disagree on non-ASCII collation. Object.keys() preserves a JSON
  // object's own (server-decided) key order for string keys, so this
  // just trusts it instead of re-deriving it.
  const titles = Object.keys(stats.by_event_title);
  const rows = titles.map((title) => {
    const s = stats.by_event_title[title];
    const label = s.accuracy === null
      ? `${s.no_call} no-call, 0 calls made`
      : `${s.correct}/${s.correct + s.wrong} (${Math.round(s.accuracy * 100)}%)${s.no_call ? `, ${s.no_call} no-call` : ""}`;
    return `<tr><td>${escapeHtml(title)}</td><td>${label}</td></tr>`;
  }).join("");

  const windowLabel = typeof stats.window_limit === "number" ? ` (last ${stats.window_limit} events)` : "";

  container.innerHTML = `
    <div id="history-stats-overall"><b>Overall${escapeHtml(windowLabel)}:</b> ${overallLabel}</div>
    <details id="history-stats-detail">
      <summary>By event type</summary>
      <table id="history-stats-table"><tbody>${rows}</tbody></table>
    </details>`;
}

// Batch 9 final-review Minor finding, fixed here: renamed from
// loadHistoryStatsIfNeeded — that name promised the same
// historyLoaded-style idempotence guard loadHistoryIfNeeded() actually
// implements; this function has none of its own (only idempotent
// because its sole caller already sits behind that guard). Also adds
// the try/catch + resp.ok check refreshDashboard() already established
// — a failure here used to throw an unhandled rejection and never
// retry (since historyLoaded is already true by the time this runs).
async function loadHistoryStats() {
  try {
    const resp = await fetch("/api/history/stats");
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    renderHistoryStats(await resp.json());
  } catch (err) {
    console.error("loadHistoryStats: fetch failed", err);
  }
}

function renderHistoryTable(rows) {
  const table = document.getElementById("history-table");
  const emptyNotice = document.getElementById("history-empty-notice");
  const tbody = document.getElementById("history-tbody");

  if (rows.length === 0) {
    table.style.display = "none";
    emptyNotice.style.display = "";
    return;
  }

  emptyNotice.style.display = "none";
  table.style.display = "";
  tbody.innerHTML = rows.map((r, idx) => {
    const dateLabel = new Date(r.event_time_utc).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
    const actualCell = r.unchanged_vs_previous
      ? `${escapeHtml(r.actual ?? "—")} <span style="color:#888;font-size:11px">(= prev)</span>`
      : escapeHtml(r.actual ?? "—");
    const sourceBadge = r.source === "seeded"
      ? ' <span style="color:#888;font-size:11px;font-weight:normal">(seeded)</span>'
      : r.source === "live_web_fallback"
      ? ' <span style="color:#888;font-size:11px;font-weight:normal">(web-sourced)</span>'
      : r.source === "cloud_web_fallback"
      ? ' <span style="color:#888;font-size:11px;font-weight:normal">(cloud-researched)</span>'
      : "";
    // Numeric rows use higher/lower/in_line; text-event fallback rows use bullish/bearish/neutral.
    const predictionLabel = { higher: "Higher", lower: "Lower", in_line: "In-line", bullish: "Bullish", bearish: "Bearish", neutral: "Neutral" }[r.ne_prediction] || escapeHtml(r.ne_prediction);
    const tier1ConflictBadge = r.tier1_conflict
      ? ` <span style="color:#ef6c00;font-size:11px;font-weight:bold">⚠ Tier 1: ${escapeHtml(r.tier1_conflict.tier1_direction)}</span>`
      : "";
    // Batch 10 (dashboard-review-2026-09-11.md live UI walkthrough):
    // "Confirmed" read ambiguously as "the actual print is confirmed"
    // rather than "the prediction was correct" — display-only relabel,
    // the backend outcome value ('Confirmed'/'Missed') is untouched, it's
    // a real data contract scoring/comparison logic already depends on.
    // See #history-legend for what each of the 5 states means.
    const outcomeLabel = r.outcome === null
      ? `<span style="color:#888">${
          r.unjudged_reason === "pending" ? "Awaiting confirmation"
          : r.unjudged_reason === "unknown_surprise" ? "Actual not comparable"
          : "No strong call"
        }</span>`
      : r.outcome === "Confirmed"
        ? '<span style="color:#2e7d32;font-weight:bold">Correct</span>'
        : '<span style="color:#c62828;font-weight:bold">Wrong</span>';
    // Batch 10: "drill-down exists only for pending Dashboard cards, not
    // resolved History rows — exactly when you'd want to see which
    // articles drove a wrong call, the UI removes that view." Reuses the
    // SAME endpoint and rendering (articleProgressionEntryHtml) the
    // Dashboard flip-card already fetches — only a symbol (instrument) to
    // key it, which a print-call-backed numeric row (no specific
    // instrument, by design — see webapp/history.py's HistoryRow
    // docstring) doesn't have, so the toggle is simply absent there
    // rather than fetching against a symbol that isn't real.
    const drillId = `history-drill-${idx}`;
    const drillToggle = r.instrument
      ? ` <button class="history-drill-toggle-btn" data-target="${drillId}" data-event-title="${escapeHtml(r.event_title)}" data-instrument="${escapeHtml(r.instrument)}" style="font-size:11px">why ▾</button>`
      : "";
    return `<tr>
      <td>${escapeHtml(r.event_title)}${sourceBadge}<br><span style="font-size:11px;color:#888">${dateLabel}</span>${drillToggle}</td>
      <td>${escapeHtml(r.instrument ?? "")}</td>
      <td>${escapeHtml(r.previous ?? "—")}</td>
      <td>${escapeHtml(r.forecast ?? "—")}</td>
      <td>${actualCell}</td>
      <td>${predictionLabel} <span class="${confidenceColorClass(Math.round(r.ne_confidence * 100))}" style="font-size:11px">(${Math.round(r.ne_confidence * 100)}% conf.)</span>${tier1ConflictBadge}</td>
      <td>${outcomeLabel}</td>
    </tr>${r.instrument ? `<tr class="history-drill-row" id="${drillId}" style="display:none"><td colspan="7"><div class="history-panel" data-loaded="false">Loading…</div></td></tr>` : ""}`;
  }).join("");
}

// Delegated (attached once, not per-render, since renderHistoryTable()
// rebuilds #history-tbody's innerHTML on every filter/sort change) — an
// expanded panel collapses on the next re-render, same as the rest of
// this table's state; acceptable here since filter/sort is a deliberate
// user action, not the silent 60s background poll refreshDashboard()
// guards against.
document.getElementById("history-tbody").addEventListener("click", async (e) => {
  const btn = e.target.closest(".history-drill-toggle-btn");
  if (!btn) return;
  const row = document.getElementById(btn.dataset.target);
  const panel = row.querySelector(".history-panel");
  if (row.style.display !== "none") {
    row.style.display = "none";
    return;
  }
  row.style.display = "";
  if (panel.dataset.loaded === "true") return;
  const resp = await fetch(`/api/predictions/${btn.dataset.instrument}/article_history?event_title=${encodeURIComponent(btn.dataset.eventTitle)}`);
  const data = await resp.json();
  panel.dataset.loaded = "true";
  const progression = data.progression || [];
  panel.innerHTML = progression.length === 0
    ? "<div style=\"font-size:12px;color:#888\">No article-based read recorded for this event yet.</div>"
    : progression.map((entry, i) => articleProgressionEntryHtml(entry, i === 0)).join("");
});
