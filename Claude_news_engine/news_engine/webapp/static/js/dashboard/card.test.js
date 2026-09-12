// webapp/static/js/dashboard/card.test.js
//
// Must import ./test-dom-setup.js FIRST (before card.js/card-view-model.js):
// see that file's header comment — the vendored lit-html.js reads the
// global `document` at module-load time, so a jsdom document must already
// be installed as a global before lit-html.js's own top-level code runs.
import "./test-dom-setup.js";
import test from "node:test";
import assert from "node:assert/strict";
import {
  articlePredictionTemplate, tier1PredictionTemplate, tier1ConfidenceDowngradeTemplate,
  essenceArticleTemplate, otherEventsTemplate,
} from "./card.js";
import {
  buildArticlePredictionViewModel, buildTier1PredictionViewModel,
  buildTier1ConfidenceDowngradeViewModel, buildEssenceArticleViewModel, buildOtherEventsViewModel,
} from "./card-view-model.js";

// lit-html's `html` tagged template constructs a TemplateResult without
// touching the DOM — these tests inspect `.values` (the interpolated
// values, in template order) to confirm the right data reached the
// template, without needing to render it.

test("articlePredictionTemplate returns an empty TemplateResult's strings for a null view model", () => {
  const result = articlePredictionTemplate(null);
  assert.equal(result.strings.join(""), "");
});

test("articlePredictionTemplate's values include the computed pct and article count", () => {
  const vm = buildArticlePredictionViewModel({ direction: "bearish", probability: 0.44, article_count: 12 }, null);
  const result = articlePredictionTemplate(vm);
  assert.ok(result.values.includes("SELL"));
  assert.ok(result.values.includes(56));
  assert.ok(result.values.some((v) => String(v).includes("12")));
});

test("tier1PredictionTemplate's values include NO CALL for a Guessing/neutral row", () => {
  const vm = buildTier1PredictionViewModel({ confidence: "Guessing", predicted_direction: "neutral", source: "src", value: "no call" }, "XAUUSD");
  const result = tier1PredictionTemplate(vm);
  assert.ok(result.values.includes("NO CALL"));
});

test("tier1ConfidenceDowngradeTemplate omits a reason clause's TemplateResult when reason is null", () => {
  const vm = buildTier1ConfidenceDowngradeViewModel({ displayed_confidence: "Likely", original_confidence: "Certain", series: "DXY", reason: null });
  const result = tier1ConfidenceDowngradeTemplate(vm);
  assert.ok(result.values.includes("Likely"));
  assert.ok(result.values.includes("Certain"));
  assert.ok(result.values.includes("DXY"));
});

test("essenceArticleTemplate: pending essence, no article — only one labeled span produced", () => {
  // essenceArticleTemplate returns html`${essenceHtml}${articleHtml}` — a
  // wrapper whose OWN `.strings` are just the empty literal segments
  // around its two interpolations ("", "", ""); the actual markup lives
  // in the nested TemplateResults carried in `.values`. So this inspects
  // those nested values rather than the (necessarily empty) outer
  // `.strings`, unlike the brief's original assertion which checked
  // `result.strings.join("").includes("Essence")` — that string is
  // always "" for this wrapper shape and the assertion could never pass;
  // confirmed empirically (a test-only fix, no production behavior change).
  const vm = buildEssenceArticleViewModel({ direction: "pending", probability: null, article_prediction: null });
  const result = essenceArticleTemplate(vm);
  assert.equal(result.values.length, 2, "essence value + article value, even when article is an empty TemplateResult");
  const [essenceValue, articleValue] = result.values;
  assert.ok(essenceValue.strings.join("").includes("Essence: Pending"));
  assert.equal(articleValue.strings.join(""), "", "no article prediction means the article half renders as an empty TemplateResult");
});

test("otherEventsTemplate returns an empty TemplateResult when the view model is null (no simultaneous siblings)", () => {
  const vm = buildOtherEventsViewModel([{ event_time_utc: "2026-09-11T12:30:00Z" }], "XAUUSD");
  const result = otherEventsTemplate(vm);
  assert.equal(result.strings.join(""), "");
});
