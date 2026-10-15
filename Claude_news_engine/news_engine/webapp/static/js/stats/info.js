// webapp/static/js/stats/info.js
//
// Information-icon panel: lists the components behind a composite metric (nowcast, news lean,
// Combined), and the click-through readings for one release (spec §5). Pure string builders.
import { escapeHtml } from "../format.js";
import { tier1Criteria, sastText, expectedWord, signedLean } from "./rows.js";

export function componentsHtml(data) {
  const rows = (data.components || []).map((c) =>
    `<tr><td>${escapeHtml(c.name)}</td><td>${escapeHtml(c.detail)}</td><td>${escapeHtml(c.source)}</td></tr>`).join("");
  return `<div class="info-panel"><strong>${escapeHtml(data.title)}</strong>`
    + `<div class="meta-text-sm">${escapeHtml(data.summary)}</div>`
    + `<table class="stats-table"><tr><th>Input</th><th>Detail</th><th>Source</th></tr>${rows}</table>`
    + (data.note ? `<div class="meta-text-sm">${escapeHtml(data.note)}</div>` : "") + "</div>";
}

// ---- click-through readings ---------------------------------------------------

// Trailing unit of the published forecast: "0.3%" -> "%", "89K" -> "K".
function unitOf(text) { return String(text ?? "").replace(/^\s*-?[\d.,]+/, "").trim(); }
// Up to 3 decimals, no trailing zeros; signed() adds "+" to positives (0.07 -> "+0.07").
function plain(x) { return String(Number(Number(x).toFixed(3))); }
function signed(x) { const v = Number(Number(x).toFixed(3)); return `${v > 0 ? "+" : ""}${v}`; }
function pct(w) { return `${Math.round(Number(w) * 100)}%`; }

function tier1Lines(row, d, unit, view) {
  const hand = d.hand_logged;
  if (hand) {
    const hasCall = row.tier1 && Object.keys(row.tier1.leans || {}).length > 0;
    return [
      "Tier 1 nowcast: direction only (a hand-researched call, no number)",
      `Researched value: ${hand.value ?? "—"}`,
      `Confidence: ${hand.confidence ?? "—"}`,
      `Source: ${hand.source ?? "—"}`,
      hasCall ? "Expected outcome: the direction in the researched value (no number to compare with the forecast)"
        : "Expected outcome: no call (the researched call is neutral or has no hotter/cooler mapping)",
      "Weights: none (a hand-researched direction; no weights are invented)",
    ];
  }
  if (d.nowcast_value == null) {
    return ["Tier 1 nowcast: no nowcast was recorded before the release, so there is no Tier 1 call"];
  }
  const asOf = d.nowcast_as_of_utc ? ` (as of ${sastText(d.nowcast_as_of_utc)})` : "";
  const out = [`Tier 1 nowcast: ${plain(d.nowcast_value)}${unit}${asOf}`];
  if (row.tier1 && row.tier1.kind) {
    out.push(row.tier1.kind === "reconstructed" ? "Snapshot: reconstructed after the fact from the stated rule"
      : "Snapshot: captured live before the release");
  }
  if (view === "tier1") {
    if (row.forecast != null) out.push(`Expected outcome: ${expectedWord(row.forecast, d.nowcast_value, d.forecast_text)}`);
    out.push("Weights: Tier 1: 100% nowcast");
  }
  return out;
}

function combinedLines(row, d, unit) {
  const out = [];
  if (d.tier1_surprise != null) out.push(`Tier 1 surprise: ${signed(d.tier1_surprise)}${unit} (nowcast minus forecast)`);
  if (d.news_surprise != null) {
    out.push(`News lean ${signedLean(d.news_lean)} × typical surprise ${plain(d.news_scale)}${unit}`
      + ` = news surprise ${signed(d.news_surprise)}${unit}`);
  } else if (d.news_lean != null) {
    out.push(`News lean ${signedLean(d.news_lean)}, but fewer than 3 earlier releases to size it: no news call`);
  } else {
    out.push("News: no news lean before the release");
  }
  if (d.combined_surprise == null || row.forecast == null) {
    out.push("Combined: n/a (Tier 1 has no number for this release)");
    return out;
  }
  const w = d.weights || { tier1: 0.7, news: 0.3 };
  if (d.news_surprise != null && d.tier1_surprise != null) {
    out.push(`Weights: ${pct(w.tier1)} Tier 1 / ${pct(w.news)} news`);
    out.push(`Contributions: Tier 1 ${pct(w.tier1)} × ${signed(d.tier1_surprise)} = ${signed(w.tier1 * d.tier1_surprise)}; `
      + `news ${pct(w.news)} × ${signed(d.news_surprise)} = ${signed(w.news * d.news_surprise)}`);
  } else {
    out.push("Weights: Tier 1 only (no news call for this release)");
  }
  const predicted = row.forecast + d.combined_surprise;
  out.push(`Combined: combined surprise ${signed(d.combined_surprise)}${unit}, predicted ${plain(predicted)}${unit}`);
  out.push(`Expected outcome: ${expectedWord(row.forecast, predicted, d.forecast_text)}`);
  return out;
}

// view is "tier1" (Tier 1 table) or "combined" (Combined table). Every served string is escaped.
export function readingsHtml(row, view) {
  const d = row.detail || {};
  const unit = unitOf(d.forecast_text);
  const lines = [`Forecast: ${d.forecast_text ?? "—"}`, ...tier1Lines(row, d, unit, view)];
  if (view === "combined") lines.push(...combinedLines(row, d, unit));
  const criteria = tier1Criteria(row);
  return `<div class="info-panel readings"><strong>Readings: ${escapeHtml(row.event_title)}, `
    + `${escapeHtml(sastText(row.event_time_utc))}</strong>`
    + (criteria ? `<div class="meta-text-sm">${escapeHtml(criteria)}</div>` : "")
    + `<ul>${lines.map((t) => `<li>${escapeHtml(t)}</li>`).join("")}</ul></div>`;
}
