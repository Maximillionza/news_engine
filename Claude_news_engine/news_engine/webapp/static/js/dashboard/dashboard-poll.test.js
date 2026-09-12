// webapp/static/js/dashboard/dashboard-poll.test.js
//
// jsdom test: the property this whole refactor exists to guarantee —
// repeat()'s keyed diffing genuinely preserves a card's DOM node (and
// therefore any state driven onto it) across two successive render()
// calls with the same key but different data.
import test from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";

test("repeat() keyed by symbol preserves the same DOM node across two renders with the same key", async () => {
  const dom = new JSDOM("<!doctype html><html><body><div id='cards'></div></body></html>");
  global.window = dom.window;
  global.document = dom.window.document;
  global.HTMLElement = dom.window.HTMLElement;
  global.Text = dom.window.Text;
  global.customElements = dom.window.customElements;

  const { html, render } = await import("../../vendor/lit-html.js");
  const { repeat } = await import("../../vendor/directives/repeat.js");

  const cardsEl = document.getElementById("cards");

  function renderList(items) {
    render(
      html`${repeat(items, (i) => i.symbol, (i) => html`<div class="card" data-symbol="${i.symbol}">${i.probability}</div>`)}`,
      cardsEl,
    );
  }

  renderList([{ symbol: "XAUUSD", probability: 0.5 }, { symbol: "US30", probability: 0.6 }]);
  const firstNode = cardsEl.querySelector('[data-symbol="XAUUSD"]');
  assert.ok(firstNode, "expected a rendered card for XAUUSD");

  // Mark the node with UI-only state a real interaction would set (e.g.
  // a flipped class) that must NOT be lost by the next render just
  // because XAUUSD's own data changed.
  firstNode.classList.add("flipped");

  renderList([{ symbol: "XAUUSD", probability: 0.9 }, { symbol: "US30", probability: 0.6 }]);
  const secondNode = cardsEl.querySelector('[data-symbol="XAUUSD"]');

  assert.equal(secondNode, firstNode, "the DOM node for the same key (symbol) must be the SAME node object, not recreated");
  assert.ok(secondNode.classList.contains("flipped"), "state set directly on the DOM node must survive a re-render keyed by the same identity");
  assert.equal(secondNode.textContent.trim(), "0.9", "the changed value must still be patched into the surviving node");
});

test("repeat() removes a card whose key (symbol) is no longer present, without touching siblings", async () => {
  const dom = new JSDOM("<!doctype html><html><body><div id='cards'></div></body></html>");
  global.window = dom.window;
  global.document = dom.window.document;
  global.HTMLElement = dom.window.HTMLElement;
  global.Text = dom.window.Text;
  global.customElements = dom.window.customElements;

  const { html, render } = await import("../../vendor/lit-html.js");
  const { repeat } = await import("../../vendor/directives/repeat.js");
  const cardsEl = document.getElementById("cards");

  function renderList(items) {
    render(html`${repeat(items, (i) => i.symbol, (i) => html`<div data-symbol="${i.symbol}"></div>`)}`, cardsEl);
  }

  renderList([{ symbol: "XAUUSD" }, { symbol: "US30" }]);
  const us30Node = cardsEl.querySelector('[data-symbol="US30"]');

  renderList([{ symbol: "US30" }]); // XAUUSD removed (e.g. untracked)

  assert.equal(cardsEl.querySelector('[data-symbol="XAUUSD"]'), null);
  assert.equal(cardsEl.querySelector('[data-symbol="US30"]'), us30Node, "the surviving card must not be rebuilt just because a sibling was removed");
});
