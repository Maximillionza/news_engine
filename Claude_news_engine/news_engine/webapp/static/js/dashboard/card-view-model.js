// webapp/static/js/dashboard/card-view-model.js
//
// Pure functions: given one prediction event dict (from /api/predictions'
// events[0]) plus this card's UI-only state, compute every value the
// template needs already decided. Extracted from the original
// monolithic renderCard()'s ~20 nested closures — same responsibilities,
// now testable without a DOM. See
// docs/superpowers/specs/2026-09-11-frontend-rendering-refactor-design.md.

import { directionLabel, directionClass, directionPct, tier1DirectionLabel } from "../format.js";

export function buildArticlePredictionViewModel(pred, prevPred) {
  if (!pred) return null;
  return {
    direction: pred.direction,
    dirClass: directionClass(pred.direction),
    label: directionLabel(pred.direction),
    pct: directionPct(pred.probability, pred.direction),
    articleCount: pred.article_count,
    probability: pred.probability,
    hasDiff: !!prevPred,
    prevDirection: prevPred?.direction,
    prevProbability: prevPred?.probability,
    currDirection: pred.direction,
    currProbability: pred.probability,
  };
}

export function buildArticlePredictionConflictViewModel(conflict) {
  if (!conflict) return null;
  return { titles: conflict.titles };
}

export function buildTier1PredictionViewModel(tier1, symbolForCard) {
  if (!tier1) return null;
  return {
    symbolForCard,
    directionLabel: tier1DirectionLabel(tier1),
    dirClass: directionClass(tier1.predicted_direction),
    confidence: tier1.confidence,
    source: tier1.source,
    value: tier1.value,
  };
}

export function buildTier1SentimentConflictViewModel(conflict) {
  if (!conflict) return null;
  return {
    tier1DirectionLabel: directionLabel(conflict.tier1_direction),
    sentimentDirectionLabel: directionLabel(conflict.sentiment_direction),
  };
}

export function buildTier1ConfidenceDowngradeViewModel(downgrade) {
  if (!downgrade) return null;
  return {
    displayedConfidence: downgrade.displayed_confidence,
    originalConfidence: downgrade.original_confidence,
    series: downgrade.series,
    reason: downgrade.reason || null,
  };
}

export function buildPrintPredictionViewModel(printPred) {
  if (!printPred) return null;
  const label = printPred.direction === "higher" ? "HIGHER than forecast"
    : printPred.direction === "lower" ? "LOWER than forecast" : "IN LINE with forecast";
  const confPct = Math.round(printPred.confidence * 100);
  return { label, confPct };
}

export function buildKalshiReadViewModel(kalshi) {
  if (!kalshi) return null;
  const label = kalshi.implied_direction === "higher" ? "HIGHER than forecast"
    : kalshi.implied_direction === "lower" ? "LOWER than forecast" : "IN LINE with forecast";
  return {
    label,
    pct: Math.round(kalshi.implied_probability * 100),
    openInterest: Math.round(kalshi.open_interest),
  };
}

export function buildTrendSignalViewModel(trend) {
  if (!trend) return null;
  const lean = trend.instrument_lean;
  return {
    direction: trend.direction,
    strength: trend.strength.toFixed(2),
    leanLabel: lean ? (lean === "bullish" ? "BUY" : "SELL") : null,
  };
}

export function buildBreakdownPanelViewModel(prediction) {
  const rows = [];
  if (prediction.article_prediction) {
    rows.push({ icon: "📰", text: `Article sentiment: ${directionLabel(prediction.article_prediction.direction)} (${prediction.article_prediction.article_count} articles)` });
  }
  if (prediction.print_prediction) {
    rows.push({ icon: "📊", text: `Print-direction lexicon: ${prediction.print_prediction.direction} (${Math.round(prediction.print_prediction.confidence * 100)}% conf.)` });
  }
  if (prediction.trend_signal) {
    const lean = prediction.trend_signal.instrument_lean;
    const leanLabel = lean ? ` — lean: ${lean === "bullish" ? "BUY" : "SELL"}` : "";
    rows.push({ icon: "📈", text: `Trend streak: ${prediction.trend_signal.direction} (strength ${prediction.trend_signal.strength.toFixed(2)})${leanLabel}` });
  }
  if (prediction.kalshi_read) {
    rows.push({ icon: "💰", text: `Kalshi market: ${prediction.kalshi_read.implied_direction} (${Math.round(prediction.kalshi_read.implied_probability * 100)}% implied)` });
  }
  return { rows, isEmpty: rows.length === 0 };
}

export function buildEssenceArticleViewModel(e) {
  const essence = e.direction === "pending"
    ? { pending: true }
    : { pending: false, dirClass: directionClass(e.direction), label: directionLabel(e.direction), pct: directionPct(e.probability, e.direction) };
  const article = e.article_prediction
    ? { dirClass: directionClass(e.article_prediction.direction), label: directionLabel(e.article_prediction.direction), pct: directionPct(e.article_prediction.probability, e.article_prediction.direction) }
    : null;
  return { essence, article };
}

export function buildOtherEventTier1MarkerViewModel(tier1, symbolForCard) {
  if (!tier1) return null;
  return { symbolForCard, dirClass: directionClass(tier1.predicted_direction), label: tier1DirectionLabel(tier1) };
}

// Sibling/other-tracked-event row view model: title, when-label (optional,
// only for otherTrackedEventsHtml's cross-day list, not the same-time
// otherEventsHtml list), essence/article dual-numbers, and every marker
// (tier1, tier1 conflict, tier1 downgrade).
export function buildOtherEventRowViewModel(e, symbolForCard, includeWhenLabel) {
  return {
    title: e.event_title,
    whenLabel: includeWhenLabel ? e.event_time_utc : null,
    essenceArticle: buildEssenceArticleViewModel(e),
    tier1Marker: buildOtherEventTier1MarkerViewModel(e.tier1_prediction, symbolForCard),
    hasConflict: !!e.tier1_sentiment_conflict,
    hasDowngrade: !!e.tier1_confidence_downgrade,
    downgradeDisplayedConfidence: e.tier1_confidence_downgrade?.displayed_confidence ?? null,
  };
}

export function buildOtherEventsViewModel(events, symbolForCard) {
  if (!events || events.length === 0) return null;
  const simultaneous = events.slice(1).filter((e) => e.event_time_utc === events[0].event_time_utc);
  if (simultaneous.length === 0) return null;
  return {
    count: simultaneous.length,
    rows: simultaneous.map((e) => buildOtherEventRowViewModel(e, symbolForCard, false)),
  };
}

const OTHER_TRACKED_EVENTS_LIMIT = 3;

export function buildOtherTrackedEventsViewModel(allEvents, symbolForCard) {
  if (!allEvents || allEvents.length === 0) return null;
  const featuredTime = allEvents[0].event_time_utc;
  const candidates = allEvents.slice(1).filter((e) => e.event_time_utc !== featuredTime);
  const conflicts = candidates.filter((e) => e.tier1_sentiment_conflict);
  const nonConflicts = candidates.filter((e) => !e.tier1_sentiment_conflict);
  const rest = conflicts.concat(nonConflicts).slice(0, OTHER_TRACKED_EVENTS_LIMIT);
  if (rest.length === 0) return null;
  return { rows: rest.map((e) => buildOtherEventRowViewModel(e, symbolForCard, true)) };
}

// buildCardViewModel: the top-level entry point. `prediction` is one
// entry from /api/predictions' `predictions[].events[0]` PLUS its
// sibling `events` array (the whole symbol entry, per the API's actual
// shape: { symbol, symbol_class, events: [...] }). `uiState` is this
// card's entry from the cardState Map (Task 6), defaulting to {} for a
// card with no prior interaction.
export function buildCardViewModel(symbolEntry, uiState = {}) {
  const { symbol, symbol_class, events } = symbolEntry;

  // Ground truth: webapp/static/app.js's original renderCard() (still
  // present, untouched) early-returns for these two cases BEFORE it ever
  // destructures events[0] — an fx_cross symbol has no USD exposure to any
  // tracked event, so there is no essence/direction data at all, and an
  // empty `events` array (a newly-added symbol still awaiting its first
  // tracked event) has no `events[0]` to read. Both render only the header
  // (symbol + Remove button) plus one fixed line of text, with no flip
  // trigger wired up (the original only attaches the flip click listener
  // later, in code these early returns never reach). Replicating that
  // shape here, not guessing at it.
  if (symbol_class === "fx_cross") {
    return { symbol, kind: "fx_cross" };
  }
  if (!events || events.length === 0) {
    return { symbol, kind: "no_events" };
  }

  const next = events[0];

  if (next.direction === "pending") {
    const articlePrediction = buildArticlePredictionViewModel(next.article_prediction, next.previous_article_prediction);
    const tier1Prediction = buildTier1PredictionViewModel(next.tier1_prediction, symbol);
    const printPrediction = buildPrintPredictionViewModel(next.print_prediction);
    const kalshiRead = buildKalshiReadViewModel(next.kalshi_read);
    const trendSignal = buildTrendSignalViewModel(next.trend_signal);
    const hasAnySignal = !!(articlePrediction || tier1Prediction || printPrediction || kalshiRead || trendSignal);
    return {
      symbol, isPending: true,
      pendingHeading: hasAnySignal ? `Awaiting essence score: ${next.event_title}` : `Awaiting: ${next.event_title}`,
      eventTimeUtc: next.event_time_utc,
      articlePrediction,
      articlePredictionConflict: articlePrediction ? null : buildArticlePredictionConflictViewModel(next.article_prediction_conflict),
      tier1Prediction,
      tier1SentimentConflict: buildTier1SentimentConflictViewModel(next.tier1_sentiment_conflict),
      tier1ConfidenceDowngrade: buildTier1ConfidenceDowngradeViewModel(next.tier1_confidence_downgrade),
      printPrediction, kalshiRead, trendSignal,
      otherEvents: buildOtherEventsViewModel(events, symbol),
      otherTrackedEvents: buildOtherTrackedEventsViewModel(events, symbol),
      next, uiState,
    };
  }

  const pct = directionPct(next.probability, next.direction);
  const dirClass = directionClass(next.direction);
  const hasPreviousChange = next.previous_probability !== null && next.previous_probability !== undefined
    && next.previous_direction !== "pending"
    && Math.abs(next.previous_probability - next.probability) > 1e-6;
  const justReleased = next.previous_direction === "pending" && next.direction !== "pending";
  const articlePrediction = buildArticlePredictionViewModel(next.article_prediction, next.previous_article_prediction);

  return {
    symbol, isPending: false,
    eventTitle: next.event_title, eventTimeUtc: next.event_time_utc,
    direction: next.direction, pct, dirClass, directionLabel: directionLabel(next.direction), probability: next.probability,
    justReleased,
    hasPreviousChange,
    prevDirection: next.previous_direction, prevProbability: next.previous_probability,
    articlePrediction,
    articlePredictionConflict: articlePrediction ? null : buildArticlePredictionConflictViewModel(next.article_prediction_conflict),
    tier1Prediction: buildTier1PredictionViewModel(next.tier1_prediction, symbol),
    tier1SentimentConflict: buildTier1SentimentConflictViewModel(next.tier1_sentiment_conflict),
    tier1ConfidenceDowngrade: buildTier1ConfidenceDowngradeViewModel(next.tier1_confidence_downgrade),
    printPrediction: buildPrintPredictionViewModel(next.print_prediction),
    kalshiRead: buildKalshiReadViewModel(next.kalshi_read),
    trendSignal: buildTrendSignalViewModel(next.trend_signal),
    otherEvents: buildOtherEventsViewModel(events, symbol),
    otherTrackedEvents: buildOtherTrackedEventsViewModel(events, symbol),
    breakdownPanel: buildBreakdownPanelViewModel(next),
    next, uiState,
  };
}
