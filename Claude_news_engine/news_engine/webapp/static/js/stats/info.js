// webapp/static/js/stats/info.js
//
// Information-icon panel: lists the components behind a composite metric (nowcast, news lean,
// Combined). Pure string builder.
import { escapeHtml } from "../format.js";

export function componentsHtml(data) {
  const rows = (data.components || []).map((c) =>
    `<tr><td>${escapeHtml(c.name)}</td><td>${escapeHtml(c.detail)}</td><td>${escapeHtml(c.source)}</td></tr>`).join("");
  return `<div class="info-panel"><strong>${escapeHtml(data.title)}</strong>`
    + `<div class="meta-text-sm">${escapeHtml(data.summary)}</div>`
    + `<table class="stats-table"><tr><th>Input</th><th>Detail</th><th>Source</th></tr>${rows}</table>`
    + (data.note ? `<div class="meta-text-sm">${escapeHtml(data.note)}</div>` : "") + "</div>";
}
