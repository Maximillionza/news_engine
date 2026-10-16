// webapp/static/js/stats/stats.js
//
// Stats tab controller: fetches the rows (per impact selection), then filters/renders client-side. Chart,
// scoreboard and the Market reaction leaderboard are fetched per selection. All HTML comes from the pure
// builders in rows.js / chart.js / info.js / reaction.js / impact-filter.js.
import { escapeHtml } from "../format.js";
import {
  fetchStatsEvents, fetchStatsChart, fetchStatsScoreboard, fetchStatsComponents,
  fetchReactionLeaderboard, fetchReactionReleases,
} from "../api.js";
import { buildChartSvg } from "./chart.js";
import { componentsHtml, readingsHtml } from "./info.js";
import { DEFAULT_IMPACTS, impactsParam, toggleImpact, chipsHtml } from "./impact-filter.js";
import { createLatestGuard } from "./latest.js";
import {
  leaderboardRowsHtml, leaderboardHeadHtml, releasesHtml, releasesErrorHtml, reactionDisclaimersHtml,
  instrumentOptionsHtml,
} from "./reaction.js";
import {
  tier1BodyHtml, emptyRowHtml, combinedRowHtml, sentimentRowHtml, pickNextRow, briefCardHtml, scoreboardHtml,
  filterRows, yearsPresent, preNewsDisclaimer, reconstructedDisclaimer, rowKey,
} from "./rows.js";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const DEFAULT_EVENT = "CPI m/m";
const SUBTABS = ["combined", "tier1", "news", "reaction"];
const DEFAULT_INSTRUMENT = "XAUUSD";
const NO_IMPACT_MESSAGE = "Select at least one impact level.";

let statsLoaded = false;
let allRows = [];
let disclaimers = {};
const state = {
  sub: "combined", method: "combined", year: "", month: "", event: DEFAULT_EVENT,
  impacts: [...DEFAULT_IMPACTS],      // shared by all four sub-tabs
  instrument: DEFAULT_INSTRUMENT,     // Market reaction only; the response's `instrument` is authoritative
  reactionEvent: "",                  // the leaderboard row whose releases are open, or ""
};
let handlersAttached = false;   // a retry after a failed first load must not double-bind listeners
let infoToken = 0;               // drops a breakdown response superseded by a newer click
let renderToken = 0;   // drops responses from a superseded selection (chart/scoreboard/leaderboard are async)
const rowsGuard = createLatestGuard();   // drops a rows response (or failure) superseded by a newer impact selection
let rowsFor = null;    // the impacts param allRows was loaded for; a sub-tab switch reloads when it differs
let detailToken = 0;   // drops a drill-down response superseded by a newer click or filter

const $ = (id) => document.getElementById(id);

export async function loadStatsIfNeeded() {
  if (statsLoaded) return;
  statsLoaded = true;
  try {
    await loadRows();
    populateFilters();
    renderChips();
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

// Fetches the rows for the current impact selection. With nothing selected the API is not called (an empty
// `impacts` would mean "no filter" to the server); the rows are simply empty. Returns false when a newer
// selection superseded this fetch, which then renders itself.
async function loadRows() {
  const impacts = impactsParam(state.impacts);
  const result = await rowsGuard.run(() => (impacts ? fetchStatsEvents({ impacts }) : Promise.resolve(null)));
  if (!result.current) return false;
  if (result.value) {
    allRows = result.value.rows || [];
    disclaimers = result.value.disclaimers || {};
  } else {
    allRows = [];
  }
  rowsFor = impacts;
  return true;
}

function renderChips(focusName = null) {
  const box = $("stats-impact-chips");
  box.innerHTML = chipsHtml(state.impacts);
  const chip = focusName && box.querySelector(`[data-impact="${focusName}"]`);
  if (chip) chip.focus();   // re-rendering drops focus; keep keyboard users where they were
}

function showRowsError(err) {
  console.error("loadRows: fetch failed", err);
  const box = $("stats-error");
  box.textContent = "Could not load the Stats data for that selection. Change the impact levels again to retry.";
  box.style.display = "";
}

// Reload the rows for the current impact selection, then redraw. The guard throws only for the newest fetch,
// so an older failure cannot show an error over newer data.
async function reloadAndRender() {
  try {
    if (!(await loadRows())) return;
  } catch (err) {
    showRowsError(err);
    return;
  }
  populateFilters();
  render();
}

async function changeImpacts(name) {
  state.impacts = toggleImpact(state.impacts, name);
  renderChips(name);
  if (state.sub !== "reaction") { await reloadAndRender(); return; }
  // Market reaction fetches its own leaderboard: draw it now, and refresh the shared rows (Year list, other
  // sub-tabs) in parallel. A failed events call must not block the leaderboard.
  render();
  try {
    if (await loadRows()) populateFilters();
  } catch (err) {
    showRowsError(err);
  }
}

function populateFilters() {
  const years = yearsPresent(allRows);
  // An empty row set (nothing selected, or no releases at that level) must not wipe the choices made so far.
  if (state.year && years.length && !years.includes(Number(state.year))) state.year = "";
  $("stats-year").innerHTML = '<option value="">All</option>'
    + years.map((y) => `<option value="${y}"${String(y) === state.year ? " selected" : ""}>${y}</option>`).join("");
  $("stats-month").innerHTML = '<option value="">All</option>'
    + MONTHS.map((m, i) => `<option value="${i + 1}"${String(i + 1) === state.month ? " selected" : ""}>${m}</option>`).join("");
  const titles = [...new Set(allRows.filter((r) => r.status !== "not_scoreable").map((r) => r.event_title))].sort();
  if (titles.length && !titles.includes(state.event)) state.event = titles[0];
  $("stats-event").innerHTML = titles
    .map((t) => `<option value="${escapeHtml(t)}"${t === state.event ? " selected" : ""}>${escapeHtml(t)}</option>`).join("");
}

function attachHandlers() {
  if (handlersAttached) return;
  handlersAttached = true;
  $("stats-year").addEventListener("change", (e) => { state.year = e.target.value; render(); });
  $("stats-month").addEventListener("change", (e) => { state.month = e.target.value; render(); });
  $("stats-event").addEventListener("change", (e) => { state.event = e.target.value; render(); });
  $("stats-instrument").addEventListener("change", (e) => { state.instrument = e.target.value; render(); });
  $("view-stats").addEventListener("keydown", (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    const rowEl = e.target.closest("tr[data-reaction-event]");
    if (!rowEl) return;
    e.preventDefault();   // Space must not scroll the page
    openReactionEvent(rowEl.dataset.reactionEvent);
  });
  $("view-stats").addEventListener("click", (e) => {
    const sub = e.target.closest("[data-sub]");
    if (sub) { setSub(sub.dataset.sub); return; }
    const chip = e.target.closest("[data-impact]");
    if (chip) { changeImpacts(chip.dataset.impact); return; }
    const reactionRow = e.target.closest("tr[data-reaction-event]");
    if (reactionRow) { openReactionEvent(reactionRow.dataset.reactionEvent); return; }
    if (e.target.closest(".reaction-close")) { hideReactionDetail(); return; }
    const method = e.target.closest("[data-method]");
    if (method) { state.method = method.dataset.method; render(); return; }
    if (e.target.closest(".info-close")) { hideInfo(); return; }
    const rowEl = e.target.closest("tr[data-row]");
    if (rowEl) {
      const row = allRows.find((r) => rowKey(r) === rowEl.dataset.row);
      if (row) showInfo(rowEl.dataset.component || null, row, rowEl.dataset.view);
      return;
    }
    const trigger = e.target.closest("[data-metric]");
    if (trigger) showInfo(trigger.dataset.metric);
  });
}

function setSub(name) {
  if (!SUBTABS.includes(name)) return;
  state.sub = name;
  // The rows may be stale if the chips changed on the Market reaction sub-tab (or that reload failed).
  if (name !== "reaction" && rowsFor !== impactsParam(state.impacts)) { render(); reloadAndRender(); return; }
  render();
}

// metric: the component list to fetch (or null); row/view: a clicked release, whose readings sit
// beside the component list (spec §5 click-through). An info icon passes a metric only.
async function showInfo(metric, row = null, view = "tier1") {
  const box = $("stats-info");
  const token = ++infoToken;
  const close = '<button type="button" class="info-close" aria-label="Close">×</button>';
  const readings = row ? readingsHtml(row, view) : "";
  let components = "";
  try {
    if (metric) components = componentsHtml(await fetchStatsComponents(metric));
  } catch (err) {
    if (token !== infoToken) return;
    console.error("showInfo: fetch failed", err);
    if (!row) {
      box.textContent = "Could not load that breakdown.";
      box.style.display = "";
      return;
    }
    components = '<div class="info-panel">Could not load the inputs list.</div>';
  }
  if (token !== infoToken) return;
  box.innerHTML = close + `<div class="info-pair">${readings}${components}</div>`;
  box.style.display = "";
  box.scrollIntoView({ behavior: "smooth", block: "nearest" });
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
  $("stats-instrument-wrap").style.display = sub === "reaction" ? "" : "none";
  $("stats-window-note").style.display = sub === "reaction" ? "" : "none";
  const noImpacts = !impactsParam(state.impacts);
  const emptyMessage = noImpacts ? NO_IMPACT_MESSAGE : undefined;   // undefined -> the default empty-state text

  const filtered = filterRows(allRows, { year: state.year, month: state.month, event: sub === "combined" ? state.event : "" });

  // Brief card: the next release is independent of the Year/Month filters (it follows the impact chips).
  $("stats-brief").innerHTML = sub === "reaction" ? "" : briefCardHtml(pickNextRow(allRows, new Date(), sub), sub, disclaimers, state.impacts.length < 4);

  const pre = preNewsDisclaimer(filtered, sub, disclaimers);
  const box = $("stats-disclaimer");
  box.textContent = pre ? disclaimers.pre_news : "";
  box.style.display = pre ? "" : "none";

  const table = newestFirst(filtered);
  if (sub === "combined") {
    $("stats-combined-body").innerHTML = table.length ? table.map(combinedRowHtml).join("") : emptyRowHtml(7, emptyMessage);
    $("stats-combined-recon-note").textContent = reconstructedDisclaimer(filtered, sub, disclaimers) ? disclaimers.reconstructed : "";
    if (noImpacts) {
      $("stats-chart").innerHTML = "";
      $("stats-scoreboard").innerHTML = "";
    } else {
      renderChartAndScoreboard(token);
    }
  } else if (sub === "tier1") {
    $("stats-tier1-body").innerHTML = noImpacts ? emptyRowHtml(5, emptyMessage) : tier1BodyHtml(filtered);
    $("stats-recon-note").textContent = reconstructedDisclaimer(filtered, sub, disclaimers) ? disclaimers.reconstructed : "";
  } else if (sub === "news") {
    $("stats-news-body").innerHTML = table.length ? table.map(sentimentRowHtml).join("") : emptyRowHtml(6, emptyMessage);
  } else {
    renderReaction(token, noImpacts);
  }
}

async function renderChartAndScoreboard(token) {
  const chartBox = $("stats-chart");
  const boardBox = $("stats-scoreboard");
  const year = state.year ? { year: state.year } : {};
  const impacts = { impacts: impactsParam(state.impacts) };
  try {
    const [chart, board] = await Promise.all([
      state.event ? fetchStatsChart({ event: state.event, method: state.method, ...year, ...impacts }) : Promise.resolve({ unit: "", points: [] }),
      fetchStatsScoreboard({ ...(state.event ? { event: state.event } : {}), ...year, ...(state.month ? { month: state.month } : {}), ...impacts }),
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

// ---- Market reaction sub-tab -------------------------------------------------

// The instrument, impact, Year and Month selection as API params (the drill-down adds the event).
function reactionParams() {
  return {
    instrument: state.instrument, impacts: impactsParam(state.impacts),
    ...(state.year ? { year: state.year } : {}), ...(state.month ? { month: state.month } : {}),
  };
}

async function renderReaction(token, noImpacts) {
  const head = $("stats-reaction-head");
  const body = $("stats-reaction-body");
  const notes = $("stats-reaction-disclaimers");
  const error = $("stats-reaction-error");
  error.style.display = "none";
  if (!head.innerHTML) head.innerHTML = leaderboardHeadHtml();
  const select = $("stats-instrument");
  if (!select.options.length) select.innerHTML = instrumentOptionsHtml([state.instrument], state.instrument);   // before the first response
  if (noImpacts) {
    body.innerHTML = emptyRowHtml(6, NO_IMPACT_MESSAGE);
    notes.innerHTML = "";
    hideReactionDetail();
    return;
  }
  try {
    const board = await fetchReactionLeaderboard(reactionParams());
    if (token !== renderToken) return;
    state.instrument = board.instrument;   // the response decides; the select is chosen by value, never by index
    $("stats-instrument").innerHTML = instrumentOptionsHtml(board.instruments, board.instrument);
    head.innerHTML = leaderboardHeadHtml(board.quantile);
    body.innerHTML = leaderboardRowsHtml(board.rows);
    notes.innerHTML = reactionDisclaimersHtml(board.disclaimers);
    if (state.reactionEvent && (board.rows || []).some((r) => r.event_title === state.reactionEvent)) {
      showReactionDetail();    // keep an open drill-down in step with the new filters
    } else {
      hideReactionDetail();
    }
  } catch (err) {
    if (token !== renderToken) return;
    console.error("renderReaction: fetch failed", err);
    body.innerHTML = "";
    notes.innerHTML = "";
    hideReactionDetail();
    error.textContent = "Could not load the Market reaction data. Change a filter or switch sub-tab to retry.";
    error.style.display = "";
  }
}

function openReactionEvent(eventTitle) {
  state.reactionEvent = eventTitle;
  showReactionDetail();
}

async function showReactionDetail() {
  const box = $("stats-reaction-detail");
  const token = ++detailToken;
  try {
    const data = await fetchReactionReleases({ ...reactionParams(), event: state.reactionEvent });
    if (token !== detailToken) return;
    box.innerHTML = releasesHtml(data);
    box.style.display = "";
    box.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (err) {
    if (token !== detailToken) return;
    console.error("showReactionDetail: fetch failed", err);
    box.innerHTML = releasesErrorHtml();
    box.style.display = "";
  }
}

function hideReactionDetail() {
  detailToken++;   // a still-pending drill-down must not reopen the panel
  state.reactionEvent = "";
  const box = $("stats-reaction-detail");
  box.innerHTML = "";
  box.style.display = "none";
}
