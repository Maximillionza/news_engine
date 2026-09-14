// webapp/static/js/shock-alerts/table.js
import { escapeHtml } from "../format.js";
import { fetchShockAlerts } from "../api.js";

let shockAlertsLoaded = false;

export async function loadShockAlertsIfNeeded() {
  if (shockAlertsLoaded) return;
  shockAlertsLoaded = true;
  try {
    const data = await fetchShockAlerts();
    renderShockAlerts(data.rows || []);
  } catch (err) {
    console.error("loadShockAlertsIfNeeded: fetch failed", err);
  }
}

const SEVERITY_COLOR = { High: "#c62828", Medium: "#ef6c00", Low: "#888" };

function _alertHtml(row) {
  const symbolsLine = (row.affected_symbols || [])
    .map((s) => `${escapeHtml(s.symbol)} (${escapeHtml(s.channel)})`)
    .join(", ") || "none currently tracked";
  const sourcesLine = (row.sources || [])
    .map((s) => `<a href="${escapeHtml(s.url)}" target="_blank" rel="noopener">${escapeHtml(s.source)}</a>`)
    .join(", ");
  const mismatchBadge = row.reality_mismatch === true
    ? ' <span style="color:#c62828;font-weight:bold">⚠ reality check: mismatch</span>'
    : row.reality_mismatch === false
    ? ' <span style="color:#2e7d32">✓ reality check: confirmed</span>'
    : "";
  const deliveryBadge = row.severity === "High" && row.delivery_status === "failed"
    ? ' <span style="color:#c62828;font-weight:bold">⚠ push failed</span>'
    : "";
  return `<div class="shock-alert-card" style="border-left:4px solid ${SEVERITY_COLOR[row.severity] || "#888"}">
    <div><b>${escapeHtml(row.severity)} — ${escapeHtml(row.category)}</b>${deliveryBadge}</div>
    <div>${escapeHtml(row.headline)}</div>
    <div class="meta-text-sm">Affects: ${symbolsLine}</div>
    ${row.rationale ? `<div class="meta-text-sm">${escapeHtml(row.rationale)}</div>` : ""}
    <div class="meta-text-sm">Sources: ${sourcesLine}</div>
    <div class="meta-text-sm">${new Date(row.detected_at_utc).toLocaleString()}${mismatchBadge}</div>
  </div>`;
}

function renderShockAlerts(rows) {
  const emptyNotice = document.getElementById("shock-alerts-empty-notice");
  const list = document.getElementById("shock-alerts-list");
  const lowDetails = document.getElementById("shock-alerts-low-details");
  const lowList = document.getElementById("shock-alerts-low-list");

  if (rows.length === 0) {
    emptyNotice.style.display = "";
    list.innerHTML = "";
    lowDetails.style.display = "none";
    return;
  }
  emptyNotice.style.display = "none";

  const prominent = rows.filter((r) => r.severity !== "Low");
  const low = rows.filter((r) => r.severity === "Low");

  list.innerHTML = prominent.map(_alertHtml).join("");
  if (low.length > 0) {
    lowDetails.style.display = "";
    lowList.innerHTML = low.map(_alertHtml).join("");
  } else {
    lowDetails.style.display = "none";
  }
}
