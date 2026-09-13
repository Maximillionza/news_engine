// webapp/static/js/dashboard/symbol-picker.js
//
// The "+ Add symbol" picker (2026-09-13): replaces the old free-text
// "Add symbol e.g. EURUSD" input entirely. Two steps -- pick a category,
// then tick/untick symbols within it -- with ticking itself being the
// add/remove action (no separate "Add" button, no confirmation, since
// there is nothing to discard: every tick already persisted the instant
// it happened). Self-registers its own listeners at module load, same
// pattern calendar-poll.js's close-button listener already uses --
// nothing here is imported by app.js beyond the side-effecting import.

import { html, render } from "../../vendor/lit-html.js";
import { fetchPredictions, postAddSymbol, deleteSymbol } from "../api.js";
import { refreshDashboard } from "./dashboard-poll.js";

// Mirrors webapp/symbols.py's METALS/INDICES sets exactly, plus a
// curated shortlist of the 7 USD-legged FX majors this project's own
// Layer2 per-instrument guidance already documents real quirks for
// (tier1-cpi-ppi-autoresearch's prompt, 2026-09-13) -- extend this list
// alongside those if either ever grows, same convention
// data_layer/dukascopy_feed.py's _INSTRUMENT_MAP comment already uses.
const CATEGORIES = [
  { key: "metals", label: "Metals", symbols: ["XAUUSD", "XAGUSD"] },
  { key: "indices", label: "Indices", symbols: ["US30", "US500", "NAS100"] },
  { key: "fx", label: "FX Pairs", symbols: ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD"] },
];

const toggleBtn = document.getElementById("symbol-picker-toggle");
const panelEl = document.getElementById("symbol-picker-panel");
const bodyEl = document.getElementById("symbol-picker-body");

// A click inside the panel (e.g. a category button) re-renders bodyEl's
// content synchronously, before the click event finishes bubbling up to
// document's own "click outside closes it" listener below. If that
// re-render removes the clicked element from the DOM (a real category
// button becomes a real tick-list item), the event's target is now
// DETACHED by the time it reaches document — panelEl.contains(target)
// on a detached node is false, so every in-panel click was wrongly read
// as an outside click and closed the panel before it ever opened the
// next step. Stopping propagation here means no click that starts
// inside the panel ever reaches that listener at all.
panelEl.addEventListener("click", (e) => e.stopPropagation());

// null = showing the category list (step 1); a category key = showing
// that category's tick list (step 2). Tracked symbols are re-fetched
// fresh every time the panel opens rather than reused from elsewhere --
// this panel is opened rarely, so a fresh fetch is simpler and safer
// than reaching into dashboard-poll.js's own private state.
let currentCategoryKey = null;
let trackedSymbols = new Set();

function categoryListTemplate() {
  return html`
    <div class="picker-header">
      <span class="picker-title">Add or remove a symbol</span>
      <button class="picker-close-btn" aria-label="Close" @click=${closePanel}>✕</button>
    </div>
    <ul class="picker-category-list">
      ${CATEGORIES.map((cat) => html`
        <li>
          <button class="picker-category-btn" @click=${() => openCategory(cat.key)}>${cat.label} ▸</button>
        </li>
      `)}
    </ul>
  `;
}

function symbolListTemplate(category) {
  return html`
    <div class="picker-header">
      <button class="picker-back-btn" aria-label="Back to categories" @click=${() => openCategory(null)}>◂ Back</button>
      <span class="picker-title">${category.label}</span>
      <button class="picker-close-btn" aria-label="Close" @click=${closePanel}>✕</button>
    </div>
    <ul class="picker-symbol-list">
      ${category.symbols.map((symbol) => html`
        <li class="picker-symbol-row">
          <label class="picker-symbol-label">
            <input type="checkbox" .checked=${trackedSymbols.has(symbol)} @change=${(e) => onToggleSymbol(symbol, e.target.checked)}>
            ${symbol}
          </label>
        </li>
      `)}
    </ul>
  `;
}

function renderPanel() {
  const category = CATEGORIES.find((c) => c.key === currentCategoryKey);
  render(category ? symbolListTemplate(category) : categoryListTemplate(), bodyEl);
}

function openCategory(key) {
  currentCategoryKey = key;
  renderPanel();
}

async function onToggleSymbol(symbol, shouldTrack) {
  // Optimistic: flip the local set immediately so the checkbox itself
  // never visually reverts while the request is in flight, then let the
  // real dashboard refresh (a real re-fetch, same as every other
  // add/remove path in this codebase) confirm it.
  if (shouldTrack) trackedSymbols.add(symbol); else trackedSymbols.delete(symbol);
  renderPanel();
  try {
    if (shouldTrack) {
      await postAddSymbol(symbol);
    } else {
      await deleteSymbol(symbol);
    }
  } catch (err) {
    console.error("symbol-picker: toggle failed", err);
    // Roll back on a real failure -- the request didn't take, so the
    // checkbox must not silently claim it did.
    if (shouldTrack) trackedSymbols.delete(symbol); else trackedSymbols.add(symbol);
    renderPanel();
    return;
  }
  await refreshDashboard();
}

async function openPanel() {
  const data = await fetchPredictions().catch(() => ({ predictions: [] }));
  trackedSymbols = new Set((data.predictions || []).map((p) => p.symbol));
  currentCategoryKey = null;
  panelEl.hidden = false;
  toggleBtn.setAttribute("aria-expanded", "true");
  renderPanel();
  document.addEventListener("click", onDocumentClick);
  document.addEventListener("keydown", onDocumentKeydown);
}

function closePanel() {
  panelEl.hidden = true;
  toggleBtn.setAttribute("aria-expanded", "false");
  document.removeEventListener("click", onDocumentClick);
  document.removeEventListener("keydown", onDocumentKeydown);
}

// Clicking anywhere outside the panel (and outside the toggle button
// itself, which has its own click handler) just closes it -- every tick
// already persisted the instant it happened, so there's nothing to lose.
function onDocumentClick(e) {
  if (panelEl.contains(e.target) || e.target === toggleBtn) return;
  closePanel();
}

function onDocumentKeydown(e) {
  if (e.key === "Escape") closePanel();
}

toggleBtn.addEventListener("click", () => {
  if (panelEl.hidden) openPanel(); else closePanel();
});
