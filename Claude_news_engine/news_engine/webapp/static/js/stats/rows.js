// webapp/static/js/stats/rows.js
//
// Pure string builders for the Stats tab: table rows, chips, the next-release brief card, the
// scoreboard and the disclaimers. No DOM access, so every function is unit-testable under plain Node.
import { escapeHtml } from "../format.js";

const LEAN = { buy: "🟢 potential BUY", sell: "🔴 potential SELL-OFF", mixed: "⚪ no clear lean" };
const CPI_FAMILY = new Set(["CPI m/m", "Core CPI m/m"]);
const METHOD_LABEL = { tier1: "Tier 1 only", news: "News only", combined: "Combined (70/30)" };
const SAST_OFFSET_MS = 2 * 60 * 60 * 1000;

// Up to 2 decimals, no trailing zeros: 0.4 -> "0.4", 89 -> "89", 0.3499 -> "0.35".
function num(n) {
  return n === null || n === undefined || Number.isNaN(Number(n)) ? "—" : String(Number(Number(n).toFixed(2)));
}

export function verdictChip(verdict) {
  if (verdict === "right") return '<span class="chip chip-right">Right</span>';
  if (verdict === "wrong") return '<span class="chip chip-wrong">Wrong</span>';
  return '<span class="chip chip-none">No call</span>';
}

// One lean word ("🟢 potential BUY"); anything unknown reads as no clear lean.
export function leanLabel(lean) { return LEAN[lean] || LEAN.mixed; }

export function leanText(leans) {
  return Object.entries(leans || {}).map(([sym, l]) => `${escapeHtml(sym)} ${leanLabel(l)}`).join(" · ");
}

// UTC ISO time -> SAST date and time. South Africa is a fixed UTC+2 (no DST), so a plain +2h is exact
// and the date rolls over for releases after 22:00 UTC.
export function toSast(isoUtc) {
  const iso = new Date(new Date(isoUtc).getTime() + SAST_OFFSET_MS).toISOString();
  return { date: iso.slice(0, 10), time: iso.slice(11, 16) };
}

function dateCell(row) { return escapeHtml(toSast(row.event_time_utc).date); }

// A tracked row is scored from a nowcast snapshot (CPI family, or any row whose call has a snapshot kind);
// every other tracked row is a hand-logged, direction-only call.
function isNowcastRow(row) {
  return CPI_FAMILY.has(row.event_title) || Boolean(row.tier1 && row.tier1.kind);
}

// Which breakdown a Tier 1 row opens when clicked, or null (untracked rows have nothing to open).
export function componentFor(row) {
  if (!row.tier1_tracked) return null;
  return isNowcastRow(row) ? "cleveland_nowcast" : null;
}

// Scoring criteria shown on hover over a tracked Tier 1 row's info icon (spec §5), in plain language.
export const CRITERIA = {
  nowcast: "Scored when a Cleveland Fed nowcast was recorded before the release and a forecast and actual exist. "
    + "Call = nowcast above or below the forecast by at least one rounding step. Click the row for the inputs.",
  handLogged: "Scored when a hand-researched Tier 1 call was logged before the release. Direction only - no number.",
};

export function tier1Criteria(row) {
  if (!row.tier1_tracked) return "";
  return isNowcastRow(row) ? CRITERIA.nowcast : CRITERIA.handLogged;
}

// Identifies a row for the click-through panel (title + release instant is unique in event_history).
// Epoch milliseconds, so no raw UTC date string leaks into the SAST-only markup.
export function rowKey(row) { return `${row.event_title}|${Date.parse(row.event_time_utc)}`; }

// Attributes that make a tracked row open its readings; `component` adds the inputs list beside them.
function clickAttrs(row, view, component) {
  const comp = component ? ` data-component="${escapeHtml(component)}"` : "";
  return ` class="row-click" data-row="${escapeHtml(rowKey(row))}" data-view="${view}"${comp}`;
}

const RECON_CHIP = ' <span class="chip chip-none">reconstructed</span>';

// The row's Tier 1 input came from the backfill (Combined inherits it), so it is tagged in both tables.
function isReconstructed(row) { return Boolean(row.tier1 && row.tier1.kind === "reconstructed"); }
function reconTag(row) { return isReconstructed(row) ? RECON_CHIP : ""; }

export function tier1RowHtml(row) {
  const title = escapeHtml(row.event_title);
  if (row.status === "not_scoreable") {
    return `<tr class="row-off"><td>${title}</td><td>${dateCell(row)}</td><td colspan="3">No forecast — not scoreable</td></tr>`;
  }
  if (!row.tier1_tracked) {
    return `<tr class="row-off"><td>${title}</td><td>${dateCell(row)}</td><td colspan="3">Not tracked by Tier 1</td></tr>`;
  }
  // Tracked, but Tier 1 may have recorded no call for this occurrence (e.g. no nowcast was captured).
  const call = row.tier1 || { predicted: null, verdict: null, leans: {}, note: null, kind: null };
  const tag = reconTag(row);
  const predicted = call.predicted == null ? (call.note === "hand-logged" ? "hand-logged call" : "no call") : num(call.predicted);
  const actual = row.status === "pending" ? "pending" : escapeHtml(row.actual_text ?? "");
  const result = row.status === "pending" ? "pending" : verdictChip(call.verdict);
  const asOf = row.nowcast_as_of_utc
    ? `<div class="meta-text-sm">nowcast as of ${escapeHtml(sastText(row.nowcast_as_of_utc))}</div>` : "";
  const criteria = escapeHtml(tier1Criteria(row));
  const icon = ` <span class="info-btn row-info" role="img" title="${criteria}" aria-label="${criteria}">&#9432;</span>`;
  return `<tr${clickAttrs(row, "tier1", componentFor(row))}><td>${title}${icon}${tag}${asOf}</td>`
    + `<td>${dateCell(row)}</td><td>${escapeHtml(predicted)} <div class="meta-text-sm">${leanText(call.leans)}</div></td>`
    + `<td>${actual}</td><td>${result}</td></tr>`;
}

export function combinedRowHtml(row) {
  const title = escapeHtml(row.event_title);
  const c = row.combined;
  const cell = (call) => (call == null ? "—" : `${num(call.predicted)} ${verdictChip(call.verdict)}`);
  const flag = c && c.note === "news_missing" ? ' <span class="meta-text-sm">Tier 1 only</span>' : "";
  const attrs = row.tier1_tracked ? clickAttrs(row, "combined", "combined") : "";
  return `<tr${attrs}><td>${title}${reconTag(row)}</td><td>${dateCell(row)}</td><td>${escapeHtml(row.forecast_text ?? "")}</td>`
    + `<td>${cell(row.tier1)}</td><td>${cell(row.news)}</td><td>${row.tier1_tracked ? cell(c) + flag : "n/a"}</td>`
    + `<td>${row.status === "pending" ? "pending" : escapeHtml(row.actual_text ?? "")}</td></tr>`;
}

// Signed to 2 decimals: 0.5 -> "+0.50", -0.254 -> "-0.25".
export function signedLean(x) { return `${x > 0 ? "+" : ""}${Number(x).toFixed(2)}`; }

// "7 articles · lean +0.50" from the row's detail; "—" when neither is known.
function articlesLeanCell(row) {
  const d = row.detail || {};
  const parts = [];
  if (d.news_article_count != null) {
    const count = Number(d.news_article_count);
    parts.push(`${count} article${count === 1 ? "" : "s"}`);
  }
  if (d.news_lean != null) parts.push(`lean ${signedLean(d.news_lean)}`);
  return parts.length ? escapeHtml(parts.join(" · ")) : "—";
}

export function sentimentRowHtml(row) {
  const n = row.news;
  const title = escapeHtml(row.event_title);
  if (!n) {
    const why = row.pre_news_period ? "No news predictions before 12 Aug 2026" : "No news call";
    return `<tr class="row-off"><td>${title}</td><td>${dateCell(row)}</td><td>${articlesLeanCell(row)}</td>`
      + `<td colspan="3">${why}</td></tr>`;
  }
  return `<tr><td>${title}</td><td>${dateCell(row)}</td><td>${articlesLeanCell(row)}</td>`
    + `<td>${num(n.predicted)} <div class="meta-text-sm">${leanText(n.leans)}</div></td>`
    + `<td>${row.status === "pending" ? "pending" : escapeHtml(row.actual_text ?? "")}</td><td>${verdictChip(n.verdict)}</td></tr>`;
}

// ---- next-release brief card -------------------------------------------------

// Soonest upcoming row for this sub-tab's method: status pending, in the future, with a predicted number.
export function pickNextRow(rows, now, method) {
  const nowMs = now.getTime();
  const candidates = (rows || []).filter((r) => {
    const call = r[method];
    return r.status === "pending" && call && call.predicted != null && r.forecast != null
      && new Date(r.event_time_utc).getTime() > nowMs;
  });
  candidates.sort((a, b) => new Date(a.event_time_utc) - new Date(b.event_time_utc));
  return candidates[0] || null;
}

// "2026-10-16 14:30 SAST" from a UTC ISO time (South Africa is UTC+2, no DST).
export function sastText(iso) {
  const t = toSast(iso);
  return `${t.date} ${t.time} SAST`;
}

// Same rule as the server: within one step of the forecast's own published precision is "in line".
function stepOf(text) {
  const m = /-?\d+(?:\.(\d+))?/.exec(String(text ?? ""));
  return m ? Math.pow(10, -(m[1] ? m[1].length : 0)) : null;
}

export function expectedWord(forecast, predicted, forecastText) {
  const diff = predicted - forecast;
  const step = stepOf(forecastText);
  if (step !== null && Math.abs(diff) < step - 1e-9) return "in line with consensus";
  if (step === null && diff === 0) return "in line with consensus";
  return diff > 0 ? "hotter than consensus" : "cooler than consensus";
}

// `impactFiltered`: the impact chips are hiding some levels, so an empty card may just mean "none at these levels".
export function briefCardHtml(row, method, disclaimers, impactFiltered = false) {
  if (!row) {
    const none = impactFiltered ? "No upcoming call yet for the selected impact levels." : "No upcoming call yet.";
    return `<div class="brief-card"><b>Next release</b><div class="meta-text-sm">${none}</div></div>`;
  }
  const call = row[method];
  const unit = String(row.forecast_text ?? "").replace(/^-?[\d.,]+/, "").trim();
  const lean = leanText(call.leans);
  return `<div class="brief-card"><b>Next release: ${escapeHtml(row.event_title)}</b>`
    + `<div class="meta-text-sm">${escapeHtml(sastText(row.event_time_utc))}</div>`
    + `<div>Expected: ${expectedWord(row.forecast, call.predicted, row.forecast_text)} `
    + `(call ${escapeHtml(num(call.predicted) + unit)} vs forecast ${escapeHtml(row.forecast_text ?? "")})</div>`
    + (lean ? `<div>${lean}</div>` : "")
    + `<div class="meta-text-sm">${escapeHtml((disclaimers && disclaimers.typical_reaction) || "")}</div></div>`;
}

// ---- scoreboard --------------------------------------------------------------

// Counts only (no percentages): the spec keeps live and reconstructed calls, and blends with and
// without news, as separate populations even though the headline total adds them up.
function populationLines(m) {
  const kOfN = (c) => `${Number((c && c.right) || 0)} of ${Number((c && c.scored) || 0)}`;
  const lines = [];
  if (m.by_kind) lines.push(`live ${kOfN(m.by_kind.live)} · reconstructed ${kOfN(m.by_kind.reconstructed)}`);
  if (m.with_news) lines.push(`with news ${kOfN(m.with_news)}`);
  return lines.map((t) => `<div class="meta-text-sm">${t}</div>`).join("");
}

export function scoreboardHtml(sb, unit) {
  const u = escapeHtml(unit || "");
  const rows = ["tier1", "news", "combined"].map((key) => {
    const m = (sb.methods || {})[key] || { scored: 0, right: 0 };
    const pct = m.accuracy_shown ? ` (${Math.round(m.accuracy * 100)}%)` : "";
    const miss = m.mean_miss == null ? "" : `<div class="meta-text-sm">mean miss ${Number(m.mean_miss).toFixed(2)}${u}</div>`;
    return `<tr><td>${METHOD_LABEL[key]}</td><td>${m.right} of ${m.scored}${pct}${populationLines(m)}${miss}</td></tr>`;
  }).join("");
  return `<table class="stats-table"><tr><th>Method</th><th>Right calls</th></tr>${rows}</table>`
    + `<div class="meta-text-sm">${escapeHtml(sb.footnote || "")}</div>`;
}

// ---- filters and disclaimers -------------------------------------------------

export function yearsPresent(rows) {
  return [...new Set(rows.map((r) => Number(r.event_time_utc.slice(0, 4))))].sort((a, b) => a - b);
}

export function emptyRowHtml(columns, message = "No releases match this selection.") {
  return `<tr class="row-off"><td colspan="${columns}">${escapeHtml(message)}</td></tr>`;
}

// Tier 1 table body: tracked events under a "Tracked by Tier 1" caption, the rest under
// "Not tracked by Tier 1"; chronological (newest first) inside each group.
export function tier1BodyHtml(rows) {
  if (rows.length === 0) return emptyRowHtml(5);
  const ordered = orderTier1(rows);
  const tracked = ordered.filter((r) => r.tier1_tracked);
  const rest = ordered.filter((r) => !r.tier1_tracked);
  const caption = (text) => `<tr class="group-row"><th colspan="5">${text}</th></tr>`;
  return (tracked.length ? caption("Tracked by Tier 1") + tracked.map(tier1RowHtml).join("") : "")
    + (rest.length ? caption("Not tracked by Tier 1") + rest.map(tier1RowHtml).join("") : "");
}

// Tier 1 table order: tracked events first (those are the ones with calls), then the greyed rest;
// newest first within each group.
export function orderTier1(rows) {
  return [...rows].sort((a, b) => (Number(b.tier1_tracked) - Number(a.tier1_tracked))
    || b.event_time_utc.localeCompare(a.event_time_utc));
}

// Year/Month filters deliberately stay UTC-based: US releases are 12:30-19:00 UTC, so their SAST
// date equals their UTC date and the filter never disagrees with the date shown in the table.
export function filterRows(rows, { year, month, event } = {}) {
  return rows.filter((r) => {
    const y = Number(r.event_time_utc.slice(0, 4));
    const m = Number(r.event_time_utc.slice(5, 7));
    return (!year || y === Number(year)) && (!month || m === Number(month)) && (!event || r.event_title === event);
  });
}

export function preNewsDisclaimer(rows, subtab, disclaimers) {
  const applies = (subtab === "news" || subtab === "combined") && rows.some((r) => r.pre_news_period);
  return applies ? escapeHtml(disclaimers.pre_news) : "";
}

export function reconstructedDisclaimer(rows, subtab, disclaimers) {
  const applies = (subtab === "tier1" || subtab === "combined") && rows.some(isReconstructed);
  return applies ? escapeHtml(disclaimers.reconstructed) : "";
}

export function disclaimerHtml(rows, subtab, disclaimers) {
  return [preNewsDisclaimer(rows, subtab, disclaimers), reconstructedDisclaimer(rows, subtab, disclaimers)]
    .filter(Boolean).map((t) => `<div>${t}</div>`).join("");
}
