// webapp/static/js/dashboard/symbol-picker.test.js
//
// jsdom test: symbol-picker.js reads document.getElementById(...) at
// MODULE TOP LEVEL (same convention calendar-poll.js already uses), so
// the real fixture DOM (including every id its transitive imports need —
// dashboard-poll.js, staleness.js) must exist before it's imported, same
// pattern dashboard-poll.test.js already uses for lit-html/repeat.js.
import test from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";

function setUpFixtureDom() {
  const dom = new JSDOM(`<!doctype html><html><body>
    <div id="cards"></div>
    <div id="predictions-stale-notice"></div>
    <div id="predictions-poll-error-notice"></div>
    <div id="feed-staleness-indicator"></div>
    <div id="accumulator-staleness-indicator"></div>
    <button id="symbol-picker-toggle"></button>
    <div id="symbol-picker-panel" hidden><div id="symbol-picker-body"></div></div>
  </body></html>`);
  global.window = dom.window;
  global.document = dom.window.document;
  global.HTMLElement = dom.window.HTMLElement;
  global.Text = dom.window.Text;
  global.customElements = dom.window.customElements;
  return dom;
}

// Real ticker set the picker currently tracks, per the mocked
// /api/predictions response — mutated by the fake fetch below so a
// tick/untick round-trip is observable the same way the real backend
// would make it observable (a changed set on the NEXT fetch).
function installFakeFetch(trackedSymbols) {
  const calls = [];
  global.fetch = async (url, options) => {
    calls.push({ url, options });
    if (url === "/api/predictions") {
      return { ok: true, json: async () => ({ predictions: [...trackedSymbols].map((symbol) => ({ symbol })) }) };
    }
    if (url === "/api/symbols" && options?.method === "POST") {
      const { ticker } = JSON.parse(options.body);
      trackedSymbols.add(ticker);
      return { ok: true, json: async () => ({ symbol: ticker }) };
    }
    if (url.startsWith("/api/symbols/") && options?.method === "DELETE") {
      const ticker = decodeURIComponent(url.split("/").pop());
      trackedSymbols.delete(ticker);
      return { ok: true, json: async () => ({}) };
    }
    throw new Error(`unexpected fetch: ${url}`);
  };
  return calls;
}

test("clicking the toggle opens the panel showing the 3 category buttons", async () => {
  setUpFixtureDom();
  installFakeFetch(new Set());
  await import(`./symbol-picker.js?t=${Math.random()}`);

  document.getElementById("symbol-picker-toggle").click();
  await new Promise((r) => setTimeout(r, 0)); // let openPanel()'s await settle

  const panel = document.getElementById("symbol-picker-panel");
  assert.equal(panel.hidden, false, "panel must be visible after the toggle is clicked");
  const buttons = [...document.querySelectorAll(".picker-category-btn")].map((b) => b.textContent);
  assert.deepEqual(buttons, ["Metals ▸", "Indices ▸", "FX Pairs ▸"]);
});

test("opening a category shows its symbols pre-ticked for whatever's already tracked", async () => {
  setUpFixtureDom();
  installFakeFetch(new Set(["XAUUSD"]));
  await import(`./symbol-picker.js?t=${Math.random()}`);

  document.getElementById("symbol-picker-toggle").click();
  await new Promise((r) => setTimeout(r, 0));
  [...document.querySelectorAll(".picker-category-btn")].find((b) => b.textContent.startsWith("Metals")).click();

  // Regression: a category click's own re-render used to detach the
  // clicked button from the DOM before the click event finished bubbling
  // to the "click outside closes it" listener, making every category
  // click look like a click outside the panel and close it immediately —
  // never reaching the tick list at all. Assert the panel is still open,
  // not just that the (still-present-in-the-DOM-either-way) checkboxes exist.
  assert.equal(document.getElementById("symbol-picker-panel").hidden, false, "the panel must stay open after picking a category");
  const boxes = [...document.querySelectorAll('.picker-symbol-label input[type="checkbox"]')];
  const bySymbol = Object.fromEntries(boxes.map((b) => [b.closest("li").textContent.trim(), b.checked]));
  assert.equal(bySymbol.XAUUSD, true, "XAUUSD is tracked — its box must start ticked");
  assert.equal(bySymbol.XAGUSD, false, "XAGUSD is not tracked — its box must start unticked");
});

test("ticking an unticked box adds the symbol immediately — no separate Add button", async () => {
  setUpFixtureDom();
  const tracked = new Set();
  const calls = installFakeFetch(tracked);
  await import(`./symbol-picker.js?t=${Math.random()}`);

  document.getElementById("symbol-picker-toggle").click();
  await new Promise((r) => setTimeout(r, 0));
  [...document.querySelectorAll(".picker-category-btn")].find((b) => b.textContent.startsWith("Metals")).click();

  const xauBox = [...document.querySelectorAll('.picker-symbol-label input[type="checkbox"]')].find((b) => b.closest("li").textContent.trim() === "XAUUSD");
  xauBox.checked = true;
  xauBox.dispatchEvent(new window.Event("change", { bubbles: true }));
  await new Promise((r) => setTimeout(r, 0));

  assert.ok(tracked.has("XAUUSD"), "the real add endpoint must have been called");
  const addCall = calls.find((c) => c.url === "/api/symbols");
  assert.ok(addCall, "expected a POST to /api/symbols");
  assert.equal(JSON.parse(addCall.options.body).ticker, "XAUUSD");
});

test("unticking a ticked box removes the symbol immediately", async () => {
  setUpFixtureDom();
  const tracked = new Set(["US30"]);
  const calls = installFakeFetch(tracked);
  await import(`./symbol-picker.js?t=${Math.random()}`);

  document.getElementById("symbol-picker-toggle").click();
  await new Promise((r) => setTimeout(r, 0));
  [...document.querySelectorAll(".picker-category-btn")].find((b) => b.textContent.startsWith("Indices")).click();

  const us30Box = [...document.querySelectorAll('.picker-symbol-label input[type="checkbox"]')].find((b) => b.closest("li").textContent.trim() === "US30");
  assert.equal(us30Box.checked, true);
  us30Box.checked = false;
  us30Box.dispatchEvent(new window.Event("change", { bubbles: true }));
  await new Promise((r) => setTimeout(r, 0));

  assert.ok(!tracked.has("US30"), "the real remove endpoint must have been called");
  assert.ok(calls.some((c) => c.url === "/api/symbols/US30" && c.options?.method === "DELETE"));
});

test("the back button returns from the symbol list to the category list", async () => {
  setUpFixtureDom();
  installFakeFetch(new Set());
  await import(`./symbol-picker.js?t=${Math.random()}`);

  document.getElementById("symbol-picker-toggle").click();
  await new Promise((r) => setTimeout(r, 0));
  [...document.querySelectorAll(".picker-category-btn")].find((b) => b.textContent.startsWith("FX Pairs")).click();
  assert.equal(document.getElementById("symbol-picker-panel").hidden, false, "picking a category must not close the panel");
  assert.ok(document.querySelector(".picker-symbol-list"), "expected the FX Pairs tick list to be showing");

  document.querySelector(".picker-back-btn").click();
  assert.equal(document.getElementById("symbol-picker-panel").hidden, false, "the back button must not close the panel either");
  assert.equal(document.querySelector(".picker-symbol-list"), null, "back must return to the category list");
  assert.ok(document.querySelector(".picker-category-list"));
});

test("clicking outside the panel closes it, and clicking the toggle again re-opens fresh at the category list", async () => {
  setUpFixtureDom();
  installFakeFetch(new Set());
  await import(`./symbol-picker.js?t=${Math.random()}`);

  document.getElementById("symbol-picker-toggle").click();
  await new Promise((r) => setTimeout(r, 0));
  [...document.querySelectorAll(".picker-category-btn")].find((b) => b.textContent.startsWith("Metals")).click();
  assert.ok(document.querySelector(".picker-symbol-list"), "sanity: drilled into a category first");

  document.body.dispatchEvent(new window.Event("click", { bubbles: true }));
  assert.equal(document.getElementById("symbol-picker-panel").hidden, true, "a click outside the panel must close it");

  document.getElementById("symbol-picker-toggle").click();
  await new Promise((r) => setTimeout(r, 0));
  assert.equal(document.getElementById("symbol-picker-panel").hidden, false);
  assert.ok(document.querySelector(".picker-category-list"), "re-opening must start back at the category list, not the last-viewed category");
});

test("the close button closes the panel", async () => {
  setUpFixtureDom();
  installFakeFetch(new Set());
  await import(`./symbol-picker.js?t=${Math.random()}`);

  document.getElementById("symbol-picker-toggle").click();
  await new Promise((r) => setTimeout(r, 0));
  document.querySelector(".picker-close-btn").click();

  assert.equal(document.getElementById("symbol-picker-panel").hidden, true);
});

test("Escape closes the panel", async () => {
  setUpFixtureDom();
  installFakeFetch(new Set());
  await import(`./symbol-picker.js?t=${Math.random()}`);

  document.getElementById("symbol-picker-toggle").click();
  await new Promise((r) => setTimeout(r, 0));
  document.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape" }));

  assert.equal(document.getElementById("symbol-picker-panel").hidden, true);
});
