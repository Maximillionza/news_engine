// webapp/static/js/stats/stats.js
//
// Stats tab controller: fetches rows once, then filters/renders client-side. Chart and scoreboard
// are fetched per selection. All HTML comes from the pure builders in rows.js / chart.js / info.js.
import { escapeHtml } from "../format.js";
import { fetchStatsEvents, fetchStatsChart, fetchStatsScoreboard, fetchStatsComponents } from "../api.js";
import { buildChartSvg } from "./chart.js";
import { componentsHtml } from "./info.js";
import {
  tier1BodyHtml, emptyRowHtml, combinedRowHtml, sentimentRowHtml, pickNextRow, briefCardHtml, scoreboardHtml,
  filterRows, yearsPresent, preNewsDisclaimer, reconstructedDisclaimer,
} from "./rows.js";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const DEFAULT_EVENT = "CPI m/m";
const SUBTABS = ["combined", "tier1", "news"];

let statsLoaded = false;
let allRows = [];
let disclaimers = {};
const state = { sub: "combined", method: "combined", year: "", month: "", event: DEFAULT_EVENT };
let handlersAttached = false;   // a retry after a failed first load must not double-bind listeners
let infoToken = 0;               // drops a breakdown response superseded by a newer click
let renderToken = 0;   // drops responses from a superseded selection (chart/scoreboard are async)

const $ = (id) => document.getElementById(id);

export async function loadStatsIfNeeded() {
  if (statsLoaded) return;
  statsLoaded = true;
  try {
    const data = await fetchStatsEvents();
    allRows = data.rows || [];
    disclaimers = data.disclaimers || {};
    populateFilters();
    attachHandlers();
    render();
  } catch (err) {
    statsLoaded = false;   // let the next click on the tab retry
    console.error("loadStatsIfNeeded: fetch failed", err);
    const box = $("stats-error");
    box.textContent = "Could not load the Stats data. Click the Stats tab again to retry.";
    box.style.display = "";
  }
}

function populateFilters() {
  $("stats-year").innerHTML = '<option value="">All</option>'
    + yearsPresent(allRows).map((y) => `<option value="${y}">${y}</option>`).join("");
  $("stats-month").innerHTML = '<option value="">All</option>'
    + MONTHS.map((m, i) => `<option value="${i + 1}">${m}</option>`).join("");
  const titles = [...new Set(allRows.filter((r) => r.status !== "not_scoreable").map((r) => r.event_title))].sort();
  if (!titles.includes(state.event)) state.event = titles[0] || "";
  $("stats-event").innerHTML = titles
    .map((t) => `<option value="${escapeHtml(t)}"${t === state.event ? " selected" : ""}>${escapeHtml(t)}</option>`).join("");
}

function attachHandlers() {
  if (handlersAttached) return;
  handlersAttached = true;
  $("stats-year").addEventListener("change", (e) => { state.year = e.target.value; render(); });
  $("stats-month").addEventListener("change", (e) => { state.month = e.target.value; render(); });
  $("stats-event").addEventListener("change", (e) => { state.event = e.target.value; render(); });
  $("view-stats").addEventListener("click", (e) => {
    const sub = e.target.closest("[data-sub]");
    if (sub) { setSub(sub.dataset.sub); return; }
    const method = e.target.closest("[data-method]");
    if (method) { state.method = method.dataset.method; render(); return; }
    if (e.target.closest(".info-close")) { hideInfo(); return; }
    const trigger = e.target.closest("[data-metric], tr[data-component]");
    if (trigger) showInfo(trigger.dataset.metric || trigger.dataset.component);
  });
}

function setSub(name) {
  if (!SUBTABS.includes(name)) return;
  state.sub = name;
  render();
}

async function showInfo(metric) {
  const box = $("stats-info");
  const token = ++infoToken;
  try {
    const data = await fetchStatsComponents(metric);
    if (token !== infoToken) return;
    box.innerHTML = '<button type="button" class="info-close" aria-label="Close">×</button>' + componentsHtml(data);
    box.style.display = "";
    box.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (err) {
    if (token !== infoToken) return;
    console.error("showInfo: fetch failed", err);
    box.textContent = "Could not load that breakdown.";
    box.style.display = "";
  }
}

function hideInfo() {
  infoToken++;   // a still-pending breakdown must not reopen the panel
  const box = $("stats-info");
  box.innerHTML = "";
  box.style.display = "none";
}

function newestFirst(rows) {
  return [...rows].sort((a, b) => b.event_time_utc.localeCompare(a.event_time_utc));
}

function render() {
  const token = ++renderToken;
  const sub = state.sub;
  $("stats-error").style.display = "none";

  SUBTABS.forEach((name) => {
    const btn = $(`stats-sub-${name}`);
    btn.classList.toggle("active", name === sub);
    btn.setAttribute("aria-selected", String(name === sub));
    $(`stats-pane-${name}`).style.display = name === sub ? "" : "none";
  });
  document.querySelectorAll("#view-stats [data-method]").forEach((b) => b.classList.toggle("active", b.dataset.method === state.method));
  $("stats-event-wrap").style.display = sub === "combined" ? "" : "none";

  const filtered = filterRows(allRows, { year: state.year, month: state.month, event: sub === "combined" ? state.event : "" });

  // Brief card: the next release is independent of the Year/Month filters.
  $("stats-brief").innerHTML = briefCardHtml(pickNextRow(allRows, new Date(), sub), sub, disclaimers);

  const pre = preNewsDisclaimer(filtered, sub, disclaimers);
  const box = $("stats-disclaimer");
  box.textContent = pre ? disclaimers.pre_news : "";
  box.style.display = pre ? "" : "none";

  const table = newestFirst(filtered);
  if (sub === "combined") {
    $("stats-combined-body").innerHTML = table.length ? table.map(combinedRowHtml).join("") : emptyRowHtml(7);
    $("stats-combined-recon-note").textContent = reconstructedDisclaimer(filtered, sub, disclaimers) ? disclaimers.reconstructed : "";
    renderChartAndScoreboard(token);
  } else if (sub === "tier1") {
    $("stats-tier1-body").innerHTML = tier1BodyHtml(filtered);
    $("stats-recon-note").textContent = reconstructedDisclaimer(filtered, sub, disclaimers) ? disclaimers.reconstructed : "";
  } else {
    $("stats-news-body").innerHTML = table.length ? table.map(sentimentRowHtml).join("") : emptyRowHtml(5);
  }
}

async function renderChartAndScoreboard(token) {
  const chartBox = $("stats-chart");
  const boardBox = $("stats-scoreboard");
  const year = state.year ? { year: state.year } : {};
  try {
    const [chart, board] = await Promise.all([
      state.event ? fetchStatsChart({ event: state.event, method: state.method, ...year }) : Promise.resolve({ unit: "", points: [] }),
      fetchStatsScoreboard({ ...(state.event ? { event: state.event } : {}), ...year, ...(state.month ? { month: state.month } : {}) }),
    ]);
    if (token !== renderToken) return;
    // Real container width keeps axis text legible at 375px (see buildChartSvg).
    chartBox.innerHTML = buildChartSvg(chart, { width: Math.max(300, Math.min(900, chartBox.clientWidth - 12)) });
    boardBox.innerHTML = scoreboardHtml(board, chart.unit);
  } catch (err) {
    if (token !== renderToken) return;
    console.error("renderChartAndScoreboard: fetch failed", err);
    chartBox.textContent = "Could not load the chart.";
    boardBox.textContent = "";
  }
}
