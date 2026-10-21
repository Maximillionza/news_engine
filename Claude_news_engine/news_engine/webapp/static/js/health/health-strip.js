// webapp/static/js/health/health-strip.js
//
// Dashboard health strip (B4 O6): one line over the cards showing every job,
// feed, classifier or Tier 1 capture that is not ok, red first. Reads the
// /api/health payload as served; ok items are not shown at all.

import { escapeHtml } from "../format.js";

const KNOWN_STATUSES = new Set(["ok", "amber", "red"]);

export function formatAge(seconds) {
  if (seconds == null) return "never";
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  if (seconds < 86400) return `${(seconds / 3600).toFixed(1)}h`;
  return `${(seconds / 86400).toFixed(1)}d`;
}

// Status is used as a CSS class, so anything unexpected is shown as amber.
function safeStatus(status) {
  return KNOWN_STATUSES.has(status) ? status : "amber";
}

function chipText(item) {
  return item.detail ? `${item.label}: ${item.detail}` : `${item.label}: last success ${formatAge(item.age_seconds)} ago`;
}

export function healthStripModel(payload) {
  const items = payload.items ?? [];
  const pick = (status) => items.filter((item) => safeStatus(item.status) === status)
    .map((item) => ({ status, text: chipText(item) }));
  return { overall: safeStatus(payload.overall), chips: [...pick("red"), ...pick("amber")] };
}

export function renderHealthStrip(el, payload) {
  const model = healthStripModel(payload);
  el.className = `health-strip ${model.overall}`;
  if (model.chips.length === 0) {
    el.textContent = "All jobs and feeds healthy";
    return;
  }
  el.innerHTML = model.chips
    .map((chip) => `<span class="health-chip ${chip.status}">${escapeHtml(chip.text)}</span>`)
    .join("");
}

export function renderHealthUnavailable(el) {
  el.className = "health-strip amber";
  el.textContent = "Health check unavailable";
}
