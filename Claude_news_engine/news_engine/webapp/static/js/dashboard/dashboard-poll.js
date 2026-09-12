// webapp/static/js/dashboard/dashboard-poll.js
//
// refreshDashboard(): fetches /api/predictions, renders every card via
// lit-html's keyed repeat() (keyed by symbol), and owns the one render
// function called from both the poll timer and every card interaction —
// see docs/superpowers/specs/2026-09-11-frontend-rendering-refactor-design.md's
// "Data flow & state model" section.

import { html, render } from "../../vendor/lit-html.js";
import { repeat } from "../../vendor/directives/repeat.js";
import { fetchPredictions } from "../api.js";
import { buildCardViewModel } from "./card-view-model.js";
import { cardTemplate } from "./card.js";
import { createCardFlipHandlers } from "./card-flip.js";
import { renderAccumulatorStaleness } from "../staleness.js";

const cardsEl = document.getElementById("cards");
const predictionsStaleNoticeEl = document.getElementById("predictions-stale-notice");
const predictionsPollErrorEl = document.getElementById("predictions-poll-error-notice");

// symbol -> { flipped, historyPanelOpen, historyPanelLoaded, historyPanelData,
//             breakdownPanelOpen, articleHistoryLoaded, articleHistory, currentEventTitle }
const cardState = new Map();
let latestPredictionsData = null;

function renderDashboardNow() {
  const predictions = latestPredictionsData?.predictions ?? [];
  // onSymbolRemoved is refreshDashboard itself (a real re-fetch), not
  // renderDashboardNow (a cheap re-render of already-cached data) — see
  // card-flip.js's own comment on why this distinction matters.
  const flipHandlers = createCardFlipHandlers(cardState, { onRender: renderDashboardNow, onSymbolRemoved: refreshDashboard });
  render(
    html`${repeat(
      predictions,
      (p) => p.symbol,
      (p) => cardTemplate(buildCardViewModel(p, cardState.get(p.symbol) ?? {}), flipHandlers),
    )}`,
    cardsEl,
  );
}

export async function refreshDashboard() {
  // dashboard-review-2026-09-11.md: a transient network blip here used to
  // throw an unhandled rejection out of this function and silently freeze
  // the dashboard on stale data every subsequent poll, with no visible
  // sign anything was wrong. Caught here instead: leaves whatever's
  // already rendered in place and surfaces a visible, distinct-from-
  // "no data yet" notice. Cleared on the next successful poll.
  let data;
  try {
    data = await fetchPredictions();
  } catch (err) {
    console.error("refreshDashboard: poll failed", err);
    predictionsPollErrorEl.textContent = "Couldn't reach the server — showing the last data received.";
    predictionsPollErrorEl.style.display = "";
    return;
  }
  predictionsPollErrorEl.style.display = "none";

  // "error" here means the background loop (webapp/scheduler.py) hasn't
  // completed its first successful fetch yet — not "a live request just
  // failed," since no route ever fetches live anymore.
  if (data.error) {
    predictionsStaleNoticeEl.textContent = data.error;
    predictionsStaleNoticeEl.style.display = "";
  } else {
    predictionsStaleNoticeEl.textContent = "";
    predictionsStaleNoticeEl.style.display = "none";
  }

  renderAccumulatorStaleness(data.accumulator_staleness_seconds);

  latestPredictionsData = data;
  renderDashboardNow();
}
