// webapp/static/js/dashboard/article-progression.js
//
// articleProgressionEntryHtml moved verbatim from app.js (was around line
// 660 there). See card-flip.js's articleProgressionContent() for how the
// resulting strings get assembled into the flip-back panel.

import { escapeHtml, directionClass, directionPct, directionLabel } from "../format.js";

// Renders one progression entry — a recorded article-based snapshot plus
// (if any) the top-3 articles that drove it. Weight_pct/usd_sentiment
// come straight from scoring/backtest_accumulator.py's
// _build_top_contributions(), computed once at scoring time and stored
// alongside that exact prediction — never recomputed here.
export function articleProgressionEntryHtml(entry, isLatest) {
  const dClass = directionClass(entry.direction);
  const pct = directionPct(entry.probability, entry.direction);
  const when = new Date(entry.scored_at_utc).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  const contribsHtml = (entry.top_contributions || []).map((c) => {
    const leanClass = c.usd_sentiment > 0 ? "bullish" : c.usd_sentiment < 0 ? "bearish" : "neutral";
    return `<div class="progression-article">
      <a href="${escapeHtml(c.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(c.title)}</a>
      <span class="progression-article-meta ${leanClass}">${escapeHtml(c.source)} · ${c.weight_pct}% weight</span>
    </div>`;
  }).join("");
  return `<div class="progression-entry ${isLatest ? "progression-entry-latest" : ""}">
    <div class="progression-entry-head">
      <span class="gauge-label ${dClass}">${directionLabel(entry.direction)} ${pct}%</span>
      <span class="progression-entry-when">${when} · ${entry.article_count} articles</span>
    </div>
    ${contribsHtml || '<div class="low-signal-warning">⚠ No individual article stood out — this read came from broad, low-signal coverage, not a genuinely on-topic signal.</div>'}
  </div>`;
}
