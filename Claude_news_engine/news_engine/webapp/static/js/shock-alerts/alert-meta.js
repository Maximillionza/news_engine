// webapp/static/js/shock-alerts/alert-meta.js
// Pure helpers (no DOM) for the extra shock-alert card lines: story age, context
// tags and the no-US-link cap badge. Old rows carry nulls and render nothing.
import { escapeHtml } from "../format.js";

const SAST_TIME = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Africa/Johannesburg", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
});

// "Published 14:42 SAST · +2 min · Fresh"; "" when the age is unknown.
export function freshnessText(row) {
  if (!row.first_published_utc || row.age_minutes === null || row.age_minutes === undefined) return "";
  const published = new Date(row.first_published_utc);
  if (Number.isNaN(published.getTime())) return "";
  return `Published ${SAST_TIME.format(published)} SAST · +${row.age_minutes} min · ${row.freshness_band}`;
}

// "Where: RU · US link: none · Polarity: escalation", known parts only.
// Returned HTML-escaped because the card inserts it as markup.
export function contextTagsText(row) {
  const parts = [];
  if (row.country) parts.push(`Where: ${row.country}`);
  if (row.us_link) parts.push(`US link: ${String(row.us_link).replace(/_/g, " ")}`);
  if (row.polarity) parts.push(`Polarity: ${row.polarity}`);
  return escapeHtml(parts.join(" · "));
}

// Badge shown when the classifier's severity was capped for lack of a US link.
export function capBadgeHtml(row) {
  if (row.capped_no_us_link !== true) return "";
  let text = "capped: no US or global-supply link";
  if (row.original_severity && row.original_severity !== row.severity) {
    text += ` (classifier said ${row.original_severity})`;
  }
  return ` <span style="color:#ef6c00">${escapeHtml(text)}</span>`;
}
