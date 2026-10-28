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
  assert.ok(html.includes("Weights: Tier 1 only (no news number to blend") && !html.includes("30% news"));
  assert.ok(!html.includes("no news call"));
  const unsized = readingsHtml({ ...noNews, detail: { ...noNews.detail, news_lean: 0.25 } }, "combined");
  assert.ok(unsized.includes("News lean +0.25") && unsized.includes("so no number")
    && !unsized.includes("to size it: no news call"));
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

// ---- Brent crude beside the nowcast (information only) -------------------------------------------
const BRENT = { snapshot_price: 90, snapshot_price_date: "2026-10-12", release_price: 92.5, release_price_date: "2026-10-13",
  change_pct: 2.78, source: "FRED DCOILBRENTEU (EIA daily Brent)" };

test("CPI readings show Brent at the nowcast snapshot vs before the release, information only at 0% weight", () => {
  for (const view of ["tier1", "combined"]) {
    const html = readingsHtml({ ...ROW, detail: { ...DETAIL, brent: BRENT } }, view);
    assert.ok(html.includes("Brent crude (information only, 0% weight): $90.00 on 2026-10-12 at the nowcast snapshot"), view);
    assert.ok(html.includes("→ $92.50 on 2026-10-13 before release (+2.78%)"), view);
    assert.ok(html.includes("source FRED/EIA"), view);
    assert.ok(!html.includes("Brent not available"), view);
  }
});

test("a falling Brent shows a minus sign and a flat one shows no sign", () => {
  const down = readingsHtml({ ...ROW, detail: { ...DETAIL, brent: { ...BRENT, release_price: 85, change_pct: -5.56 } } }, "tier1");
  assert.ok(down.includes("$85.00 on 2026-10-13 before release (-5.56%)"));
  const flat = readingsHtml({ ...ROW, detail: { ...DETAIL, brent: { ...BRENT, release_price: 90, change_pct: 0 } } }, "tier1");
  assert.ok(flat.includes("(0.00%)"));
});

test("a null Brent says it is not available and invents no price", () => {
  for (const brent of [null, undefined]) {
    const html = readingsHtml({ ...ROW, detail: { ...DETAIL, brent } }, "tier1");
    assert.ok(html.includes("Brent crude (information only, 0% weight): Brent not available"));
    assert.ok(!html.includes("$"));
  }
});

test("when only one side has a price the other is said to be missing and no change is shown", () => {
  const html = readingsHtml({ ...ROW, detail: { ...DETAIL, brent: { ...BRENT, snapshot_price: null, snapshot_price_date: null, change_pct: null } } }, "tier1");
  assert.ok(html.includes("no price at the nowcast snapshot") && html.includes("$92.50 on 2026-10-13 before release"));
  assert.ok(!html.includes("%)"));
});

test("Brent is not mentioned where there is no nowcast (no snapshot, or a hand-logged call)", () => {
  const none = readingsHtml({ ...ROW, tier1: null, detail: { ...DETAIL, nowcast_value: null, nowcast_as_of_utc: null, brent: null } }, "tier1");
  assert.ok(!none.includes("Brent"));
  const hand = readingsHtml({ ...ROW, event_title: "PPI m/m", tier1: { predicted: null, verdict: "right", leans: { XAUUSD: "sell" }, note: "hand-logged", kind: null },
    detail: { ...DETAIL, nowcast_value: null, hand_logged: { value: "0.4% hot", confidence: "Likely", source: "BLS" }, brent: null } }, "tier1");
  assert.ok(!hand.includes("Brent"));
});

test("Brent text is escaped and adds no weight or call", () => {
  const evil = readingsHtml({ ...ROW, detail: { ...DETAIL, brent: { ...BRENT, snapshot_price_date: "<b>x</b>", release_price_date: "<i>y</i>" } } }, "combined");
  assert.ok(!evil.includes("<b>") && !evil.includes("<i>"));
  const plainHtml = readingsHtml({ ...ROW, detail: { ...DETAIL, brent: BRENT } }, "combined");
  assert.ok(plainHtml.includes("Weights: 70% Tier 1 / 30% news"));                  // unchanged: Brent carries no weight
});

test("Combined readings name the News call", () => {
  const lower = readingsHtml({ ...ROW, news_call: "lower" }, "combined");
  assert.ok(lower.includes("News call: lower"));
  const none = readingsHtml({ ...ROW, news_call: "no_call" }, "combined");
  assert.ok(none.includes("News call: none (|lean| under 0.2, pre-registered)"));
});
