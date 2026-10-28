// webapp/static/js/shock-alerts/table.js
import { escapeHtml } from "../format.js";
import { fetchShockAlerts } from "../api.js";
import { affectsLineHtml } from "./affects.js";
import { freshnessText, contextTagsText, capBadgeHtml, incidentLabelText } from "./alert-meta.js";
import { gradingTableHtml, summaryHtml } from "./grading.js";

let shockAlertsLoaded = false;
let rangeFormWired = false;

async function loadRange(range) {
  const data = await fetchShockAlerts(range);
  const from = document.getElementById("shock-range-from");
  const to = document.getElementById("shock-range-to");
  if (data.range && from && to) {
    from.value = data.range.from;
    to.value = data.range.to;
  }
  renderShockAlerts(data.rows || [], data.summary);
}

// B10 K13: the Show button re-fetches; the first load happens once, with the server's default range.
function wireRangeForm() {
  const form = document.getElementById("shock-range");
  if (rangeFormWired || !form) return;
  rangeFormWired = true;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await loadRange({
        from: document.getElementById("shock-range-from").value,
        to: document.getElementById("shock-range-to").value,
      });
    } catch (err) {
      console.error("shock alerts range fetch failed", err);
    }
  });
}

export async function loadShockAlertsIfNeeded() {
  if (shockAlertsLoaded) return;
  shockAlertsLoaded = true;
  wireRangeForm();
  try {
    await loadRange({});
  } catch (err) {
    console.error("loadShockAlertsIfNeeded: fetch failed", err);
  }
}

const SEVERITY_COLOR = { High: "#c62828", Medium: "#ef6c00", Low: "#888" };

function _alertHtml(row) {
  const symbolsLine = affectsLineHtml(row.affected_symbols);
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
  const tags = contextTagsText(row);
  const freshness = freshnessText(row);
  const incident = incidentLabelText(row);
  return `<div class="shock-alert-card" style="border-left:4px solid ${SEVERITY_COLOR[row.severity] || "#888"}">
    <div><b>${escapeHtml(row.severity)} — ${escapeHtml(row.category)}</b>${deliveryBadge}${capBadgeHtml(row)}</div>
    <div>${escapeHtml(row.headline)}</div>
    ${incident ? `<div class="meta-text-sm">${incident}</div>` : ""}
    ${tags ? `<div class="meta-text-sm">${tags}</div>` : ""}
    <div class="meta-text-sm">Affects: ${symbolsLine}</div>
    ${row.rationale ? `<div class="meta-text-sm">${escapeHtml(row.rationale)}</div>` : ""}
    <div class="meta-text-sm">Sources: ${sourcesLine}</div>
    <div class="meta-text-sm">${new Date(row.detected_at_utc).toLocaleString()}${freshness ? ` · ${escapeHtml(freshness)}` : ""}${mismatchBadge}</div>
  </div>`;
}

function renderShockAlerts(rows, summary) {
  const summaryBox = document.getElementById("shock-grading-summary");
  const tableBox = document.getElementById("shock-grading-table");
  summaryBox.innerHTML = summary && rows.length > 0 ? summaryHtml(summary) : "";
  tableBox.innerHTML = gradingTableHtml(rows, summary ? summary.symbols : []);
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
