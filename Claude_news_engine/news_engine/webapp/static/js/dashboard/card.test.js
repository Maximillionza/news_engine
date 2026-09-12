// webapp/static/js/dashboard/card.test.js
//
// Must import ./test-dom-setup.js FIRST (before card.js/card-view-model.js):
// see that file's header comment — the vendored lit-html.js reads the
// global `document` at module-load time, so a jsdom document must already
// be installed as a global before lit-html.js's own top-level code runs.
import "./test-dom-setup.js";
import test from "node:test";
import assert from "node:assert/strict";
import { render } from "../../vendor/lit-html.js";
import {
  articlePredictionTemplate, tier1PredictionTemplate, tier1ConfidenceDowngradeTemplate,
  essenceArticleTemplate, otherEventsTemplate, cardTemplate,
} from "./card.js";
import {
  buildArticlePredictionViewModel, buildTier1PredictionViewModel,
  buildTier1ConfidenceDowngradeViewModel, buildEssenceArticleViewModel, buildOtherEventsViewModel,
  buildCardViewModel,
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

// Fix round 1, Finding 1: cardTemplate must actually render the fx_cross
// and no_events branches (not just the view model not throwing — the
// template has to handle vm.kind too).

const noopFlipHandlers = {
  onFlipClick: () => {}, onRemoveClick: () => {}, onHistoryToggle: () => {}, onBreakdownToggle: () => {},
  historyPanelContent: () => "", articleProgressionContent: () => "",
};

test("cardTemplate renders the fx_cross branch: header + fixed message, no essence/direction markup", () => {
  const vm = buildCardViewModel({ symbol: "EURGBP", symbol_class: "fx_cross", events: [] }, {});
  const container = document.createElement("div");
  render(cardTemplate(vm, noopFlipHandlers), container);
  assert.match(container.innerHTML, /No USD exposure for tracked events/);
  assert.match(container.innerHTML, />EURGBP</);
  assert.doesNotMatch(container.innerHTML, /gauge-row/, "fx_cross has no essence score, so no gauge should render");
});

test("cardTemplate renders the no_events branch: header + fixed message", () => {
  const vm = buildCardViewModel({ symbol: "XAUUSD", symbol_class: "metal", events: [] }, {});
  const container = document.createElement("div");
  render(cardTemplate(vm, noopFlipHandlers), container);
  assert.match(container.innerHTML, /Awaiting next tracked event/);
  assert.match(container.innerHTML, />XAUUSD</);
});

// Fix round 1, Finding 1 (regression vs. the original renderCard(), which
// calls finalizeCardFlip() unconditionally for BOTH its pending and
// resolved branches): the isPending branch must render the same flip
// structure the resolved branch does, and its symbol <h3> must wire the
// same onFlipClick handler the resolved branch's does — not just have the
// right CSS class with no listener behind it.

test("cardTemplate's isPending branch renders the flip structure (front/back) and wires the symbol click the same as the resolved branch", () => {
  const vm = buildCardViewModel(
    {
      symbol: "XAUUSD", symbol_class: "metal",
      events: [{ event_title: "FOMC Statement", event_time_utc: "2026-09-11T18:00:00Z", direction: "pending" }],
    },
    { flipped: true },
  );
  assert.equal(vm.isPending, true, "sanity check: this test must exercise the isPending branch");

  let flippedSymbolArg = null;
  const flipHandlers = {
    ...noopFlipHandlers,
    onFlipClick: (symbol) => { flippedSymbolArg = symbol; },
    articleProgressionContent: () => "Loading…",
  };
  const container = document.createElement("div");
  render(cardTemplate(vm, flipHandlers), container);

  assert.ok(container.querySelector(".card-flip-inner"), "expected a .card-flip-inner wrapper, same as the resolved branch");
  assert.ok(container.querySelector(".card-flip-front"), "expected a .card-flip-front, same as the resolved branch");
  const back = container.querySelector(".card-flip-back");
  assert.ok(back, "expected a .card-flip-back, same as the resolved branch");
  assert.ok(back.querySelector(".article-progression"), "expected the back face to render the article-progression panel");
  assert.ok(container.querySelector(".card").classList.contains("flipped"), "vm.uiState.flipped must drive the flipped class here too");

  const trigger = container.querySelector(".symbol-flip-trigger");
  assert.ok(trigger, "expected the symbol <h3> flip trigger");
  trigger.click();
  assert.equal(flippedSymbolArg, "XAUUSD", "the pending branch's symbol click must call flipHandlers.onFlipClick, same as the resolved branch");
});

// Fix round 1, Finding 2 (this round): `.card-has-flip` must be applied
// UNCONDITIONALLY, not only once flipped — the original finalizeCardFlip()
// added it to every flippable card and toggled only `.flipped` on top,
// because `.card-has-flip` strips `.card`'s own border/padding/shadow in
// favor of `.card-flip-front`/`.card-flip-back`'s own box styling (see
// style.css's comment on `.card-has-flip`). Applying it conditionally on
// `vm.uiState.flipped` meant every UNFLIPPED card (the default, 100% of
// them) nested two borders/paddings/shadows.

test("cardTemplate's resolved branch applies card-has-flip even when the card is not flipped", () => {
  const vm = buildCardViewModel(
    {
      symbol: "XAUUSD", symbol_class: "metal",
      events: [{ event_title: "NFP", event_time_utc: "2026-09-11T18:00:00Z", direction: "bullish", probability: 0.7 }],
    },
    {}, // no uiState.flipped set — the default, unflipped state
  );
  assert.equal(vm.isPending, false, "sanity check: this test must exercise the resolved branch");
  const container = document.createElement("div");
  render(cardTemplate(vm, noopFlipHandlers), container);
  const card = container.querySelector(".card");
  assert.ok(card.classList.contains("card-has-flip"), "card-has-flip must be present even on an unflipped card");
  assert.ok(!card.classList.contains("flipped"), "flipped must NOT be present on an unflipped card");
});

test("cardTemplate's isPending branch applies card-has-flip even when the card is not flipped", () => {
  const vm = buildCardViewModel(
    {
      symbol: "XAUUSD", symbol_class: "metal",
      events: [{ event_title: "FOMC Statement", event_time_utc: "2026-09-11T18:00:00Z", direction: "pending" }],
    },
    {}, // no uiState.flipped set — the default, unflipped state
  );
  assert.equal(vm.isPending, true, "sanity check: this test must exercise the isPending branch");
  const container = document.createElement("div");
  render(cardTemplate(vm, noopFlipHandlers), container);
  const card = container.querySelector(".card");
  assert.ok(card.classList.contains("card-has-flip"), "card-has-flip must be present even on an unflipped pending card");
  assert.ok(!card.classList.contains("flipped"), "flipped must NOT be present on an unflipped card");
});

// Fix round 1, Finding 1 (this round): the pending branch's symbol-flip
// trigger must pass the real event title through to onFlipClick (as its
// third argument) so card-flip.js can seed state.currentEventTitle before
// ever fetching article history — not omit it and leave the fetch to send
// event_title=undefined.

test("cardTemplate's isPending branch passes the real event title to onFlipClick, not undefined", () => {
  const vm = buildCardViewModel(
    {
      symbol: "XAUUSD", symbol_class: "metal",
      events: [{ event_title: "FOMC Statement", event_time_utc: "2026-09-11T18:00:00Z", direction: "pending" }],
    },
    {},
  );
  let flipArgs = null;
  const flipHandlers = { ...noopFlipHandlers, onFlipClick: (...args) => { flipArgs = args; } };
  const container = document.createElement("div");
  render(cardTemplate(vm, flipHandlers), container);
  container.querySelector(".symbol-flip-trigger").click();
  assert.equal(flipArgs[0], "XAUUSD");
  assert.equal(flipArgs[2], "FOMC Statement", "the pending branch's flip trigger must pass the real event title as the third argument");
});

test("cardTemplate's resolved branch passes the real event title to onFlipClick, not undefined", () => {
  const vm = buildCardViewModel(
    {
      symbol: "XAUUSD", symbol_class: "metal",
      events: [{ event_title: "NFP", event_time_utc: "2026-09-11T18:00:00Z", direction: "bullish", probability: 0.7 }],
    },
    {},
  );
  let flipArgs = null;
  const flipHandlers = { ...noopFlipHandlers, onFlipClick: (...args) => { flipArgs = args; } };
  const container = document.createElement("div");
  render(cardTemplate(vm, flipHandlers), container);
  container.querySelector(".symbol-flip-trigger").click();
  assert.equal(flipArgs[0], "XAUUSD");
  assert.equal(flipArgs[2], "NFP", "the resolved branch's flip trigger must pass the real event title as the third argument");
});

// Fix round 1, Finding 2: a value that goes through card.js's normal
// lit-html `${}` bindings must render its real characters once, not come
// out double-escaped (entity-encoded text that's never decoded back,
// because it's set via a direct DOM property/text-node assignment, not
// parsed as HTML). Verified empirically before the fix: with escapeHtml()
// still in tier1PredictionTemplate, this same test's `source` field
// rendered as the literal, visible substring "Fed&#39;s Beige Book"
// instead of "Fed's Beige Book".

test("tier1PredictionTemplate renders apostrophes/ampersands/angle-brackets ONCE through the real DOM, not double-escaped", () => {
  const vm = buildTier1PredictionViewModel(
    { confidence: "Likely", predicted_direction: "bullish", source: "Fed's Beige Book <2026>", value: "hawkish & confident" },
    "XAUUSD",
  );
  const container = document.createElement("div");
  render(tier1PredictionTemplate(vm), container);
  assert.ok(container.textContent.includes("Fed's Beige Book <2026>"), `expected the real apostrophe/brackets in textContent, got: ${container.textContent}`);
  assert.ok(container.textContent.includes("hawkish & confident"), `expected a real ampersand in textContent, got: ${container.textContent}`);
  assert.ok(!container.innerHTML.includes("&#39;"), "must not be entity-encoded — lit-html's normal ${} binding already prevents injection without escapeHtml()");
  assert.ok(!container.innerHTML.includes("&amp;amp;"), "must not be double-escaped");
});

// Fix round 1, Finding 3: articleProgressionContent() returns a real HTML
// string (card-flip.js's own articleProgressionContent, backed by
// article-progression.js's articleProgressionEntryHtml — real <div>/<a>
// markup). card.js's flip-back panel must interpolate it via unsafeHTML(),
// not a plain lit-html ${} binding (which would set it as literal text,
// never parsed as HTML). historyPanelContent deliberately returns plain
// text and is NOT part of this fix.

test("cardTemplate's flip-back panel renders articleProgressionContent's HTML as real DOM structure, not escaped text", () => {
  const vm = buildCardViewModel(
    { symbol: "XAUUSD", symbol_class: "metal", events: [{ event_title: "NFP", event_time_utc: "2026-09-11T12:30:00Z", direction: "bullish", probability: 0.7 }] },
    { flipped: true },
  );
  const flipHandlers = {
    ...noopFlipHandlers,
    articleProgressionContent: () => '<div class="progression-entry"><a href="https://example.com">Example article</a></div>',
  };
  const container = document.createElement("div");
  render(cardTemplate(vm, flipHandlers), container);
  const progressionDiv = container.querySelector(".article-progression");
  assert.ok(progressionDiv, "expected a .article-progression element");
  const link = progressionDiv.querySelector("a");
  assert.ok(link, "expected articleProgressionContent's markup to render as a real <a> element, not escaped text");
  assert.equal(link.getAttribute("href"), "https://example.com");
  assert.ok(!progressionDiv.innerHTML.includes("&lt;div"), "must not render as escaped literal text");
});
