// webapp/static/js/stats/reaction.js
//
// Pure string builders for the Market reaction sub-tab (market-reaction spec sections 4.2 and 7): the event
// leaderboard and the per-event drill-down. No DOM access, so every function runs under plain Node.
// All dynamic text goes through escapeHtml.
import { escapeHtml } from "../format.js";
import { toSast, leanLabel, leanText, verdictChip, emptyRowHtml } from "./rows.js";

// How each cluster credit is worded. A cluster never gives exclusive credit, so shared/matched are labelled as such.
export const CREDIT_LABELS = {
  solo_hit: "Solo hit",
  solo_miss: "Solo miss",
  shared_hit: "Shared driver",
  shared_miss: "Shared miss",
  matched: "Matched the move",
  overruled: "Overruled",
  no_reaction: "No reaction",
  no_signal: "No signal",
  no_data: "No data",
};

const REACTION_LABELS = { buy: "Buy", sell: "Sell", none: "No reaction" };
const METHOD_LABELS = { tier1: "Tier 1", news: "News", combined: "Combined" };
const DEFAULT_QUANTILE = 0.75;   // the baseline the service uses; only a fallback if a response omits it
const LEADERBOARD_COLUMNS = 6;

// Signed to 2 decimals with an optional suffix: 0.2 -> "+0.20%", -0.254 -> "-0.25%", null -> "-".
function signed(value, suffix = "") {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  const text = Number(value).toFixed(2);
  if (Number(text) === 0) return `0.00${suffix}`;
  return `${Number(value) > 0 ? "+" : ""}${text}${suffix}`;
}

// "95% interval 44%-100%" from a Wilson interval given as fractions, or "" when there is none.
function intervalTitle(rate) {
  const interval = rate && rate.interval;
  if (!Array.isArray(interval) || interval.length !== 2) return "";
  return `95% interval ${Math.round(interval[0] * 100)}%-${Math.round(interval[1] * 100)}%`;
}

function titleAttr(text) { return text ? ` title="${escapeHtml(text)}"` : ""; }

// "k of n", plus the percent only when the service sends one (it hides percentages on small samples).
function rateText(rate) {
  const base = `${rate.k} of ${rate.n}`;
  return rate.percent === null || rate.percent === undefined ? base : `${base} (${Math.round(rate.percent)}%)`;
}

// ---- leaderboard ------------------------------------------------------------------

// Column headers. Chance level is 1 - quantile: with the 75th percentile baseline an ordinary window "moves the
// market" about 25% of the time, so a rate near that is noise.
export function leaderboardHeadHtml(quantile) {
  const q = Number(quantile);
  const chance = Math.round((1 - (Number.isFinite(q) && q > 0 && q < 1 ? q : DEFAULT_QUANTILE)) * 100);
  return "<tr><th>Event</th><th>Impact</th><th>Releases</th>"
    + `<th>Moved the market<div class="meta-text-sm">Chance level for an ordinary window is ${chance}%</div></th>`
    + "<th>Avg 5-min move</th><th>Engine call right</th></tr>";
}

export function reactionEmptyHtml() { return emptyRowHtml(LEADERBOARD_COLUMNS); }

// solo / shared / in_conflict count RELEASES THAT MOVED THE MARKET (credits that need a reaction), not all
// releases, so the line says "of the {moved} that moved" and is never read as a share of the Releases column.
function hitLineHtml(row) {
  const hitRate = row.hit.percent === null || row.hit.percent === undefined ? ""
    : ` &middot; <span class="hit-rate"${titleAttr(intervalTitle(row.hit))}>${Math.round(row.hit.percent)}%</span>`;
  return `<div class="meta-text-sm">of the ${escapeHtml(row.reaction.k)} that moved: ${escapeHtml(row.hit.k)} went the implied way `
    + `(solo ${escapeHtml(row.solo)}, shared ${escapeHtml(row.shared)}, in conflict ${escapeHtml(row.in_conflict)})${hitRate}</div>`;
}

export function leaderboardRowHtml(row) {
  const impact = escapeHtml(row.impact_effective) + (row.impact_inferred ? " (inferred)" : "");
  const few = row.few ? ' <span class="chip chip-none">few releases</span>' : "";
  const moved = `<span${titleAttr(intervalTitle(row.reaction))}>${escapeHtml(rateText(row.reaction))}</span>`;
  const avg = row.avg_move_pct === null || row.avg_move_pct === undefined ? "-"
    : `<span title="Positive = moved the way the surprise implied">${signed(row.avg_move_pct, "%")}</span>`;
  const engine = row.engine ? `${escapeHtml(row.engine.k)} of ${escapeHtml(row.engine.n)}` : "n/a";
  return `<tr class="row-click" tabindex="0" data-reaction-event="${escapeHtml(row.event_title)}">`
    + `<td>${escapeHtml(row.event_title)}${few}</td><td>${impact}</td><td>${escapeHtml(row.releases)}</td>`
    + `<td>${moved}${hitLineHtml(row)}</td><td>${avg}</td><td>${engine}</td></tr>`;
}

export function leaderboardRowsHtml(rows) {
  return rows && rows.length ? rows.map(leaderboardRowHtml).join("") : reactionEmptyHtml();
}

// The two disclaimers from the response, verbatim and escaped; "" when the response has none.
export function reactionDisclaimersHtml(disclaimers) {
  if (!disclaimers) return "";
  return [disclaimers.association, disclaimers.cluster].filter(Boolean)
    .map((text) => `<div class="meta-text-sm">${escapeHtml(text)}</div>`).join("");
}

// The Instrument select's options, chosen BY VALUE (the list is alphabetical, so the index means nothing).
export function instrumentOptionsHtml(instruments, selected) {
  return (instruments || []).map((symbol) =>
    `<option value="${escapeHtml(symbol)}"${symbol === selected ? " selected" : ""}>${escapeHtml(symbol)}</option>`).join("");
}

// ---- drill-down -------------------------------------------------------------------

function creditLabel(credit) { return CREDIT_LABELS[credit] || "No data"; }

function plural(n, word) { return `${n} ${word}${n === 1 ? "" : "s"}`; }

// The events released in the same minute (the other ones when `ownTitle` is given), each with its lean and credit,
// then the "+N lower-impact events" note for cluster members hidden by the impact filter, then the overlap note.
export function clusterNoteHtml(release, ownTitle) {
  const members = (release.cluster || []).filter((m) => ownTitle === undefined || m.event_title !== ownTitle);
  const parts = [];
  if (members.length) {
    parts.push('<ul class="cluster-list">' + members.map((m) =>
      `<li>${escapeHtml(m.event_title)} (${escapeHtml(m.impact_effective)}): ${escapeHtml(leanLabel(m.lean))} - ${escapeHtml(creditLabel(m.credit))}</li>`).join("") + "</ul>");
  }
  const hidden = Number(release.hidden_in_cluster) || 0;
  if (hidden > 0) parts.push(`<div class="meta-text-sm">+${hidden} lower-impact ${hidden === 1 ? "event" : "events"} at the same time</div>`);
  if (release.note) parts.push(`<div class="meta-text-sm">${escapeHtml(release.note)}</div>`);
  return parts.join("");
}

function moveCell(release) {
  if (release.move === null || release.move === undefined) return "-";
  const typical = release.threshold === null || release.threshold === undefined ? ""
    : ` (typical ${Number(release.threshold).toFixed(2)})`;
  return `${signed(release.move_pct, "%")}<div class="meta-text-sm">${signed(release.move)}${typical}</div>`;
}

function engineCell(call) {
  if (!call) return "-";
  return `${escapeHtml(METHOD_LABELS[call.method] || call.method)} ${verdictChip(call.verdict)}`;
}

function releaseRowHtml(release, data) {
  const sast = toSast(release.event_time_utc);
  const lean = leanText({ [data.instrument]: release.lean });
  const reaction = REACTION_LABELS[release.reaction] || "No data";
  return `<tr><td>${escapeHtml(sast.date)} ${escapeHtml(sast.time)}</td><td>${moveCell(release)}</td>`
    + `<td>${escapeHtml(reaction)}</td><td>${lean}</td><td>${escapeHtml(creditLabel(release.credit))}</td>`
    + `<td>${clusterNoteHtml(release, data.event_title) || "-"}</td><td>${engineCell(release.engine_call)}</td></tr>`;
}

// One event's releases, in the order given (the service sends newest first).
export function releasesHtml(data) {
  const close = '<button type="button" class="reaction-close" aria-label="Close">&times;</button>';
  const head = `${close}<strong>${escapeHtml(data.event_title)}</strong> `
    + `<span class="meta-text-sm">${escapeHtml(data.instrument)}, ${plural((data.releases || []).length, "release")}, newest first, times in SAST</span>`;
  const releases = data.releases || [];
  if (!releases.length) return `<div class="info-panel reaction-detail">${head}<div class="meta-text-sm">No releases match this selection.</div></div>`;
  return `<div class="info-panel reaction-detail">${head}<div class="stats-scroll"><table class="stats-table">`
    + "<tr><th>Date (SAST)</th><th>Instrument move</th><th>Reaction</th><th>Implied lean</th><th>Credit</th>"
    + "<th>Others at the same time</th><th>Engine call</th></tr>"
    + releases.map((r) => releaseRowHtml(r, data)).join("") + "</table></div></div>";
}
