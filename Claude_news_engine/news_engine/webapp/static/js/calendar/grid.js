// webapp/static/js/calendar/grid.js
import { html } from "../../vendor/lit-html.js";
import { repeat } from "../../vendor/directives/repeat.js";

// Note on escapeHtml: not used in this file. Every value here (including
// `title="${...}"`, an attribute binding) flows through a normal lit-html
// `${}` binding, which already escapes it via direct DOM property/
// attribute assignment — never parsed as HTML. Calling format.js's
// escapeHtml() first would double-escape (see card.js's header comment
// for the full rule and the empirically-confirmed regression it caused).
function cellTemplate(cell, onCellClick) {
  if (!cell) return html`<div class="cal-cell"></div>`;
  const classes = ["cal-cell"];
  if (cell.isToday) classes.push("today");
  if (cell.isNearestUpcoming) classes.push("nearest-upcoming");
  if (cell.hasEstimatedOnly) classes.push("has-estimated-only");
  return html`<div class="${classes.join(" ")}" data-date="${cell.dateStr}" @click=${() => onCellClick(cell.dateStr)}>
    ${cell.day}<br>
    ${cell.dots.map((d) => html`<span class="cal-dot ${d.impactClass}" title="${d.title}"></span>`)}
    ${cell.estimatedDots.map((d) => html`<span class="cal-dot cal-dot-estimated" title="${d.title}"></span>`)}
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
