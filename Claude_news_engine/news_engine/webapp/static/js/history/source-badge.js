// webapp/static/js/history/source-badge.js
// The small provenance label after an event title on the History tab. 'live' (Forex Factory)
// and 'fred' (the same-day FRED fast path) get none; the official-publisher labels are the
// `source` values webapp/release_poller.py writes (data_layer/official_actuals PUBLISHER_SOURCES).
const SOURCE_LABELS = {
  seeded: "seeded",
  live_web_fallback: "web-sourced",
  cloud_web_fallback: "cloud-researched",
  bls: "BLS",
  bea: "BEA",
  census: "Census",
  eia: "EIA",
  fed: "Fed",
  treasury: "Treasury",
};

export function sourceBadge(source) {
  // hasOwn: a source named "constructor" must not pick up an inherited property.
  if (!Object.hasOwn(SOURCE_LABELS, source)) return "";
  return ` <span class="meta-text-sm">(${SOURCE_LABELS[source]})</span>`;
}
