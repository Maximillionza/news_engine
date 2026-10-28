// webapp/static/js/shock-alerts/grading.test.js
import test from "node:test";
import assert from "node:assert/strict";
import {
  lagText, moveText, verdictCellHtml, hitRateText, gradingTableHtml, summaryHtml, rangeQuery,
} from "./grading.js";

const EMPTY = { n: 0, right: 0, wrong: 0, hit_rate: null, no_move: 0, no_lean: 0, no_data: 0, no_baseline: 0 };

test("lag shows the stored age in minutes, a dash when unknown", () => {
  assert.equal(lagText({ age_minutes: 7 }), "+7 min");
  assert.equal(lagText({ age_minutes: 0 }), "+0 min");
  assert.equal(lagText({ age_minutes: null }), "—");
  assert.equal(lagText({}), "—");
});

test("move text is pips for gold and points for the index", () => {
  assert.equal(moveText("XAUUSD", 1.234), "+123 pips");
  assert.equal(moveText("XAUUSD", -0.5), "-50 pips");
  assert.equal(moveText("US30", 45.25), "+45.3 pts");
  assert.equal(moveText("US30", -3), "-3.0 pts");
  assert.equal(moveText("US30", null), "—");
  assert.equal(moveText("XAUUSD", undefined), "—");
});

test("hit rate text counts only right and wrong in n and lists the non-calls", () => {
  const counts = { n: 8, right: 5, wrong: 3, hit_rate: 0.625, no_move: 4, no_lean: 6, no_data: 1, no_baseline: 0 };
  assert.equal(hitRateText(counts), "62.5% (5 of 8) · no move 4 · no lean 6 · no data 1 · no baseline 0");
  assert.equal(hitRateText(EMPTY), "n/a (0 of 0) · no move 0 · no lean 0 · no data 0 · no baseline 0");
});

test("verdict cell escapes the lean and carries the verdict class", () => {
  const html = verdictCellHtml({
    symbol: "XAUUSD", lean: "<b>", verdict: "no_move", move: 0.2, baseline: 1.0,
  });
  assert.ok(!html.includes("<b>"));
  assert.ok(html.includes("&lt;b&gt;"));
  assert.ok(html.includes("verdict-no_move"));
  assert.ok(html.includes("no move"));
  assert.ok(html.includes("+20 pips"));
});

test("verdict cell tolerates a missing lean and move", () => {
  const html = verdictCellHtml({ symbol: "US30", lean: null, verdict: "no_data", move: null });
  assert.ok(html.includes("verdict-no_data"));
  assert.ok(html.includes("no data"));
});

const ROW = {
  id: 1, detected_at_utc: "2026-10-20T08:00:00+00:00", severity: "High", headline: "Hormuz <closed>",
  incident_id: 1, age_minutes: 7, polarity: "escalation", country: "IR", grades: [],
};

test("grading table has the lag, polarity, country and per-symbol columns", () => {
  const html = gradingTableHtml([ROW], ["XAUUSD", "US30"]);
  for (const header of ["Lag", "Polarity", "Country", "XAUUSD published", "US30 detected", "Detected (SAST)"]) {
    assert.ok(html.includes(header), header);
  }
  assert.ok(html.includes("not graded yet"));
  assert.ok(html.includes("Hormuz &lt;closed&gt;"));
  assert.ok(html.includes("+7 min"));
  assert.ok(html.includes("10:00"), "08:00 UTC is 10:00 SAST");
});

test("graded rows show the verdict cell instead of the placeholder", () => {
  const row = {
    ...ROW,
    grades: [{ symbol: "XAUUSD", anchor: "published", lean: "buy", verdict: "right", move: 1.5, baseline: 1.0 }],
  };
  const html = gradingTableHtml([row], ["XAUUSD"]);
  assert.ok(html.includes("verdict-right"));
  assert.ok(!html.includes("not graded yet"));
});

test("empty table says nothing is graded", () => {
  assert.equal(gradingTableHtml([], ["XAUUSD"]), "");
});

test("summary shows overall, per symbol and per incident hit rates", () => {
  const counts = { ...EMPTY, n: 3, right: 2, wrong: 1, hit_rate: 0.6667, no_move: 2, no_lean: 1, no_data: 4, no_baseline: 5 };
  const summary = {
    window_minutes: 5,
    symbols: ["XAUUSD"],
    overall: { published: EMPTY, detected: counts },
    by_symbol: { XAUUSD: { published: EMPTY, detected: counts } },
    incidents: [{
      incident_id: 12, headline: "Hormuz <closed>", first_detected_utc: "2026-10-20T08:00:00+00:00",
      alerts: 2, published: EMPTY, detected: counts,
    }],
    ungraded_alerts: 4,
  };
  const html = summaryHtml(summary);
  assert.ok(html.includes("Incident #12"));
  assert.ok(html.includes("(2 of 3)"));
  assert.ok(html.includes("66.7%"));
  // Excluded verdicts are shown per incident for both anchors (counts is used for detected, EMPTY for published).
  const incidentRow = html.slice(html.indexOf("Incident #12"));
  assert.ok(incidentRow.includes("2 of 3) · no move 2 · no lean 1 · no data 4 · no baseline 5"));
  assert.ok(incidentRow.includes("n/a (0 of 0) · no move 0 · no lean 0 · no data 0 · no baseline 0"));
  assert.ok(html.includes("Hormuz &lt;closed&gt;"));
  assert.ok(html.includes("4"));
  assert.ok(html.includes("not graded yet"));
});

test("range query", () => {
  assert.equal(rangeQuery("2026-10-01", "2026-10-28"), "?from=2026-10-01&to=2026-10-28");
  assert.equal(rangeQuery("", ""), "");
  assert.equal(rangeQuery("2026-10-01", ""), "?from=2026-10-01");
  assert.equal(rangeQuery(undefined, "2026-10-28"), "?to=2026-10-28");
});
