// webapp/static/js/api.js
//
// Thin fetch wrappers. No DOM, no rendering — throws a real Error on a
// non-ok response so callers can catch/handle uniformly, same behavior
// dashboard-poll.js / calendar-poll.js (Tasks 6-7) already need.

async function fetchJson(url, options) {
  const resp = await fetch(url, options);
  if (!resp.ok) throw new Error(`HTTP ${resp.status} for ${url}`);
  return resp.json();
}

export function fetchPredictions() {
  return fetchJson("/api/predictions");
}

export function fetchCalendar() {
  return fetchJson("/api/calendar");
}

export function fetchCalendarMonthAhead() {
  return fetchJson("/api/calendar/monthahead");
}

export function fetchCalendarDate(dateStr) {
  return fetchJson(`/api/calendar/date/${dateStr}`);
}

export function fetchHistory() {
  return fetchJson("/api/history");
}

export function fetchHistoryStats() {
  return fetchJson("/api/history/stats");
}

export function fetchShockAlerts() {
  return fetchJson("/api/shock-alerts");
}

// B4 O6: every job, feed, classifier and Tier 1 capture graded ok/amber/red.
export function fetchHealth() {
  return fetchJson("/api/health");
}

export function fetchArticleHistory(symbol, eventTitle) {
  return fetchJson(`/api/predictions/${symbol}/article_history?event_title=${encodeURIComponent(eventTitle)}`);
}

export function fetchEventHistory(eventTitle) {
  return fetchJson(`/api/event_history?title=${encodeURIComponent(eventTitle)}`);
}

export async function postAddSymbol(ticker) {
  const resp = await fetch("/api/symbols", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker }),
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.error || "Could not add symbol");
  }
}

export function deleteSymbol(ticker) {
  return fetch(`/api/symbols/${ticker}`, { method: "DELETE" });
}

export function fetchStatsEvents(params = {}) {
  return fetchJson(`/api/stats/events?${new URLSearchParams(params)}`);
}

export function fetchStatsChart(params) {
  return fetchJson(`/api/stats/chart?${new URLSearchParams(params)}`);
}

export function fetchStatsScoreboard(params = {}) {
  return fetchJson(`/api/stats/scoreboard?${new URLSearchParams(params)}`);
}

export function fetchStatsComponents(metric) {
  return fetchJson(`/api/stats/components/${encodeURIComponent(metric)}`);
}

// Market reaction sub-tab. params: instrument, impacts (comma list), year, month (leaderboard); plus event (releases).
// The Stats helpers above take the same `impacts` param through their params object.
export function fetchReactionLeaderboard(params = {}) {
  return fetchJson(`/api/stats/reaction/leaderboard?${new URLSearchParams(params)}`);
}

export function fetchReactionReleases(params) {
  return fetchJson(`/api/stats/reaction/releases?${new URLSearchParams(params)}`);
}
