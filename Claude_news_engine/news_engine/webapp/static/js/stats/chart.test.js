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
