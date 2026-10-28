// webapp/static/js/shock-alerts/grading.js
//
// B10 (2026-10-28) K13: pure helpers (no DOM) for the Shock Alerts grading table and hit-rate summary.
// Each alert's stored lean is graded per symbol at two anchors (when it was published, when we detected
// it) against the 5-minute move and that hour's baseline; see alerting/lean_grading.py. Hit rate counts
// only right and wrong calls; no-move, no-lean, no-data and no-baseline are shown as counts, never in n.
import { escapeHtml } from "../format.js";

const DASH = "—";
const ANCHORS = ["published", "detected"];

const SAST_STAMP = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Africa/Johannesburg", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
  hourCycle: "h23",
});

const sign = (n) => (n < 0 ? "-" : "+");

// "+7 min"; a dash when the publication time is unknown.
export function lagText(row) {
  const age = row ? row.age_minutes : null;
  if (age === null || age === undefined) return DASH;
  return `+${age} min`;
}

// Gold in pips (1.00 = 100 pips), the index in points.
export function moveText(symbol, move) {
  if (move === null || move === undefined || Number.isNaN(move)) return DASH;
  if (symbol === "XAUUSD") {
    const pips = Math.round(Math.abs(move) * 100);
    return `${pips === 0 ? "+" : sign(move)}${pips} pips`;
  }
  const pts = Math.abs(move).toFixed(1);
  return `${pts === "0.0" ? "+" : sign(move)}${pts} pts`;
}

function pctText(counts) {
  return counts.n ? `${((counts.right / counts.n) * 100).toFixed(1)}%` : "n/a";
}

// "62.5% (5 of 8)"
function hitRateShort(counts) {
  return `${pctText(counts)} (${counts.right} of ${counts.n})`;
}

// "62.5% (5 of 8) · no move 4 · no lean 6 · no data 1 · no baseline 0"
export function hitRateText(counts) {
  return `${hitRateShort(counts)} · no move ${counts.no_move} · no lean ${counts.no_lean}`
    + ` · no data ${counts.no_data} · no baseline ${counts.no_baseline}`;
}

const verdictLabel = (verdict) => String(verdict || "").replace(/_/g, " ");

// One graded cell: the stored lean, a verdict badge and the measured move.
export function verdictCellHtml(grade) {
  const verdict = String(grade.verdict || "");
  const lean = grade.lean ? escapeHtml(grade.lean) : DASH;
  return `<span class="verdict-lean">${lean}</span> `
    + `<span class="verdict-badge verdict-${escapeHtml(verdict)}">${escapeHtml(verdictLabel(verdict))}</span> `
    + `<span class="meta-text-sm">${escapeHtml(moveText(grade.symbol, grade.move))}</span>`;
}

function detectedText(utcIso) {
  const when = new Date(utcIso);
  return Number.isNaN(when.getTime()) ? DASH : SAST_STAMP.format(when);
}

function gradeCell(row, symbol, anchor) {
  const grade = (row.grades || []).find((g) => g.symbol === symbol && g.anchor === anchor);
  return `<td>${grade ? verdictCellHtml(grade) : DASH}</td>`;
}

// The per-alert grading table; "" when there are no rows (the caller shows the empty notice).
export function gradingTableHtml(rows, symbols) {
  if (!rows || rows.length === 0) return "";
  const syms = symbols || [];
  const fixed = ["Detected (SAST)", "Severity", "Headline", "Incident", "Lag", "Polarity", "Country"];
  const head = fixed.concat(syms.flatMap((s) => ANCHORS.map((a) => `${s} ${a}`)))
    .map((h) => `<th>${escapeHtml(h)}</th>`).join("");
  const body = rows.map((row) => {
    const graded = (row.grades || []).length > 0;
    const cells = graded
      ? syms.flatMap((s) => ANCHORS.map((a) => gradeCell(row, s, a))).join("")
      : `<td colspan="${Math.max(1, syms.length * ANCHORS.length)}" class="meta-text-sm">not graded yet</td>`;
    return `<tr>`
      + `<td>${escapeHtml(detectedText(row.detected_at_utc))}</td>`
      + `<td>${escapeHtml(row.severity)}</td>`
      + `<td>${escapeHtml(row.headline)}</td>`
      + `<td>#${escapeHtml(row.incident_id)}</td>`
      + `<td>${escapeHtml(lagText(row))}</td>`
      + `<td>${escapeHtml(row.polarity || DASH)}</td>`
      + `<td>${escapeHtml(row.country || DASH)}</td>`
      + `${cells}</tr>`;
  }).join("");
  return `<div class="stats-scroll"><table class="shock-grading-table"><thead><tr>${head}</tr></thead>`
    + `<tbody>${body}</tbody></table></div>`;
}

function anchorRows(perAnchor) {
  return ANCHORS.map((a) => `<tr><td>${a}</td><td>${escapeHtml(hitRateText(perAnchor[a]))}</td></tr>`).join("");
}

// Overall, per-symbol and per-incident hit rates for the requested range.
export function summaryHtml(summary) {
  if (!summary) return "";
  const minutes = summary.window_minutes;
  const symbolBlocks = (summary.symbols || []).filter((s) => summary.by_symbol && summary.by_symbol[s]).map((s) =>
    `<tr><th colspan="2">${escapeHtml(s)}</th></tr>${anchorRows(summary.by_symbol[s])}`).join("");
  const incidents = (summary.incidents || []).map((i) =>
    `<tr><td>Incident #${escapeHtml(i.incident_id)}</td><td>${escapeHtml(i.headline)}</td>`
    + `<td>${escapeHtml(i.alerts)}</td><td>${escapeHtml(hitRateText(i.published))}</td>`
    + `<td>${escapeHtml(hitRateText(i.detected))}</td></tr>`).join("");
  const ungraded = summary.ungraded_alerts
    ? `<div class="meta-text-sm">${escapeHtml(summary.ungraded_alerts)} alert(s) not graded yet (graded weekly, Sunday 20:00 SAST).</div>`
    : "";
  return `<div class="shock-grading-summary">`
    + `<div class="meta-text-sm">Hit rate = right / (right + wrong) on the ${escapeHtml(minutes)}-minute move beyond that hour's baseline. `
    + `Typical reaction, not a trade signal.</div>`
    + `<table class="shock-grading-table"><thead><tr><th colspan="2">Overall</th></tr></thead>`
    + `<tbody>${anchorRows(summary.overall)}${symbolBlocks}</tbody></table>`
    + (incidents
      ? `<div class="stats-scroll"><table class="shock-grading-table"><thead><tr><th>Incident</th><th>Headline</th>`
        + `<th>Alerts</th><th>Published hit rate</th><th>Detected hit rate</th></tr></thead>`
        + `<tbody>${incidents}</tbody></table></div>`
      : "")
    + ungraded + `</div>`;
}

// "?from=...&to=..." with only the parts given; "" for none.
export function rangeQuery(from, to) {
  const parts = [];
  if (from) parts.push(`from=${encodeURIComponent(from)}`);
  if (to) parts.push(`to=${encodeURIComponent(to)}`);
  return parts.length ? `?${parts.join("&")}` : "";
}
