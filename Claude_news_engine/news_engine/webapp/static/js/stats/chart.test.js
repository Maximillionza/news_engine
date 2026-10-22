// webapp/static/js/stats/chart.test.js
import test from "node:test";
import assert from "node:assert/strict";
import { buildChartSvg } from "./chart.js";

const pts = [
  { month: "2026-08", label: "2026-08", forecast: 0.3, actual: 0.3, predicted: null, verdict: null },
  { month: "2026-09", label: "2026-09", forecast: 0.3, actual: 0.4, predicted: 0.4, verdict: "right" },
  { month: "2026-10", label: "2026-10", forecast: 0.3, actual: 0.2, predicted: 0.4, verdict: "wrong" },
];

test("right segments are green and wrong segments are red", () => {
  const svg = buildChartSvg({ unit: "%", points: pts });
  assert.ok(svg.includes("#2e7d32"));
  assert.ok(svg.includes("#c62828"));
});

test("a month with no call leaves a gap instead of a zero", () => {
  const svg = buildChartSvg({ unit: "%", points: pts });
  // 1 segment (Sep -> Oct) + 2 dots (Sep, Oct); nothing is drawn for Aug.
  assert.equal((svg.match(/data-predicted/g) || []).length, 3);
});

test("an empty series renders a message, not a broken chart", () => {
  assert.match(buildChartSvg({ unit: "%", points: [] }), /No scored releases/);
});

test("forecast and actual lines are always drawn", () => {
  const svg = buildChartSvg({ unit: "%", points: pts });
  assert.ok(svg.includes('data-line="forecast"') && svg.includes('data-line="actual"'));
});

test("the x-axis uses each point's label, not its month", () => {
  const svg = buildChartSvg({ unit: "%", points: pts.map((p, i) => ({ ...p, label: ["2026-08-10", "2026-09-11", "2026-10-12"][i] })) });
  assert.ok(svg.includes("2026-08-10") && svg.includes("2026-10-12"));
});

test("axis text is escaped", () => {
  const svg = buildChartSvg({ unit: "<u>", points: [{ ...pts[1], label: "<b>x</b>" }] });
  assert.ok(!svg.includes("<b>x") && !svg.includes("<u>"));
});

test("a single point still renders without NaN", () => {
  assert.ok(!buildChartSvg({ unit: "%", points: [pts[1]] }).includes("NaN"));
});

test("the viewBox follows the requested width so labels stay at their real size on a phone", () => {
  assert.ok(buildChartSvg({ unit: "%", points: pts }, { width: 340 }).includes('viewBox="0 0 340 '));
  assert.ok(buildChartSvg({ unit: "%", points: pts }).includes('viewBox="0 0 640 '));
});

test("narrow charts thin out x-axis labels so they do not overlap", () => {
  const many = Array.from({ length: 12 }, (_, i) => ({ ...pts[1], label: `2026-${String(i + 1).padStart(2, "0")}` }));
  const count = (svg) => (svg.match(/text-anchor="middle"/g) || []).length;
  assert.ok(count(buildChartSvg({ unit: "%", points: many }, { width: 320 })) < count(buildChartSvg({ unit: "%", points: many }, { width: 900 })));
});

test("a method with no calls keeps forecast and actual and says so", () => {
  const none = pts.map((p) => ({ ...p, predicted: null, verdict: null }));
  const news = buildChartSvg({ method: "news", unit: "%", points: none });
  assert.ok(news.includes('data-line="forecast"') && news.includes('data-line="actual"'));
  assert.equal((news.match(/data-predicted/g) || []).length, 0);
  assert.ok(news.includes("No News sentiment calls for this selection"));
  const t1 = buildChartSvg({ method: "tier1", unit: "%", points: none });
  assert.ok(t1.includes("No Tier 1 calls for this selection"));
});

test("pending (null-verdict) dots and segments are grey", () => {
  const svg = buildChartSvg({ unit: "%", points: [
    { label: "a", forecast: 0.3, actual: 0.3, predicted: 0.4, verdict: "right" },
    { label: "b", forecast: 0.3, actual: null, predicted: 0.5, verdict: null },
  ] });
  assert.ok(/data-predicted="seg"[^>]*stroke="#9e9e9e"/.test(svg));
  assert.ok(/data-predicted="dot"[^>]*fill="#9e9e9e"/.test(svg));
  assert.ok(!svg.includes("#c62828"));
});
