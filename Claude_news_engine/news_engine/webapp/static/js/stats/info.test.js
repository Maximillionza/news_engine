// webapp/static/js/stats/info.test.js
import test from "node:test";
import assert from "node:assert/strict";
import { componentsHtml, readingsHtml } from "./info.js";

test("lists every component with its source", () => {
  const html = componentsHtml({ title: "T", summary: "S", note: "N",
    components: [{ name: "Brent crude (daily)", detail: "d", source: "EIA" }] });
  assert.ok(html.includes("Brent crude (daily)") && html.includes("EIA") && html.includes("N"));
});

test("escapes component text", () => {
  assert.ok(!componentsHtml({ title: "<b>", summary: "", components: [] }).includes("<b>"));
});

// ---- B2: click-through readings ------------------------------------------------------
const DETAIL = { forecast_text: "0.3%", nowcast_value: 0.4, nowcast_as_of_utc: "2026-10-12T06:06:00+00:00",
  tier1_surprise: 0.1, news_lean: 0.5, news_scale: 0.2, news_surprise: 0.1, combined_surprise: 0.1,
  weights: { tier1: 0.7, news: 0.3 }, hand_logged: null, news_article_count: 7 };
const ROW = { event_title: "CPI m/m", event_time_utc: "2026-10-14T12:30:00+00:00", forecast: 0.3, forecast_text: "0.3%",
  tier1_tracked: true, nowcast_as_of_utc: DETAIL.nowcast_as_of_utc, detail: DETAIL,
  tier1: { predicted: 0.4, verdict: "right", leans: { XAUUSD: "sell" }, note: null, kind: "live" },
  combined: { predicted: 0.4, verdict: "right", leans: { XAUUSD: "sell" }, note: null, kind: "live" } };

test("Tier 1 readings: forecast, nowcast with its SAST as-of time, expected outcome and the 100% weight", () => {
  const html = readingsHtml(ROW, "tier1");
  assert.ok(html.includes("CPI m/m") && html.includes("2026-10-14 14:30 SAST"));
  assert.ok(html.includes("Forecast: 0.3%"));
  assert.ok(html.includes("Tier 1 nowcast: 0.4%") && html.includes("as of 2026-10-12 08:06 SAST"));
  assert.ok(html.includes("Expected outcome: hotter than consensus"));
  assert.ok(html.includes("Weights: Tier 1: 100% nowcast"));
  assert.ok(html.includes("Scored when a Cleveland Fed nowcast"));                 // criteria repeated for touch screens
  assert.ok(!html.includes("30% news"));
});

test("Tier 1 readings when no nowcast was recorded say so and invent nothing", () => {
  const html = readingsHtml({ ...ROW, tier1: null, detail: { ...DETAIL, nowcast_value: null, nowcast_as_of_utc: null } }, "tier1");
  assert.ok(html.includes("no nowcast was recorded before the release") && !html.includes("Expected outcome: hotter"));
});

test("Combined readings: 70/30 weights, the news lean and both contributions", () => {
  const html = readingsHtml(ROW, "combined");
  assert.ok(html.includes("Weights: 70% Tier 1 / 30% news"));
  assert.ok(html.includes("News lean +0.50") && html.includes("typical surprise 0.2") && html.includes("news surprise +0.1"));
  assert.ok(html.includes("Tier 1 70% × +0.1 = +0.07") && html.includes("news 30% × +0.1 = +0.03"));
  assert.ok(html.includes("combined surprise +0.1") && html.includes("Expected outcome: hotter than consensus"));
});

test("Combined readings without news say Tier 1 only, and explain a lean that had no size yet", () => {
  const noNews = { ...ROW, combined: { ...ROW.combined, note: "news_missing" },
    detail: { ...DETAIL, news_lean: null, news_scale: null, news_surprise: null, combined_surprise: 0.1 } };
  const html = readingsHtml(noNews, "combined");
  assert.ok(html.includes("Weights: Tier 1 only") && !html.includes("30% news"));
  const unsized = readingsHtml({ ...noNews, detail: { ...noNews.detail, news_lean: 0.25 } }, "combined");
  assert.ok(unsized.includes("News lean +0.25") && unsized.includes("no news call"));
});

test("hand-logged readings show the researched value, confidence and source and no invented weights", () => {
  const row = { ...ROW, event_title: "PPI m/m", nowcast_as_of_utc: null, combined: null,
    tier1: { predicted: null, verdict: "right", leans: { XAUUSD: "sell" }, note: "hand-logged", kind: null },
    detail: { ...DETAIL, nowcast_value: null, nowcast_as_of_utc: null, tier1_surprise: null, combined_surprise: null,
      news_lean: null, news_scale: null, news_surprise: null,
      hand_logged: { value: "0.4% hot", confidence: "Likely", source: "BLS" } } };
  for (const view of ["tier1", "combined"]) {
    const html = readingsHtml(row, view);
    assert.ok(html.includes("Tier 1 nowcast: direction only"));
    assert.ok(html.includes("Researched value: 0.4% hot") && html.includes("Confidence: Likely") && html.includes("Source: BLS"));
    assert.ok(!html.includes("100%") && !html.includes("70%"));
    assert.ok(html.includes("Scored when a hand-researched Tier 1 call"));
  }
  assert.ok(readingsHtml(row, "combined").includes("Combined: n/a"));
});

test("readings escape every served string", () => {
  const evil = { ...ROW, event_title: "<script>", detail: { ...DETAIL, forecast_text: "<b>",
    hand_logged: { value: "<i>", confidence: "<u>", source: "<s>" } } };
  const html = readingsHtml(evil, "tier1") + readingsHtml(evil, "combined");
  for (const tag of ["<script>", "<b>", "<i>", "<u>", "<s>"]) assert.ok(!html.includes(tag), tag);
});
