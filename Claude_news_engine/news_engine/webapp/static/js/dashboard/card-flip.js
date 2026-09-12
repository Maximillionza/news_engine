// webapp/static/js/dashboard/card-flip.js
//
// Interaction handlers for one card: flip-to-see-progression, the
// History panel toggle, and the "Why this call" breakdown toggle. Each
// handler mutates `cardState` (a Map, symbol -> per-card UI state) and
// calls `onRender()` to trigger a cheap re-render — except a real symbol
// removal, which calls `onSymbolRemoved()` (a real re-fetch) instead,
// since a removed symbol's card must not linger in already-cached data.
// This file owns no rendering itself, only state transitions plus the
// lazy-fetches that used to live inline inside renderCard()'s DOM event
// listeners.

import { fetchArticleHistory, fetchEventHistory, deleteSymbol } from "../api.js";
import { articleProgressionEntryHtml } from "./article-progression.js";

export function createCardFlipHandlers(cardState, { onRender, onSymbolRemoved }) {
  function getState(symbol) {
    if (!cardState.has(symbol)) cardState.set(symbol, {});
    return cardState.get(symbol);
  }

  async function onFlipClick(symbol, show) {
    const state = getState(symbol);
    const nextFlipped = show === undefined ? !state.flipped : show;
    state.flipped = nextFlipped;
    onRender();
    if (!nextFlipped || state.articleHistoryLoaded) return;
    // Lazily fetches on first flip only (data-loaded guard, same pattern
    // as the History toggle) — flipping back and forth afterward is free.
    const eventTitle = state.currentEventTitle;
    const data = await fetchArticleHistory(symbol, eventTitle);
    state.articleHistoryLoaded = true;
    state.articleHistory = data.progression || [];
    onRender();
  }

  // A real server-side deletion, not a local state mutation — the removed
  // symbol's card must actually disappear now, not linger in
  // already-fetched data until the next natural poll. onSymbolRemoved
  // (wired to refreshDashboard() in dashboard-poll.js) does a real
  // re-fetch; calling onRender() here instead would be a real regression
  // from today's removeSymbol()'s own await-then-refresh behavior.
  async function onRemoveClick(symbol) {
    await deleteSymbol(symbol);
    await onSymbolRemoved();
  }

  async function onHistoryToggle(symbol, eventTitle) {
    const state = getState(symbol);
    state.currentEventTitle = eventTitle;
    state.historyPanelOpen = !state.historyPanelOpen;
    onRender();
    if (!state.historyPanelOpen || state.historyPanelLoaded) return;
    const data = await fetchEventHistory(eventTitle);
    state.historyPanelLoaded = true;
    state.historyPanelData = data;
    onRender();
  }

  function onBreakdownToggle(symbol) {
    const state = getState(symbol);
    state.breakdownPanelOpen = !state.breakdownPanelOpen;
    onRender();
  }

  function historyPanelContent(uiState) {
    if (!uiState.historyPanelOpen) return "";
    if (!uiState.historyPanelLoaded) return "Loading…";
    const occurrences = uiState.historyPanelData?.occurrences || [];
    if (occurrences.length === 0) return "No history recorded yet";
    const rows = occurrences.map((o) => {
      const dateLabel = new Date(o.event_time_utc).toLocaleDateString(undefined, { year: "numeric", month: "short" });
      const surpriseLabel = o.surprise_direction
        ? `(${o.surprise_direction.replace("_", "-")})`
        : (o.actual ? "(untracked)" : "(pending)");
      return `${dateLabel}: forecast ${o.forecast ?? "—"}, previous ${o.previous ?? "—"}, actual ${o.actual ?? "—"} ${surpriseLabel}`;
    }).join(" / ");
    return `${rows} → ${uiState.historyPanelData.trend_summary}`;
  }

  function articleProgressionContent(uiState) {
    if (!uiState.flipped) return "";
    if (!uiState.articleHistoryLoaded) return "Loading…";
    if (uiState.articleHistory.length === 0) return "No article-based read recorded for this event yet.";
    return uiState.articleHistory.map((entry, i) => articleProgressionEntryHtml(entry, i === 0)).join("");
  }

  return { onFlipClick, onRemoveClick, onHistoryToggle, onBreakdownToggle, historyPanelContent, articleProgressionContent };
}
