// webapp/static/js/calendar/grid.js
import { html } from "../../vendor/lit-html.js";
import { repeat } from "../../vendor/directives/repeat.js";
import { escapeHtml } from "../format.js";

function cellTemplate(cell, onCellClick) {
  if (!cell) return html`<div class="cal-cell"></div>`;
  const classes = ["cal-cell"];
  if (cell.isToday) classes.push("today");
  if (cell.isNearestUpcoming) classes.push("nearest-upcoming");
  if (cell.hasEstimatedOnly) classes.push("has-estimated-only");
  return html`<div class="${classes.join(" ")}" data-date="${cell.dateStr}" @click=${() => onCellClick(cell.dateStr)}>
    ${cell.day}<br>
    ${cell.dots.map((d) => html`<span class="cal-dot ${d.impactClass}" title="${escapeHtml(d.title)}"></span>`)}
    ${cell.estimatedDots.map((d) => html`<span class="cal-dot cal-dot-estimated" title="${escapeHtml(d.title)}"></span>`)}
  </div>`;
}

export function calendarGridTemplate(gridViewModel, onCellClick) {
  const blanks = Array.from({ length: gridViewModel.leadingBlanks }, () => null);
  const allCells = blanks.concat(gridViewModel.cells);
  return html`${repeat(
    allCells,
    (cell, i) => cell?.dateStr ?? `blank-${i}`,
    (cell) => cellTemplate(cell, onCellClick),
  )}`;
}
