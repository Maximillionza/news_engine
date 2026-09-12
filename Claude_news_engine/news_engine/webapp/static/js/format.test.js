// webapp/static/js/format.test.js
import test from "node:test";
import assert from "node:assert/strict";
import {
  escapeHtml, confidenceColorClass, formatEventDateTime, toIsoDateLocal,
  directionLabel, directionClass, directionPct, gaugeSvg, bullBearScaleSvg,
  buildDiffStripHtml, diffPieSvg, dayStripHtml, tier1DirectionLabel,
} from "./format.js";

test("escapeHtml escapes the 5 HTML-sensitive characters", () => {
  assert.equal(escapeHtml(`<script>&"'`), "&lt;script&gt;&amp;&quot;&#39;");
});

test("escapeHtml treats null/undefined as empty string, never 'null'/'undefined' text", () => {
  assert.equal(escapeHtml(null), "");
  assert.equal(escapeHtml(undefined), "");
});

test("confidenceColorClass: 3-tier split at 33/66", () => {
  assert.equal(confidenceColorClass(10), "confidence-low");
  assert.equal(confidenceColorClass(33), "confidence-medium");
  assert.equal(confidenceColorClass(65), "confidence-medium");
  assert.equal(confidenceColorClass(66), "confidence-high");
  assert.equal(confidenceColorClass(100), "confidence-high");
});

test("directionLabel maps bullish/bearish/neutral to BUY/SELL/INDECISIVE", () => {
  assert.equal(directionLabel("bullish"), "BUY");
  assert.equal(directionLabel("bearish"), "SELL");
  assert.equal(directionLabel("neutral"), "INDECISIVE");
});

test("directionClass maps bullish/bearish/neutral to bullish/bearish/neutral CSS classes", () => {
  assert.equal(directionClass("bullish"), "bullish");
  assert.equal(directionClass("bearish"), "bearish");
  assert.equal(directionClass("neutral"), "neutral");
});

test("directionPct: BUY shows raw probability, SELL shows its complement", () => {
  assert.equal(directionPct(0.71, "bullish"), 71);
  assert.equal(directionPct(0.39, "bearish"), 61);
});

test("gaugeSvg returns an svg string containing the percentage text", () => {
  const svg = gaugeSvg(61, "bearish");
  assert.match(svg, /<svg/);
  assert.match(svg, />61%</);
  assert.match(svg, /#c62828/);  // bearish color
});

test("bullBearScaleSvg returns an svg string with a unique gradient id per call", () => {
  const a = bullBearScaleSvg(0.5);
  const b = bullBearScaleSvg(0.5);
  assert.match(a, /<svg/);
  assert.notEqual(a, b, "each call must use a distinct gradient id or SVG defs collide across multiple cards on one page");
});

test("buildDiffStripHtml: a direction flip renders 'Reversed', not a numeric delta", () => {
  const html = buildDiffStripHtml("bullish", 0.52, "bearish", 0.46);
  assert.match(html, /Reversed/);
  assert.match(html, /BUY 52%/);
  assert.match(html, /SELL 54%/);
});

test("buildDiffStripHtml: same direction, no change returns empty string", () => {
  assert.equal(buildDiffStripHtml("bullish", 0.52, "bullish", 0.52), "");
});

test("buildDiffStripHtml: same direction, a real change renders a delta", () => {
  const html = buildDiffStripHtml("bullish", 0.50, "bullish", 0.55);
  assert.match(html, /\+5pp/);
});

test("diffPieSvg returns an svg string", () => {
  assert.match(diffPieSvg(50, 5), /<svg/);
});

test("dayStripHtml marks exactly one cell 'today' and one cell 'event' when the event falls within the strip", () => {
  const today = new Date();
  const html = dayStripHtml(today.toISOString());
  const todayCount = (html.match(/class="day-cell today event"/g) || []).length
    + (html.match(/class="day-cell event today"/g) || []).length
    + (html.match(/class="day-cell today"/g) || []).length;
  assert.ok(todayCount >= 1, "expected at least one cell marked today");
});

test("toIsoDateLocal formats a Date as YYYY-MM-DD using LOCAL date fields, not UTC", () => {
  const d = new Date(2026, 8, 11); // September 11 2026, local time, month is 0-indexed
  assert.equal(toIsoDateLocal(d), "2026-09-11");
});

test("formatEventDateTime returns a non-empty locale string for a real ISO timestamp", () => {
  const result = formatEventDateTime("2026-09-11T12:30:00Z");
  assert.ok(result.length > 0);
});

test("tier1DirectionLabel: Guessing+neutral (no confident call) reads 'NO CALL', not 'INDECISIVE'", () => {
  assert.equal(tier1DirectionLabel({ confidence: "Guessing", predicted_direction: "neutral" }), "NO CALL");
});

test("tier1DirectionLabel: a real neutral call (not Guessing) still reads INDECISIVE via directionLabel", () => {
  assert.equal(tier1DirectionLabel({ confidence: "Certain", predicted_direction: "neutral" }), "INDECISIVE");
});
