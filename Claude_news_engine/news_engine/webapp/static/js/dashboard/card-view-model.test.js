// webapp/static/js/dashboard/card-view-model.test.js
import test from "node:test";
import assert from "node:assert/strict";
import {
  buildArticlePredictionViewModel, buildTier1PredictionViewModel,
  buildTier1ConfidenceDowngradeViewModel, buildEssenceArticleViewModel,
  buildOtherEventsViewModel, buildOtherTrackedEventsViewModel, buildCardViewModel,
} from "./card-view-model.js";

test("buildArticlePredictionViewModel returns null when no prediction exists (never fabricated)", () => {
  assert.equal(buildArticlePredictionViewModel(null, null), null);
});

test("buildArticlePredictionViewModel computes dirClass/pct from a real prediction", () => {
  const vm = buildArticlePredictionViewModel({ direction: "bearish", probability: 0.44, article_count: 12 }, null);
  assert.equal(vm.dirClass, "bearish");
  assert.equal(vm.pct, 56); // directionPct complement for bearish
  assert.equal(vm.articleCount, 12);
  assert.equal(vm.hasDiff, false);
});

test("buildTier1PredictionViewModel returns null when no Tier1 row exists", () => {
  assert.equal(buildTier1PredictionViewModel(null, "XAUUSD"), null);
});

test("buildTier1PredictionViewModel: a Guessing/neutral row reads NO CALL", () => {
  const vm = buildTier1PredictionViewModel(
    { confidence: "Guessing", predicted_direction: "neutral", source: "Cleveland Fed", value: "no confident call" },
    "XAUUSD",
  );
  assert.equal(vm.directionLabel, "NO CALL");
  assert.equal(vm.symbolForCard, "XAUUSD");
});

test("buildTier1ConfidenceDowngradeViewModel returns null with no downgrade", () => {
  assert.equal(buildTier1ConfidenceDowngradeViewModel(null), null);
});

test("buildTier1ConfidenceDowngradeViewModel passes through reason=null honestly, never fabricated text", () => {
  const vm = buildTier1ConfidenceDowngradeViewModel({ displayed_confidence: "Likely", original_confidence: "Certain", series: "DXY", reason: null });
  assert.equal(vm.reason, null);
});

test("buildEssenceArticleViewModel: pending essence with no article prediction", () => {
  const vm = buildEssenceArticleViewModel({ direction: "pending", probability: null, article_prediction: null });
  assert.equal(vm.essence.pending, true);
  assert.equal(vm.article, null);
});

test("buildEssenceArticleViewModel: real essence AND a real article prediction both surface, independently", () => {
  const vm = buildEssenceArticleViewModel({
    direction: "bearish", probability: 0.5,
    article_prediction: { direction: "bullish", probability: 0.559 },
  });
  assert.equal(vm.essence.pending, false);
  assert.equal(vm.essence.label, "SELL");
  assert.equal(vm.article.label, "BUY");
});

test("buildOtherEventsViewModel returns null when no simultaneous sibling exists", () => {
  const events = [{ event_time_utc: "2026-09-11T12:30:00Z" }];
  assert.equal(buildOtherEventsViewModel(events, "XAUUSD"), null);
});

test("buildOtherEventsViewModel includes only genuinely simultaneous siblings", () => {
  const events = [
    { event_title: "Core CPI m/m", event_time_utc: "2026-09-11T12:30:00Z" },
    { event_title: "CPI m/m", event_time_utc: "2026-09-11T12:30:00Z" },
    { event_title: "Unrelated Later Event", event_time_utc: "2026-09-12T09:00:00Z" },
  ];
  const vm = buildOtherEventsViewModel(events, "XAUUSD");
  assert.equal(vm.count, 1);
  assert.equal(vm.rows[0].title, "CPI m/m");
});

test("buildOtherTrackedEventsViewModel promotes conflict-flagged rows to the front before bounding", () => {
  const events = [
    { event_title: "Featured", event_time_utc: "2026-09-11T12:30:00Z" },
    { event_title: "No Conflict A", event_time_utc: "2026-09-10T12:30:00Z" },
    { event_title: "Has Conflict", event_time_utc: "2026-09-09T12:30:00Z", tier1_sentiment_conflict: { tier1_direction: "bullish", sentiment_direction: "bearish" } },
    { event_title: "No Conflict B", event_time_utc: "2026-09-08T12:30:00Z" },
    { event_title: "No Conflict C", event_time_utc: "2026-09-07T12:30:00Z" },
  ];
  const vm = buildOtherTrackedEventsViewModel(events, "XAUUSD");
  assert.equal(vm.rows[0].title, "Has Conflict", "the conflict row must be promoted to the front, not lost to the 3-item bound");
  assert.equal(vm.rows.length, 3);
});

test("buildCardViewModel: pending branch produces isPending:true with the right heading when a signal exists", () => {
  const symbolEntry = {
    symbol: "XAUUSD", symbol_class: "metal",
    events: [{
      direction: "pending", event_title: "Prelim UoM Consumer Sentiment", event_time_utc: "2026-09-11T16:00:00Z",
      article_prediction: { direction: "bearish", probability: 0.56, article_count: 139 },
      previous_article_prediction: null, article_prediction_conflict: null,
      tier1_prediction: null, tier1_sentiment_conflict: null, tier1_confidence_downgrade: null,
      print_prediction: null, kalshi_read: null, trend_signal: null,
    }],
  };
  const vm = buildCardViewModel(symbolEntry, {});
  assert.equal(vm.isPending, true);
  assert.match(vm.pendingHeading, /Awaiting essence score/);
});

test("buildCardViewModel: resolved branch computes pct/dirClass and passes uiState through untouched", () => {
  const symbolEntry = {
    symbol: "XAUUSD", symbol_class: "metal",
    events: [{
      direction: "bearish", probability: 0.5, event_title: "Core CPI m/m", event_time_utc: "2026-09-11T12:30:00Z",
      previous_direction: "bullish", previous_probability: 0.53,
      article_prediction: null, article_prediction_conflict: null,
      tier1_prediction: null, tier1_sentiment_conflict: null, tier1_confidence_downgrade: null,
      print_prediction: null, kalshi_read: null, trend_signal: null,
    }],
  };
  const uiState = { flipped: true };
  const vm = buildCardViewModel(symbolEntry, uiState);
  assert.equal(vm.isPending, false);
  assert.equal(vm.dirClass, "bearish");
  assert.equal(vm.hasPreviousChange, true, "a direction reversal from previous must be flagged, even though buildDiffStripHtml renders it as Reversed, not a delta");
  assert.equal(vm.uiState, uiState, "uiState must pass through unchanged for card.js to read");
});

// Fix round 1, Finding 1: the original, untouched renderCard() in
// webapp/static/app.js early-returns for symbol_class === "fx_cross" and
// for an empty/missing `events` array, BEFORE it ever destructures
// events[0] — buildCardViewModel() must replicate that, not crash trying
// to read events[0] off a symbol with no events (the real API shape
// webapp/predictions_service.py unconditionally produces for these cases).

test("buildCardViewModel: fx_cross symbol_class never touches events[0], never throws", () => {
  const symbolEntry = { symbol: "EURGBP", symbol_class: "fx_cross", events: [] };
  assert.doesNotThrow(() => buildCardViewModel(symbolEntry, {}));
  const vm = buildCardViewModel(symbolEntry, {});
  assert.equal(vm.kind, "fx_cross");
  assert.equal(vm.symbol, "EURGBP");
});

test("buildCardViewModel: empty events array never throws, distinct from fx_cross", () => {
  const symbolEntry = { symbol: "XAUUSD", symbol_class: "metal", events: [] };
  assert.doesNotThrow(() => buildCardViewModel(symbolEntry, {}));
  const vm = buildCardViewModel(symbolEntry, {});
  assert.equal(vm.kind, "no_events");
  assert.equal(vm.symbol, "XAUUSD");
});

test("buildCardViewModel: fx_cross takes priority even if events happens to be non-empty (matches the original's branch order)", () => {
  const symbolEntry = {
    symbol: "EURGBP", symbol_class: "fx_cross",
    events: [{ direction: "bearish", probability: 0.5, event_title: "Core CPI m/m", event_time_utc: "2026-09-11T12:30:00Z" }],
  };
  const vm = buildCardViewModel(symbolEntry, {});
  assert.equal(vm.kind, "fx_cross", "the original checks symbol_class before ever looking at events, so fx_cross wins regardless");
});

// Fix round 1, Finding 3: the BUY/SELL/INDECISIVE direction label is a
// decision that belongs in the view model, not recomputed inline in
// card.js's templates (which was happening 3 times).

test("buildArticlePredictionViewModel exposes a pre-computed label, not left for the template to decide", () => {
  const vm = buildArticlePredictionViewModel({ direction: "bearish", probability: 0.44, article_count: 12 }, null);
  assert.equal(vm.label, "SELL");
});

test("buildCardViewModel: resolved branch exposes a pre-computed directionLabel", () => {
  const symbolEntry = {
    symbol: "XAUUSD", symbol_class: "metal",
    events: [{
      direction: "bullish", probability: 0.62, event_title: "Core CPI m/m", event_time_utc: "2026-09-11T12:30:00Z",
      previous_direction: "pending", previous_probability: null,
      article_prediction: null, article_prediction_conflict: null,
      tier1_prediction: null, tier1_sentiment_conflict: null, tier1_confidence_downgrade: null,
      print_prediction: null, kalshi_read: null, trend_signal: null,
    }],
  };
  const vm = buildCardViewModel(symbolEntry, {});
  assert.equal(vm.directionLabel, "BUY");
});
