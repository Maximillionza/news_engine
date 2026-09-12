// webapp/static/js/dashboard/card.js
//
// lit-html templates for one Dashboard card. Thin — reads already-decided
// values from the view model (card-view-model.js); minimal branching of
// its own. Each sub-signal is its own named template function, matching
// the original renderCard()'s nested-closure boundaries.
//
// Note on raw-HTML interpolation: format.js's SVG builders and
// buildDiffStripHtml still return pre-built HTML strings rather than
// lit-html templates (Task 3 extracted them verbatim to avoid also
// rewriting their internals here — see the design doc's YAGNI framing).
// The design brief for this task suggested interpolating those strings
// via `html([someString])`, treating a plain array as a stand-in for a
// tagged-template strings array. That does not work: lit-html's internal
// `P()` validation requires the strings array to carry a `.raw` property
// (only real tagged-template call sites produce one), so `html([str])`
// throws "invalid template strings array" the moment it's actually
// rendered — confirmed with a throwaway script against the vendored
// lit-html before writing this file. This uses lit-html's actual,
// documented mechanism for the same job instead: the `unsafeHTML`
// directive, vendored into webapp/static/vendor/directives/unsafe-html.js
// the same way Task 1 vendored repeat.js.
import { html } from "../../vendor/lit-html.js";
import { unsafeHTML } from "../../vendor/directives/unsafe-html.js";
import { escapeHtml, gaugeSvg, bullBearScaleSvg, buildDiffStripHtml, dayStripHtml } from "../format.js";

export function articlePredictionTemplate(vm) {
  if (!vm) return html``;
  const diffHtml = vm.hasDiff
    ? buildDiffStripHtml(vm.prevDirection, vm.prevProbability, vm.currDirection, vm.currProbability)
    : "";
  return html`<div class="article-prediction ${vm.dirClass}">
    📰 Article-based read: <b>${vm.dirClass === "bearish" ? "SELL" : vm.dirClass === "bullish" ? "BUY" : "INDECISIVE"} ${vm.pct}%</b>
    <span style="font-size:12px;color:#888">(backed by ${vm.articleCount} article${vm.articleCount === 1 ? "" : "s"})</span>
    <div class="bull-bear-scale">${unsafeHTML(bullBearScaleSvg(vm.probability))}</div>
    ${unsafeHTML(diffHtml)}
  </div>`;
}

export function articlePredictionConflictTemplate(vm) {
  if (!vm) return html``;
  return html`<div class="article-prediction-conflict">
    ⚠ Conflicting signals across co-released events
    <span style="font-size:12px;color:#888">(${vm.titles.map(escapeHtml).join(", ")})</span>
  </div>`;
}

export function tier1PredictionTemplate(vm) {
  if (!vm) return html``;
  return html`<div class="tier1-prediction ${vm.dirClass}">
    🧮 Tier 1 (${escapeHtml(vm.symbolForCard)}): <b>${vm.directionLabel}</b>
    <span style="font-size:12px;color:#888">— ${escapeHtml(vm.confidence)}, ${escapeHtml(vm.source)}</span>
    <div style="font-size:11px;color:#999">${escapeHtml(vm.value)}</div>
  </div>`;
}

export function tier1SentimentConflictTemplate(vm) {
  if (!vm) return html``;
  return html`<div class="tier1-sentiment-conflict">
    ⚠ Tier 1 vs. sentiment disagree: <b>${vm.tier1DirectionLabel}</b> vs <b>${vm.sentimentDirectionLabel}</b>
  </div>`;
}

export function tier1ConfidenceDowngradeTemplate(vm) {
  if (!vm) return html``;
  return html`<div class="tier1-confidence-downgrade">
    ⚠ Confidence downgraded to <b>${vm.displayedConfidence}</b>
    (was ${vm.originalConfidence}) — unexplained ${vm.series} move${vm.reason ? html`: ${escapeHtml(vm.reason)}` : html``}
  </div>`;
}

export function printPredictionTemplate(vm) {
  if (!vm) return html``;
  return html`<div class="print-prediction">
    📊 Print call: likely <b>${vm.label}</b> <span class="confidence-${vm.confPct >= 66 ? "high" : vm.confPct >= 33 ? "medium" : "low"}">(${vm.confPct}% confidence)</span>
  </div>`;
}

export function kalshiReadTemplate(vm) {
  if (!vm) return html``;
  return html`<div class="kalshi-read">
    💰 Kalshi market: likely <b>${vm.label}</b> <span style="font-size:12px;color:#888">(${vm.pct}% implied, ${vm.openInterest} open interest)</span>
  </div>`;
}

export function trendSignalTemplate(vm) {
  if (!vm) return html``;
  return html`<div class="trend-signal">
    📈 Trend streak: <b>${vm.direction}</b> <span style="font-size:12px;color:#888">(strength ${vm.strength})</span>${vm.leanLabel ? html` — lean: <b>${vm.leanLabel}</b>` : html``}
  </div>`;
}

export function breakdownPanelTemplate(vm) {
  if (!vm || vm.isEmpty) return html`<div style="font-size:12px;color:#888">No structured signals fired for this event yet.</div>`;
  return html`${vm.rows.map((r) => html`<div>${r.icon} ${r.text}</div>`)}`;
}

export function otherEventTier1MarkerTemplate(vm) {
  if (!vm) return html``;
  return html`<span class="other-event-tier1 ${vm.dirClass}">🧮 Tier 1 (${escapeHtml(vm.symbolForCard)}): <b>${vm.label}</b></span>`;
}

export function otherEventTier1ConflictMarkerTemplate(hasConflict) {
  if (!hasConflict) return html``;
  return html`<span class="other-event-tier1-conflict">⚠ Tier 1 vs. sentiment disagree</span>`;
}

export function otherEventTier1DowngradeMarkerTemplate(hasDowngrade, displayedConfidence) {
  if (!hasDowngrade) return html``;
  return html`<span class="other-event-tier1-downgrade">⚠ Confidence downgraded to <b>${displayedConfidence}</b></span>`;
}

export function essenceArticleTemplate(vm) {
  const essenceHtml = vm.essence.pending
    ? html`<span class="other-event-pending">Essence: Pending</span>`
    : html`<span class="other-event-call ${vm.essence.dirClass}">Essence: ${vm.essence.label} ${vm.essence.pct}%</span>`;
  const articleHtml = vm.article
    ? html` <span class="other-event-article ${vm.article.dirClass}">Article: ${vm.article.label} ${vm.article.pct}%</span>`
    : html``;
  return html`${essenceHtml}${articleHtml}`;
}

function otherEventRowTemplate(row) {
  return html`<div class="other-event-row">
    <span class="other-event-title">${escapeHtml(row.title)}${row.whenLabel ? html` <span style="font-size:11px;color:#888">(${new Date(row.whenLabel).toLocaleString()})</span>` : html``}</span>
    ${essenceArticleTemplate(row.essenceArticle)}
    ${otherEventTier1MarkerTemplate(row.tier1Marker)}
    ${otherEventTier1ConflictMarkerTemplate(row.hasConflict)}
    ${otherEventTier1DowngradeMarkerTemplate(row.hasDowngrade, row.downgradeDisplayedConfidence)}
  </div>`;
}

export function otherEventsTemplate(vm) {
  if (!vm) return html``;
  return html`<div class="other-events">
    <div class="other-events-heading">${vm.count} more event${vm.count === 1 ? "" : "s"} at this time</div>
    ${vm.rows.map(otherEventRowTemplate)}
  </div>`;
}

export function otherTrackedEventsTemplate(vm) {
  if (!vm) return html``;
  return html`<div class="other-events">
    <div class="other-events-heading">Other tracked events</div>
    ${vm.rows.map(otherEventRowTemplate)}
  </div>`;
}

// cardTemplate: the top-level card. `flipHandlers` is an object of event
// handler functions supplied by card-flip.js (Task 5) — kept as a
// parameter rather than imported directly so card.js has zero dependency
// on cardState/interaction wiring, staying a pure function of (viewModel,
// handlers) -> TemplateResult.
export function cardTemplate(vm, flipHandlers) {
  const safeSymbol = escapeHtml(vm.symbol);
  if (vm.isPending) {
    return html`<div class="card">
      <div class="card-header">
        <h3 class="symbol-flip-trigger" data-symbol="${safeSymbol}" @click=${() => flipHandlers.onFlipClick(vm.symbol)}>${safeSymbol}</h3>
        <button class="remove-btn" @click=${() => flipHandlers.onRemoveClick(vm.symbol)}>Remove</button>
      </div>
      <div class="pending">${vm.pendingHeading}<br>
        <span style="font-size:12px;color:#888">${new Date(vm.eventTimeUtc).toLocaleString()}</span></div>
      ${articlePredictionTemplate(vm.articlePrediction)}${articlePredictionConflictTemplate(vm.articlePredictionConflict)}
      ${tier1PredictionTemplate(vm.tier1Prediction)}${tier1SentimentConflictTemplate(vm.tier1SentimentConflict)}${tier1ConfidenceDowngradeTemplate(vm.tier1ConfidenceDowngrade)}
      ${printPredictionTemplate(vm.printPrediction)}${kalshiReadTemplate(vm.kalshiRead)}${trendSignalTemplate(vm.trendSignal)}
      ${otherEventsTemplate(vm.otherEvents)}${otherTrackedEventsTemplate(vm.otherTrackedEvents)}
    </div>`;
  }

  return html`<div class="card ${vm.uiState.flipped ? "card-has-flip flipped" : ""}">
    <div class="card-flip-inner">
      <div class="card-flip-front">
        <div class="card-header">
          <h3 class="symbol-flip-trigger" data-symbol="${safeSymbol}" @click=${() => flipHandlers.onFlipClick(vm.symbol)}>${safeSymbol}</h3>
          <button class="remove-btn" @click=${() => flipHandlers.onRemoveClick(vm.symbol)}>Remove</button>
        </div>
        ${vm.justReleased ? html`<div class="just-released ${vm.dirClass}">🎯 Just released — ${vm.dirClass === "bearish" ? "SELL" : vm.dirClass === "bullish" ? "BUY" : "INDECISIVE"} ${vm.pct}%</div>` : html``}
        ${vm.hasPreviousChange ? unsafeHTML(buildDiffStripHtml(vm.prevDirection, vm.prevProbability, vm.direction, vm.probability)) : html``}
        <div class="gauge-row">${unsafeHTML(gaugeSvg(vm.pct, vm.direction))}
          <div><div class="gauge-label ${vm.dirClass}">Essence: ${vm.dirClass === "bearish" ? "SELL" : vm.dirClass === "bullish" ? "BUY" : "INDECISIVE"} ${vm.pct}%</div>
          <div style="font-size:12px;color:#888">${escapeHtml(vm.eventTitle)}</div>
          ${articlePredictionTemplate(vm.articlePrediction)}${articlePredictionConflictTemplate(vm.articlePredictionConflict)}
          ${tier1PredictionTemplate(vm.tier1Prediction)}${tier1SentimentConflictTemplate(vm.tier1SentimentConflict)}${tier1ConfidenceDowngradeTemplate(vm.tier1ConfidenceDowngrade)}
          ${printPredictionTemplate(vm.printPrediction)}${kalshiReadTemplate(vm.kalshiRead)}</div></div>
        <div class="bull-bear-scale">${unsafeHTML(bullBearScaleSvg(vm.probability))}</div>
        ${otherEventsTemplate(vm.otherEvents)}${otherTrackedEventsTemplate(vm.otherTrackedEvents)}
        ${unsafeHTML(dayStripHtml(vm.eventTimeUtc))}
        <div class="history-toggle">
          <button class="history-toggle-btn" @click=${() => flipHandlers.onHistoryToggle(vm.symbol, vm.eventTitle)}>History ▾</button>
          <div class="history-panel" style="display:${vm.uiState.historyPanelOpen ? "" : "none"}">${flipHandlers.historyPanelContent(vm.uiState)}</div>
        </div>
        <div class="history-toggle">
          <button class="breakdown-toggle-btn" @click=${() => flipHandlers.onBreakdownToggle(vm.symbol)}>Why this call ▾</button>
          <div class="history-panel" style="display:${vm.uiState.breakdownPanelOpen ? "" : "none"}">${breakdownPanelTemplate(vm.breakdownPanel)}</div>
        </div>
      </div>
      <div class="card-flip-back">
        <div class="card-header">
          <h3>${safeSymbol} — why this changed</h3>
          <button class="flip-back-btn" @click=${() => flipHandlers.onFlipClick(vm.symbol, false)}>✕ Back</button>
        </div>
        <div class="article-progression">${flipHandlers.articleProgressionContent(vm.uiState)}</div>
      </div>
    </div>
  </div>`;
}
