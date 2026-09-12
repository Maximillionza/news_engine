// webapp/static/js/dashboard/card-flip.test.js
global.fetch = async () => ({ ok: true, json: async () => ({ progression: [] }) });

import test from "node:test";
import assert from "node:assert/strict";
import { createCardFlipHandlers } from "./card-flip.js";

test("onFlipClick toggles state.flipped and calls onRender", async () => {
  const cardState = new Map();
  let renderCount = 0;
  const handlers = createCardFlipHandlers(cardState, { onRender: () => { renderCount++; }, onSymbolRemoved: async () => {} });
  await handlers.onFlipClick("XAUUSD");
  assert.equal(cardState.get("XAUUSD").flipped, true);
  assert.ok(renderCount >= 1);
});

test("onFlipClick(symbol, false) forces the flip closed regardless of prior state", async () => {
  const cardState = new Map([["XAUUSD", { flipped: true }]]);
  const handlers = createCardFlipHandlers(cardState, { onRender: () => {}, onSymbolRemoved: async () => {} });
  await handlers.onFlipClick("XAUUSD", false);
  assert.equal(cardState.get("XAUUSD").flipped, false);
});

test("onBreakdownToggle toggles independently of onHistoryToggle's state", () => {
  const cardState = new Map();
  const handlers = createCardFlipHandlers(cardState, { onRender: () => {}, onSymbolRemoved: async () => {} });
  handlers.onBreakdownToggle("XAUUSD");
  assert.equal(cardState.get("XAUUSD").breakdownPanelOpen, true);
  assert.equal(cardState.get("XAUUSD").historyPanelOpen, undefined, "breakdown and history panels must not share state");
});

test("historyPanelContent returns empty string when the panel is closed", () => {
  const cardState = new Map();
  const handlers = createCardFlipHandlers(cardState, { onRender: () => {}, onSymbolRemoved: async () => {} });
  assert.equal(handlers.historyPanelContent({ historyPanelOpen: false }), "");
});

test("historyPanelContent shows Loading… before the fetch resolves", () => {
  const cardState = new Map();
  const handlers = createCardFlipHandlers(cardState, { onRender: () => {}, onSymbolRemoved: async () => {} });
  assert.equal(handlers.historyPanelContent({ historyPanelOpen: true, historyPanelLoaded: false }), "Loading…");
});

test("onFlipClick(symbol, undefined, eventTitle) seeds currentEventTitle before any History toggle has run, and fetches article history with the real title", async () => {
  const cardState = new Map();
  const fetchedUrls = [];
  global.fetch = async (url) => {
    fetchedUrls.push(url);
    return { ok: true, json: async () => ({ progression: [] }) };
  };
  const handlers = createCardFlipHandlers(cardState, { onRender: () => {}, onSymbolRemoved: async () => {} });
  await handlers.onFlipClick("XAUUSD", undefined, "Real Event Title");
  assert.equal(cardState.get("XAUUSD").currentEventTitle, "Real Event Title");
  assert.equal(fetchedUrls.length, 1);
  assert.ok(fetchedUrls[0].includes(encodeURIComponent("Real Event Title")), `expected fetch URL to include the real event title, got: ${fetchedUrls[0]}`);
  assert.ok(!fetchedUrls[0].includes("undefined"), `fetch URL must not contain the literal string "undefined": ${fetchedUrls[0]}`);
  global.fetch = async () => ({ ok: true, json: async () => ({ progression: [] }) });
});

test("onFlipClick(symbol, false) without an eventTitle leaves an existing currentEventTitle untouched", async () => {
  const cardState = new Map([["XAUUSD", { flipped: true, currentEventTitle: "Existing Title" }]]);
  const handlers = createCardFlipHandlers(cardState, { onRender: () => {}, onSymbolRemoved: async () => {} });
  await handlers.onFlipClick("XAUUSD", false);
  assert.equal(cardState.get("XAUUSD").currentEventTitle, "Existing Title");
});

test("articleProgressionContent wraps the empty-state message in its styled div", () => {
  const cardState = new Map();
  const handlers = createCardFlipHandlers(cardState, { onRender: () => {}, onSymbolRemoved: async () => {} });
  const content = handlers.articleProgressionContent({ flipped: true, articleHistoryLoaded: true, articleHistory: [] });
  assert.equal(content, `<div style="font-size:12px;color:#888">No article-based read recorded for this event yet.</div>`);
});

test("onRemoveClick calls onSymbolRemoved (a real re-fetch), not onRender (a cheap re-render of stale data)", async () => {
  const cardState = new Map();
  let renderCount = 0, removedCount = 0;
  const handlers = createCardFlipHandlers(cardState, { onRender: () => { renderCount++; }, onSymbolRemoved: async () => { removedCount++; } });
  await handlers.onRemoveClick("XAUUSD");
  assert.equal(removedCount, 1);
  assert.equal(renderCount, 0, "removing a symbol must trigger a real re-fetch, not a render of data that still contains the deleted symbol");
});
