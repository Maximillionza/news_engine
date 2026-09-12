// webapp/static/js/staleness.js
//
// renderFeedStaleness/renderAccumulatorStaleness — moved verbatim from
// app.js's original definitions (Task 6), byte-for-byte, zero logic
// change. They read/write specific DOM elements by id, unlike format.js's
// pure functions, which is why they were never moved into format.js.

const feedStalenessEl = document.getElementById("feed-staleness-indicator");
const accumulatorStalenessEl = document.getElementById("accumulator-staleness-indicator");

// Thresholds from docs/calendar-feed-staleness-policy.md's operational
// policy table — display-only, no scoring impact.
const FEED_STALENESS_FRESH_SECONDS = 3 * 60 * 60;
const FEED_STALENESS_AGING_SECONDS = 24 * 60 * 60;

export function renderFeedStaleness(seconds) {
  if (feedStalenessEl == null) return;
  if (seconds == null) {
    feedStalenessEl.textContent = "Calendar feed: never fetched yet";
    feedStalenessEl.className = "feed-staleness stale";
    return;
  }
  const minutes = Math.round(seconds / 60);
  const label = minutes < 60 ? `${minutes}m ago` : `${(seconds / 3600).toFixed(1)}h ago`;
  const level = seconds < FEED_STALENESS_FRESH_SECONDS ? "fresh" : seconds < FEED_STALENESS_AGING_SECONDS ? "aging" : "stale";
  feedStalenessEl.textContent = `Forex Factory feed last checked: ${label}`;
  feedStalenessEl.className = `feed-staleness ${level}`;
}

// The article-based accumulator (scripts/run_accumulator.py) is a
// SEPARATE process from this Flask app — it can silently stop running
// (crash, never started, sandbox reset) while the dashboard keeps
// serving whatever article_prediction it last computed, with nothing
// otherwise distinguishing that from a healthy "no new articles" quiet
// period. Tighter thresholds than the calendar feed's — this pipeline is
// meant to poll far more frequently near a live event (down to 5-minute
// intervals, see webapp/scheduler.py's FINAL_INTERVAL_SECONDS), so an
// hour of silence is already a real signal something's wrong, not routine.
const ACCUMULATOR_STALENESS_FRESH_SECONDS = 20 * 60;
const ACCUMULATOR_STALENESS_AGING_SECONDS = 60 * 60;

export function renderAccumulatorStaleness(seconds) {
  if (accumulatorStalenessEl == null) return;
  if (seconds == null) {
    accumulatorStalenessEl.textContent = "Article accumulator: never run — start scripts/run_accumulator.py";
    accumulatorStalenessEl.className = "feed-staleness stale";
    return;
  }
  const minutes = Math.round(seconds / 60);
  const label = minutes < 60 ? `${minutes}m ago` : `${(seconds / 3600).toFixed(1)}h ago`;
  const level = seconds < ACCUMULATOR_STALENESS_FRESH_SECONDS ? "fresh" : seconds < ACCUMULATOR_STALENESS_AGING_SECONDS ? "aging" : "stale";
  accumulatorStalenessEl.textContent = `Article accumulator last checked: ${label}`;
  accumulatorStalenessEl.className = `feed-staleness ${level}`;
}
