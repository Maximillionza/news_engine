// webapp/static/js/calendar/date-panel.js
//
// The click-to-inspect date panel. State (selectedCalendarDateStr,
// calendarPanelClosed) is owned by calendar-poll.js and passed in —
// this module is a pure template + one fetch-triggering function.

import { html, render } from "../../vendor/lit-html.js";
import { escapeHtml, directionLabel, directionPct, confidenceColorClass } from "../format.js";
import { fetchCalendarDate } from "../api.js";

function callLineTemplate(symbol, call) {
  if (!call) return html`<div class="date-panel-call">${escapeHtml(symbol)}: <span style="color:#888">no call recorded</span></div>`;
  const essenceLine = call.direction != null && call.direction !== "pending"
    ? html`<b>${directionLabel(call.direction)} ${directionPct(call.probability, call.direction)}%</b>`
    : html`<span style="color:#888">no essence score yet</span>`;
  const articleLine = call.article_prediction
    ? html`<div style="font-size:12px;color:#666">📰 ${directionLabel(call.article_prediction.direction)} ${directionPct(call.article_prediction.probability, call.article_prediction.direction)}% (${call.article_prediction.article_count} articles)</div>`
    : html``;
  const printLine = call.print_prediction
    ? (() => {
        const pct = Math.round(call.print_prediction.confidence * 100);
        return html`<div style="font-size:12px">📊 ${escapeHtml(call.print_prediction.direction)} <span class="${confidenceColorClass(pct)}">(${pct}% conf.)</span></div>`;
      })()
    : html``;
  return html`<div class="date-panel-call">${escapeHtml(symbol)}: ${essenceLine}${articleLine}${printLine}</div>`;
}

function eventTemplate(e) {
  if (e.estimated) {
    return html`<div class="date-panel-event">
      <b>${escapeHtml(e.title)}</b> <span class="estimated-badge" title="FRED month-ahead estimate — not yet confirmed by Forex Factory's own feed">ESTIMATED</span><br>
      <span style="font-size:12px;color:#888">Exact time not yet confirmed — Forex Factory hasn't reached this occurrence's week yet.</span>
    </div>`;
  }
  return html`<div class="date-panel-event">
    <b>${escapeHtml(e.title)}</b> (${escapeHtml(e.impact ?? "")})<br>
    <span style="font-size:12px;color:#888">forecast ${escapeHtml(e.forecast ?? "—")}, previous ${escapeHtml(e.previous ?? "—")}, actual ${escapeHtml(e.actual ?? "—")}</span>
    ${Object.entries(e.calls || {}).map(([symbol, call]) => callLineTemplate(symbol, call))}
  </div>`;
}

export async function showDatePanel(dateStr, state) {
  state.selectedCalendarDateStr = dateStr;
  state.calendarPanelClosed = false;
  const panel = document.getElementById("calendar-date-panel");
  const title = document.getElementById("calendar-date-panel-title");
  const body = document.getElementById("calendar-date-panel-body");
  title.textContent = new Date(`${dateStr}T00:00:00`).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
  panel.style.display = "";

  const data = await fetchCalendarDate(dateStr);
  if (!data.events || data.events.length === 0) {
    render(html`<div style="color:#888">No tracked events on this date.</div>`, body);
    return;
  }
  render(html`${data.events.map(eventTemplate)}`, body);
}
