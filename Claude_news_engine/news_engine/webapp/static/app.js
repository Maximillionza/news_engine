const POLL_INTERVAL_MS = 60_000;

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

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

function formatEventDateTime(eventTimeUtc) {
  return new Date(eventTimeUtc).toLocaleString();
}

// Local-calendar-date ISO string (YYYY-MM-DD). NOT Date.toISOString() —
// that converts to UTC first, which would shift the date for any
// non-UTC+0 local timezone (e.g. SAST/UTC+2 local midnight becomes the
// previous day at 22:00 UTC) and desync the cell's data-date from the
// cell's own displayed day number.
function toIsoDateLocal(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

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

function directionLabel(direction) {
  if (direction === "bullish") return "BUY";
  if (direction === "bearish") return "SELL";
  return "INDECISIVE";
}

function directionClass(direction) {
  if (direction === "bullish") return "bullish";
  if (direction === "bearish") return "bearish";
  return "neutral";
}

// `probability` is P(bullish) throughout this whole system (0-100%, 50%
// = neutral) - the SAME single number for either direction, which is
// exactly what made "SELL 39%" ambiguous (is 39% the sell confidence, or
// the leftover bullish reading?). This returns P(that specific direction)
// instead: BUY shows the raw number as-is, SELL shows its complement
// (100 - raw) - e.g. a raw 39% BUY-probability reads as "SELL 61%", each
// direction now genuinely "out of its own 100," never sharing one scale.
function directionPct(probability, direction) {
  const raw = Math.round(probability * 100);
  return direction === "bearish" ? 100 - raw : raw;
}

function gaugeSvg(pct, direction) {
  // `pct` is already the per-direction display percentage (directionPct())
  // — the arc fills to match the number shown, not the raw shared-scale
  // probability, so a "SELL 61%" gauge visually reads as 61% filled, not 39%.
  const color = direction === "bullish" ? "#2e7d32" : direction === "bearish" ? "#c62828" : "#888";
  const circumference = 2 * Math.PI * 26;
  const filled = (pct / 100) * circumference;
  return `
    <svg width="70" height="70" viewBox="0 0 70 70">
      <circle cx="35" cy="35" r="26" fill="none" stroke="#eee" stroke-width="7"/>
      <circle cx="35" cy="35" r="26" fill="none" stroke="${color}" stroke-width="7"
        stroke-dasharray="${filled} ${circumference}" stroke-linecap="round"
        transform="rotate(-90 35 35)"/>
      <text x="35" y="39" text-anchor="middle" font-size="13" font-weight="bold">${pct}%</text>
    </svg>`;
}

let _bullBearScaleCounter = 0;

// Bear(red)<->Bull(green) horizontal scale with a sliding indicator at
// `probability` (0.0-1.0) — where the article-based read sits relative to
// full-bear/full-bull, not "confidence in the shown direction." Directly
// addresses the ambiguity of a bare "SELL 39%" label: visually, 39% is
// obviously a mild lean toward the red end, not a strong one, without
// requiring the reader to do (100 - 39)% math in their head.
function bullBearScaleSvg(probability) {
  const id = `bbgrad-${_bullBearScaleCounter++}`;
  const pct = Math.max(0, Math.min(100, probability * 100));
  const trackX = 4, trackWidth = 172;
  const indicatorX = trackX + (pct / 100) * trackWidth;
  return `
    <svg width="180" height="34" viewBox="0 0 180 34">
      <defs>
        <linearGradient id="${id}" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#c62828"/>
          <stop offset="50%" stop-color="#ddd"/>
          <stop offset="100%" stop-color="#2e7d32"/>
        </linearGradient>
      </defs>
      <rect x="${trackX}" y="12" width="${trackWidth}" height="7" rx="3.5" fill="url(#${id})"/>
      <line x1="90" y1="8" x2="90" y2="23" stroke="#999" stroke-width="1"/>
      <circle cx="${indicatorX}" cy="15.5" r="6.5" fill="#222" stroke="#fff" stroke-width="2"/>
      <text x="${trackX}" y="33" font-size="9" fill="#c62828" font-weight="bold">BEAR</text>
      <text x="${trackX + trackWidth}" y="33" font-size="9" fill="#2e7d32" font-weight="bold" text-anchor="end">BULL</text>
    </svg>`;
}

// Shared by the essence-only gauge and the article-based read — both
// compare a previous (direction, probability) pair against a current one.
// previous_probability/probability are remapped onto THEIR OWN direction's
// basis via directionPct(), same as everywhere else — comparing
// "confidence within the same call" only makes sense when the direction
// didn't change. A flip (e.g. previous BUY -> now SELL) isn't a numeric
// delta at all; showing "-9pp" for a full reversal would misrepresent it
// as a minor wobble instead of the call flipping entirely. Returns '' if
// there's nothing meaningful to show (identical direction+probability).
function buildDiffStripHtml(prevDirection, prevProbability, currDirection, currProbability) {
  const prevPct = directionPct(prevProbability, prevDirection);
  const currPct = directionPct(currProbability, currDirection);

  if (prevDirection !== currDirection) {
    return `<div class="diff-strip reversed">
      <div>↔ Reversed: was <b>${directionLabel(prevDirection)} ${prevPct}%</b> → now <b>${directionLabel(currDirection)} ${currPct}%</b></div>
    </div>`;
  }

  const delta = currPct - prevPct;
  if (delta === 0) return '';
  return `<div class="diff-strip">${diffPieSvg(prevPct, delta)}
    <div>Previous: <b>${directionLabel(prevDirection)} ${prevPct}%</b><br>
    <span class="${delta >= 0 ? 'delta-up' : 'delta-down'}">${delta >= 0 ? '▲' : '▼'} ${delta >= 0 ? '+' : ''}${delta}pp → now ${currPct}%</span></div>
  </div>`;
}

function diffPieSvg(previousPct, delta) {
  const isUp = delta >= 0;
  const baseColor = "#a5d6a7";
  const deltaColor = isUp ? "#2e7d32" : "#c62828";
  const basePct = isUp ? previousPct : previousPct + delta; // the smaller of the two — the part that's "still true"
  const deltaAbs = Math.abs(delta);
  return `
    <svg width="44" height="44" viewBox="0 0 32 32">
      <circle r="14" cx="16" cy="16" fill="#eee" pathLength="100"/>
      <circle r="14" cx="16" cy="16" fill="transparent" stroke="${baseColor}" stroke-width="14" pathLength="100"
        stroke-dasharray="${basePct} 100" transform="rotate(-90 16 16)"/>
      <circle r="14" cx="16" cy="16" fill="transparent" stroke="${deltaColor}" stroke-width="14" opacity="0.9" pathLength="100"
        stroke-dasharray="${deltaAbs} 100" stroke-dashoffset="${-basePct}" transform="rotate(-90 16 16)"/>
    </svg>`;
}

function dayStripHtml(eventTimeUtc) {
  const today = new Date();
  const eventDate = new Date(eventTimeUtc);
  const cells = [];
  for (let offset = -4; offset <= 10; offset++) {
    const d = new Date(today);
    d.setDate(d.getDate() + offset);
    const isToday = offset === 0;
    const isEvent = d.toDateString() === eventDate.toDateString();
    const classes = ["day-cell"];
    if (isToday) classes.push("today");
    if (isEvent) classes.push("event");
    cells.push(`<div class="${classes.join(" ")}">${d.getDate()}</div>`);
  }
  return `<div class="day-strip">${cells.join("")}</div>`;
}

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
  function tier1DirectionLabel(tier1) {
    if (tier1.confidence === 'Guessing' && tier1.predicted_direction === 'neutral') return 'NO CALL';
    return directionLabel(tier1.predicted_direction);
  }
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
  const tier1PredictionLine = tier1PredictionHtml(next.tier1_prediction, symbol)
    + tier1SentimentConflictHtml(next.tier1_sentiment_conflict);

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
      📊 Print call: likely <b>${label}</b> <span style="font-size:12px;color:#888">(${confPct}% confidence)</span>
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
        + otherEventTier1ConflictMarkerHtml(e.tier1_sentiment_conflict);
      if (e.direction === "pending") {
        return `<div class="other-event-row">
          <span class="other-event-title">${escapeHtml(e.event_title)}</span>
          <span class="other-event-pending">Pending</span>
          ${tier1Marker}
        </div>`;
      }
      const pct = directionPct(e.probability, e.direction);
      const dClass = directionClass(e.direction);
      return `<div class="other-event-row">
        <span class="other-event-title">${escapeHtml(e.event_title)}</span>
        <span class="other-event-call ${dClass}">${directionLabel(e.direction)} ${pct}%</span>
        ${tier1Marker}
      </div>`;
    }).join('');
    return `<div class="other-events">
      <div class="other-events-heading">${simultaneous.length} more event${simultaneous.length === 1 ? '' : 's'} at this time</div>
      ${rows}
    </div>`;
  }
  const otherEventsLine = otherEventsHtml(events, symbol);

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
      ${articlePredictionLine}${tier1PredictionLine}${printPredictionLine}${kalshiReadLine}${trendSignalLine}${otherEventsLine}`;
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

  body += `<div class="gauge-row">${gaugeSvg(pct, next.direction)}
    <div><div class="gauge-label ${dirClass}">${directionLabel(next.direction)} ${pct}%</div>
    <div style="font-size:12px;color:#888">${escapeHtml(next.event_title)}</div>
    ${articlePredictionLine}${tier1PredictionLine}${printPredictionLine}${kalshiReadLine}</div></div>
    <div class="bull-bear-scale">${bullBearScaleSvg(next.probability)}</div>`;
  body += otherEventsLine;
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
        ? `<div style="font-size:12px;color:#666">📊 ${escapeHtml(call.print_prediction.direction)} (${Math.round(call.print_prediction.confidence * 100)}% conf.)</div>`
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

async function loadHistoryIfNeeded() {
  if (historyLoaded) return;  // fetched once per page load, not on the dashboard's poll cycle
  historyLoaded = true;
  const resp = await fetch("/api/history");
  const data = await resp.json();
  renderHistoryTable(data.rows || []);
  await loadHistoryStatsIfNeeded();
}

function renderHistoryStats(stats) {
  const container = document.getElementById("history-stats");
  const overall = stats.overall;
  const overallLabel = overall.accuracy === null
    ? `${overall.correct + overall.wrong} calls made, ${overall.no_call} no-call`
    : `${overall.correct}/${overall.correct + overall.wrong} correct (${Math.round(overall.accuracy * 100)}%), ${overall.no_call} no-call`;

  const titles = Object.keys(stats.by_event_title).sort();
  const rows = titles.map((title) => {
    const s = stats.by_event_title[title];
    const label = s.accuracy === null
      ? `${s.no_call} no-call, 0 calls made`
      : `${s.correct}/${s.correct + s.wrong} (${Math.round(s.accuracy * 100)}%)${s.no_call ? `, ${s.no_call} no-call` : ""}`;
    return `<tr><td>${escapeHtml(title)}</td><td>${label}</td></tr>`;
  }).join("");

  container.innerHTML = `
    <div id="history-stats-overall"><b>Overall:</b> ${overallLabel}</div>
    <details id="history-stats-detail">
      <summary>By event type</summary>
      <table id="history-stats-table"><tbody>${rows}</tbody></table>
    </details>`;
}

async function loadHistoryStatsIfNeeded() {
  const resp = await fetch("/api/history/stats");
  const data = await resp.json();
  renderHistoryStats(data);
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
  tbody.innerHTML = rows.map((r) => {
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
    const outcomeLabel = r.outcome === null
      ? `<span style="color:#888">${
          r.unjudged_reason === "pending" ? "Awaiting confirmation"
          : r.unjudged_reason === "unknown_surprise" ? "Actual not comparable"
          : "No strong call"
        }</span>`
      : r.outcome === "Confirmed"
        ? '<span style="color:#2e7d32;font-weight:bold">Confirmed</span>'
        : '<span style="color:#c62828;font-weight:bold">Missed</span>';
    return `<tr>
      <td>${escapeHtml(r.event_title)}${sourceBadge}<br><span style="font-size:11px;color:#888">${dateLabel}</span></td>
      <td>${escapeHtml(r.instrument ?? "")}</td>
      <td>${escapeHtml(r.previous ?? "—")}</td>
      <td>${escapeHtml(r.forecast ?? "—")}</td>
      <td>${actualCell}</td>
      <td>${predictionLabel} <span style="font-size:11px;color:#888">(${Math.round(r.ne_confidence * 100)}% conf.)</span>${tier1ConflictBadge}</td>
      <td>${outcomeLabel}</td>
    </tr>`;
  }).join("");
}
