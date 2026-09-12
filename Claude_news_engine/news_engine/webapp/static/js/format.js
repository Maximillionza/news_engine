// webapp/static/js/format.js
//
// Pure formatting/label functions, zero DOM dependency (except where noted),
// extracted verbatim from the original monolithic app.js
// (docs/superpowers/specs/2026-09-11-frontend-rendering-refactor-design.md).

// escapeHtml originally used `document.createElement("div").textContent =`
// (DOM-dependent) -- rewritten here as pure string replacement so it can be
// unit-tested under plain Node with no jsdom, and so it works identically
// inside a lit-html template context. Escapes the same 5 characters the
// browser's own textContent/innerHTML round-trip would.
export function escapeHtml(str) {
  const s = str ?? "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Batch 10 (dashboard-review-2026-09-11.md live UI walkthrough): "1% and
// 100% render as identical plain text" — no threshold treatment
// distinguished a genuinely strong call from a noise-level one anywhere in
// the UI. Not a new scale — a visual rendering of the 3-tier split this
// codebase's own confidence language already uses elsewhere (Tier 1's
// Certain/Likely/Guessing tags).
export function confidenceColorClass(pct) {
  if (pct >= 66) return "confidence-high";
  if (pct >= 33) return "confidence-medium";
  return "confidence-low";
}

export function formatEventDateTime(eventTimeUtc) {
  return new Date(eventTimeUtc).toLocaleString();
}

// Local-calendar-date ISO string (YYYY-MM-DD). NOT Date.toISOString() —
// that converts to UTC first, which would shift the date for any
// non-UTC+0 local timezone (e.g. SAST/UTC+2 local midnight becomes the
// previous day at 22:00 UTC) and desync the cell's data-date from the
// cell's own displayed day number.
export function toIsoDateLocal(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function directionLabel(direction) {
  if (direction === "bullish") return "BUY";
  if (direction === "bearish") return "SELL";
  return "INDECISIVE";
}

export function directionClass(direction) {
  if (direction === "bullish") return "bullish";
  if (direction === "bearish") return "bearish";
  return "neutral";
}

// `probability` is P(bullish) throughout this whole system (0-100%, 50%
// = neutral) - the SAME single number for either direction, which is
// exactly what made "SELL 39%" ambiguous (is 39% the sell confidence, or
// the leftover bullish reading?). This returns P(that specific direction)
// instead: BUY shows the raw number as-is, SELL shows its complement
// (100 - raw) - e.g. a raw 39% BUY-probability reads as "SELL 61%", each
// direction now genuinely "out of its own 100," never sharing one scale.
export function directionPct(probability, direction) {
  const raw = Math.round(probability * 100);
  return direction === "bearish" ? 100 - raw : raw;
}

export function gaugeSvg(pct, direction) {
  // `pct` is already the per-direction display percentage (directionPct())
  // — the arc fills to match the number shown, not the raw shared-scale
  // probability, so a "SELL 61%" gauge visually reads as 61% filled, not 39%.
  const color = direction === "bullish" ? "#2e7d32" : direction === "bearish" ? "#c62828" : "#888";
  const circumference = 2 * Math.PI * 26;
  const filled = (pct / 100) * circumference;
  return `
    <svg width="70" height="70" viewBox="0 0 70 70">
      <circle cx="35" cy="35" r="26" fill="none" stroke="#eee" stroke-width="7"/>
      <circle cx="35" cy="35" r="26" fill="none" stroke="${color}" stroke-width="7"
        stroke-dasharray="${filled} ${circumference}" stroke-linecap="round"
        transform="rotate(-90 35 35)"/>
      <text x="35" y="39" text-anchor="middle" font-size="13" font-weight="bold">${pct}%</text>
    </svg>`;
}

let _bullBearScaleCounter = 0;

// Bear(red)<->Bull(green) horizontal scale with a sliding indicator at
// `probability` (0.0-1.0) — where the article-based read sits relative to
// full-bear/full-bull, not "confidence in the shown direction." Directly
// addresses the ambiguity of a bare "SELL 39%" label: visually, 39% is
// obviously a mild lean toward the red end, not a strong one, without
// requiring the reader to do (100 - 39)% math in their head.
export function bullBearScaleSvg(probability) {
  const id = `bbgrad-${_bullBearScaleCounter++}`;
  const pct = Math.max(0, Math.min(100, probability * 100));
  const trackX = 4, trackWidth = 172;
  const indicatorX = trackX + (pct / 100) * trackWidth;
  return `
    <svg width="180" height="34" viewBox="0 0 180 34">
      <defs>
        <linearGradient id="${id}" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#c62828"/>
          <stop offset="50%" stop-color="#ddd"/>
          <stop offset="100%" stop-color="#2e7d32"/>
        </linearGradient>
      </defs>
      <rect x="${trackX}" y="12" width="${trackWidth}" height="7" rx="3.5" fill="url(#${id})"/>
      <line x1="90" y1="8" x2="90" y2="23" stroke="#999" stroke-width="1"/>
      <circle cx="${indicatorX}" cy="15.5" r="6.5" fill="#222" stroke="#fff" stroke-width="2"/>
      <text x="${trackX}" y="33" font-size="9" fill="#c62828" font-weight="bold">BEAR</text>
      <text x="${trackX + trackWidth}" y="33" font-size="9" fill="#2e7d32" font-weight="bold" text-anchor="end">BULL</text>
    </svg>`;
}

// Shared by the essence-only gauge and the article-based read — both
// compare a previous (direction, probability) pair against a current one.
// previous_probability/probability are remapped onto THEIR OWN direction's
// basis via directionPct(), same as everywhere else — comparing
// "confidence within the same call" only makes sense when the direction
// didn't change. A flip (e.g. previous BUY -> now SELL) isn't a numeric
// delta at all; showing "-9pp" for a full reversal would misrepresent it
// as a minor wobble instead of the call flipping entirely. Returns '' if
// there's nothing meaningful to show (identical direction+probability).
export function buildDiffStripHtml(prevDirection, prevProbability, currDirection, currProbability) {
  const prevPct = directionPct(prevProbability, prevDirection);
  const currPct = directionPct(currProbability, currDirection);

  if (prevDirection !== currDirection) {
    return `<div class="diff-strip reversed">
      <div>↔ Reversed: was <b>${directionLabel(prevDirection)} ${prevPct}%</b> → now <b>${directionLabel(currDirection)} ${currPct}%</b></div>
    </div>`;
  }

  const delta = currPct - prevPct;
  if (delta === 0) return '';
  return `<div class="diff-strip">${diffPieSvg(prevPct, delta)}
    <div>Previous: <b>${directionLabel(prevDirection)} ${prevPct}%</b><br>
    <span class="${delta >= 0 ? 'delta-up' : 'delta-down'}">${delta >= 0 ? '▲' : '▼'} ${delta >= 0 ? '+' : ''}${delta}pp → now ${currPct}%</span></div>
  </div>`;
}

export function diffPieSvg(previousPct, delta) {
  const isUp = delta >= 0;
  const baseColor = "#a5d6a7";
  const deltaColor = isUp ? "#2e7d32" : "#c62828";
  const basePct = isUp ? previousPct : previousPct + delta; // the smaller of the two — the part that's "still true"
  const deltaAbs = Math.abs(delta);
  return `
    <svg width="44" height="44" viewBox="0 0 32 32">
      <circle r="14" cx="16" cy="16" fill="#eee" pathLength="100"/>
      <circle r="14" cx="16" cy="16" fill="transparent" stroke="${baseColor}" stroke-width="14" pathLength="100"
        stroke-dasharray="${basePct} 100" transform="rotate(-90 16 16)"/>
      <circle r="14" cx="16" cy="16" fill="transparent" stroke="${deltaColor}" stroke-width="14" opacity="0.9" pathLength="100"
        stroke-dasharray="${deltaAbs} 100" stroke-dashoffset="${-basePct}" transform="rotate(-90 16 16)"/>
    </svg>`;
}

export function dayStripHtml(eventTimeUtc) {
  const today = new Date();
  const eventDate = new Date(eventTimeUtc);
  const cells = [];
  for (let offset = -4; offset <= 10; offset++) {
    const d = new Date(today);
    d.setDate(d.getDate() + offset);
    const isToday = offset === 0;
    const isEvent = d.toDateString() === eventDate.toDateString();
    const classes = ["day-cell"];
    if (isToday) classes.push("today");
    if (isEvent) classes.push("event");
    cells.push(`<div class="${classes.join(" ")}">${d.getDate()}</div>`);
  }
  return `<div class="day-strip">${cells.join("")}</div>`;
}

// tier1DirectionLabel (2026-09-07): Tier 1's own predicted_direction is
// "bullish"/"bearish"/"neutral" -- directionLabel() maps those to
// BUY/SELL/INDECISIVE. A Tier 1 row logged as confidence="Guessing" with
// no confident call also carries predicted_direction="neutral" by
// convention (see scoring/backtest.py's Tier1Prediction docstring) -- this
// wrapper exists so the label reads "NO CALL" for that specific case
// instead of the generic "INDECISIVE" a real neutral essence/article call
// would show, since Tier 1 neutral means something different (no
// confident directional judgment was possible) from essence/article
// neutral (a genuinely balanced read).
export function tier1DirectionLabel(tier1) {
  if (tier1.confidence === "Guessing" && tier1.predicted_direction === "neutral") return "NO CALL";
  return directionLabel(tier1.predicted_direction);
}
