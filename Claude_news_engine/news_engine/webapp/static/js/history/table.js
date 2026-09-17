import { escapeHtml, directionLabel, directionClass, directionPct, confidenceColorClass } from "../format.js";
import { fetchHistory, fetchHistoryStats } from "../api.js";
import { articleProgressionEntryHtml } from "../dashboard/article-progression.js";

let historyLoaded = false;
// Batch 10: the whole table is small (~35 rows per the live review), so
// filter/sort stay entirely client-side against one fetched snapshot —
// no server round trip per filter change. allHistoryRows is the fetched,
// unfiltered set; renderHistoryTable() below always derives its view from
// it plus the current filter/sort state, never mutates it.
let allHistoryRows = [];
const historySort = { column: "event_time_utc", ascending: false };  // most recent first, matches the API's own default order

export async function loadHistoryIfNeeded() {
  if (historyLoaded) return;  // fetched once per page load, not on the dashboard's poll cycle
  historyLoaded = true;
  const data = await fetchHistory();
  allHistoryRows = data.rows || [];
  _populateHistoryFilterOptions(allHistoryRows);
  renderHistoryTable(_filterAndSortHistoryRows(allHistoryRows));
  await loadHistoryStats();
}

function _populateHistoryFilterOptions(rows) {
  const titleSelect = document.getElementById("history-filter-title");
  const instrumentSelect = document.getElementById("history-filter-instrument");
  const titles = [...new Set(rows.map((r) => r.event_title))].sort();
  const instruments = [...new Set(rows.map((r) => r.instrument).filter(Boolean))].sort();
  for (const t of titles) {
    const opt = document.createElement("option");
    opt.value = t; opt.textContent = t;
    titleSelect.appendChild(opt);
  }
  for (const i of instruments) {
    const opt = document.createElement("option");
    opt.value = i; opt.textContent = i;
    instrumentSelect.appendChild(opt);
  }
}

// A row's "graded" outcome for filtering purposes — 'Correct'/'Wrong' map
// directly from the real backend outcome; every no-call/awaiting/not-
// comparable state (r.outcome === null) collapses to one 'no_call' filter
// value, since the History-tab controls this session added group them as
// one filter option (see index.html's #history-filter-outcome) rather
// than exposing the 3 separate unjudged_reason values as 3 more dropdown
// entries — the underlying data keeps the distinction (still shown per-row
// via unjudged_reason), only the FILTER groups them.
function _historyOutcomeFilterValue(row) {
  if (row.outcome === "Confirmed") return "Correct";
  if (row.outcome === "Missed") return "Wrong";
  return "no_call";
}

function _filterAndSortHistoryRows(rows) {
  const titleFilter = document.getElementById("history-filter-title").value;
  const instrumentFilter = document.getElementById("history-filter-instrument").value;
  const outcomeFilter = document.getElementById("history-filter-outcome").value;

  let filtered = rows.filter((r) =>
    (!titleFilter || r.event_title === titleFilter)
    && (!instrumentFilter || r.instrument === instrumentFilter)
    && (!outcomeFilter || _historyOutcomeFilterValue(r) === outcomeFilter)
  );

  const { column, ascending } = historySort;
  const direction = ascending ? 1 : -1;
  filtered = filtered.slice().sort((a, b) => {
    let av, bv;
    if (column === "event_time_utc") { av = a.event_time_utc; bv = b.event_time_utc; }
    else if (column === "event_title") { av = a.event_title; bv = b.event_title; }
    else if (column === "instrument") { av = a.instrument ?? ""; bv = b.instrument ?? ""; }
    else if (column === "ne_confidence") { av = a.ne_confidence; bv = b.ne_confidence; }
    else { av = a.event_time_utc; bv = b.event_time_utc; }
    if (av < bv) return -1 * direction;
    if (av > bv) return 1 * direction;
    return 0;
  });
  return filtered;
}

function _applyHistoryFilterAndSort() {
  renderHistoryTable(_filterAndSortHistoryRows(allHistoryRows));
}

for (const id of ["history-filter-title", "history-filter-instrument", "history-filter-outcome"]) {
  document.getElementById(id).addEventListener("change", _applyHistoryFilterAndSort);
}

// Column-header click-to-sort — toggles ascending/descending on repeat
// clicks of the same column, defaults to ascending on a new column. A
// small ▲/▼ arrow on the active column's own header is the only visual
// indicator (no separate sort-state UI needed).
const HISTORY_SORTABLE_COLUMNS = {
  "history-th-event": "event_title",
  "history-th-instrument": "instrument",
  "history-th-confidence": "ne_confidence",
};
for (const [id, column] of Object.entries(HISTORY_SORTABLE_COLUMNS)) {
  const th = document.getElementById(id);
  if (!th) continue;
  th.style.cursor = "pointer";
  th.addEventListener("click", () => {
    if (historySort.column === column) {
      historySort.ascending = !historySort.ascending;
    } else {
      historySort.column = column;
      historySort.ascending = true;
    }
    _renderHistorySortIndicators();
    _applyHistoryFilterAndSort();
  });
}

function _renderHistorySortIndicators() {
  for (const [id, column] of Object.entries(HISTORY_SORTABLE_COLUMNS)) {
    const th = document.getElementById(id);
    if (!th) continue;
    const base = th.dataset.label || th.textContent.replace(/ [▲▼]$/, "");
    th.dataset.label = base;
    th.textContent = column === historySort.column ? `${base} ${historySort.ascending ? "▲" : "▼"}` : base;
  }
}

function renderHistoryStats(stats) {
  const container = document.getElementById("history-stats");
  const overall = stats.overall;
  // Batch 9 final-review Minor finding, fixed here: an empty DB rendered
  // a placeholder ("Overall: 0 calls made, 0 no-call" + an empty
  // collapsed detail) instead of nothing — a real conflict with this
  // project's own "render nothing, not a placeholder, when absent"
  // convention every other optional signal on this dashboard follows.
  if (overall.correct + overall.wrong + overall.no_call === 0) {
    container.innerHTML = "";
    return;
  }
  const overallLabel = overall.accuracy === null
    ? `${overall.correct + overall.wrong} calls made, ${overall.no_call} no-call`
    : `${overall.correct}/${overall.correct + overall.wrong} correct (${Math.round(overall.accuracy * 100)}%), ${overall.no_call} no-call`;

  // Batch 9 final-review Minor finding, fixed here: this was re-sorted
  // client-side on top of an already server-sorted response
  // (webapp/app.py's /api/history/stats sorts by_event_title itself) —
  // redundant, and Python's sorted() vs JS's default Array.sort() can
  // disagree on non-ASCII collation. Object.keys() preserves a JSON
  // object's own (server-decided) key order for string keys, so this
  // just trusts it instead of re-deriving it.
  const titles = Object.keys(stats.by_event_title);
  const rows = titles.map((title) => {
    const s = stats.by_event_title[title];
    const label = s.accuracy === null
      ? `${s.no_call} no-call, 0 calls made`
      : `${s.correct}/${s.correct + s.wrong} (${Math.round(s.accuracy * 100)}%)${s.no_call ? `, ${s.no_call} no-call` : ""}`;
    return `<tr><td>${escapeHtml(title)}</td><td>${label}</td></tr>`;
  }).join("");

  const windowLabel = typeof stats.window_limit === "number" ? ` (last ${stats.window_limit} events)` : "";

  container.innerHTML = `
    <div id="history-stats-overall"><b>Overall${escapeHtml(windowLabel)}:</b> ${overallLabel}</div>
    <details id="history-stats-detail">
      <summary>By event type</summary>
      <table id="history-stats-table"><tbody>${rows}</tbody></table>
    </details>`;
}

// Batch 9 final-review Minor finding, fixed here: renamed from
// loadHistoryStatsIfNeeded — that name promised the same
// historyLoaded-style idempotence guard loadHistoryIfNeeded() actually
// implements; this function has none of its own (only idempotent
// because its sole caller already sits behind that guard). Also adds
// the try/catch + resp.ok check refreshDashboard() already established
// — a failure here used to throw an unhandled rejection and never
// retry (since historyLoaded is already true by the time this runs).
async function loadHistoryStats() {
  try {
    const data = await fetchHistoryStats();
    renderHistoryStats(data);
  } catch (err) {
    console.error("loadHistoryStats: fetch failed", err);
  }
}

function renderHistoryTable(rows) {
  const table = document.getElementById("history-table");
  const emptyNotice = document.getElementById("history-empty-notice");
  const tbody = document.getElementById("history-tbody");

  if (rows.length === 0) {
    table.style.display = "none";
    emptyNotice.style.display = "";
    return;
  }

  emptyNotice.style.display = "none";
  table.style.display = "";
  tbody.innerHTML = rows.map((r, idx) => {
    const dateLabel = new Date(r.event_time_utc).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
    const actualCell = r.unchanged_vs_previous
      ? `${escapeHtml(r.actual ?? "—")} <span class="meta-text-sm">(= prev)</span>`
      : escapeHtml(r.actual ?? "—");
    const sourceBadge = r.source === "seeded"
      ? ' <span class="meta-text-sm">(seeded)</span>'
      : r.source === "live_web_fallback"
      ? ' <span class="meta-text-sm">(web-sourced)</span>'
      : r.source === "cloud_web_fallback"
      ? ' <span class="meta-text-sm">(cloud-researched)</span>'
      : "";
    // Numeric rows use higher/lower/in_line; text-event fallback rows use bullish/bearish/neutral.
    const predictionLabel = { higher: "Higher", lower: "Lower", in_line: "In-line", bullish: "Bullish", bearish: "Bearish", neutral: "Neutral" }[r.ne_prediction] || escapeHtml(r.ne_prediction);
    // 2026-09-17 fix: previously only rendered when Tier 1 and sentiment
    // genuinely disagreed (r.tier1_conflict), so a real, computed Tier 1
    // call was invisible on the History tab whenever it happened to AGREE
    // with sentiment (the common case) — the underlying data was always
    // there (webapp/history.py's tier1_prediction field), just never shown.
    // Now renders whenever a real Tier 1 call exists for this row at all;
    // the conflict case additionally gets the warning color/icon.
    const tier1Badge = r.tier1_prediction
      ? ` <span style="color:${r.tier1_conflict ? "#ef6c00" : "#555"};font-size:11px;font-weight:bold">${r.tier1_conflict ? "⚠ " : ""}Tier 1: ${escapeHtml(r.tier1_prediction.predicted_direction)} (${escapeHtml(r.tier1_prediction.confidence)})</span>`
      : "";
    // Batch 10 (dashboard-review-2026-09-11.md live UI walkthrough):
    // "Confirmed" read ambiguously as "the actual print is confirmed"
    // rather than "the prediction was correct" — display-only relabel,
    // the backend outcome value ('Confirmed'/'Missed') is untouched, it's
    // a real data contract scoring/comparison logic already depends on.
    // See #history-legend for what each of the 5 states means.
    const outcomeLabel = r.outcome === null
      ? `<span style="color:#888">${
          r.unjudged_reason === "pending" ? "Awaiting confirmation"
          : r.unjudged_reason === "unknown_surprise" ? "Actual not comparable"
          : "No strong call"
        }</span>`
      : r.outcome === "Confirmed"
        ? '<span style="color:#2e7d32;font-weight:bold">Correct</span>'
        : '<span style="color:#c62828;font-weight:bold">Wrong</span>';
    // Batch 10: "drill-down exists only for pending Dashboard cards, not
    // resolved History rows — exactly when you'd want to see which
    // articles drove a wrong call, the UI removes that view." Reuses the
    // SAME endpoint and rendering (articleProgressionEntryHtml) the
    // Dashboard flip-card already fetches — only a symbol (instrument) to
    // key it, which a print-call-backed numeric row (no specific
    // instrument, by design — see webapp/history.py's HistoryRow
    // docstring) doesn't have, so the toggle is simply absent there
    // rather than fetching against a symbol that isn't real.
    const drillId = `history-drill-${idx}`;
    // Accessibility fix (2026-09-13): aria-expanded/aria-controls kept in
    // sync with the real open/closed state by the click handler below,
    // same "does a screen reader know this is a toggle, and which state
    // it's in" gap already fixed on the Dashboard card's own History/
    // breakdown toggles.
    const drillToggle = r.instrument
      ? ` <button class="history-drill-toggle-btn" data-target="${drillId}" data-event-title="${escapeHtml(r.event_title)}" data-instrument="${escapeHtml(r.instrument)}" aria-expanded="false" aria-controls="${drillId}">why ▾</button>`
      : "";
    return `<tr>
      <td>${escapeHtml(r.event_title)}${sourceBadge}<br><span class="meta-text-sm">${dateLabel}</span>${drillToggle}</td>
      <td>${escapeHtml(r.instrument ?? "")}</td>
      <td>${escapeHtml(r.previous ?? "—")}</td>
      <td>${escapeHtml(r.forecast ?? "—")}</td>
      <td>${actualCell}</td>
      <td>${predictionLabel} <span class="${confidenceColorClass(Math.round(r.ne_confidence * 100))}" style="font-size:11px">(${Math.round(r.ne_confidence * 100)}% conf.)</span>${tier1Badge}</td>
      <td>${outcomeLabel}</td>
    </tr>${r.instrument ? `<tr class="history-drill-row" id="${drillId}" style="display:none"><td colspan="7"><div class="history-panel" data-loaded="false">Loading…</div></td></tr>` : ""}`;
  }).join("");
}

// Moved from webapp/static/app.js (Task 9 boundary-miss cleanup — this
// delegated listener belongs to the History tab's own rendering, same as
// every other function in this file, but Task 8's move only named the
// functions/state above, missing this listener). Delegated (attached once,
// not per-render, since renderHistoryTable() rebuilds #history-tbody's
// innerHTML on every filter/sort change) — an expanded panel collapses on
// the next re-render, same as the rest of this table's state; acceptable
// here since filter/sort is a deliberate user action, not the silent 60s
// background poll refreshDashboard() guards against.
document.getElementById("history-tbody").addEventListener("click", async (e) => {
  const btn = e.target.closest(".history-drill-toggle-btn");
  if (!btn) return;
  const row = document.getElementById(btn.dataset.target);
  const panel = row.querySelector(".history-panel");
  if (row.style.display !== "none") {
    row.style.display = "none";
    btn.setAttribute("aria-expanded", "false");
    return;
  }
  row.style.display = "";
  btn.setAttribute("aria-expanded", "true");
  if (panel.dataset.loaded === "true") return;
  const resp = await fetch(`/api/predictions/${btn.dataset.instrument}/article_history?event_title=${encodeURIComponent(btn.dataset.eventTitle)}`);
  const data = await resp.json();
  panel.dataset.loaded = "true";
  const progression = data.progression || [];
  panel.innerHTML = progression.length === 0
    ? "<div class=\"meta-text\">No article-based read recorded for this event yet.</div>"
    : progression.map((entry, i) => articleProgressionEntryHtml(entry, i === 0)).join("");
});
