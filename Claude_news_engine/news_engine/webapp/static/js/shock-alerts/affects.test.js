// webapp/static/js/shock-alerts/affects.test.js
import test from "node:test";
import assert from "node:assert/strict";
import { affectsLineHtml } from "./affects.js";

const WITH_LEANS = [
  { symbol: "XAUUSD", channel: "safe_haven", lean: "buy", lean_why: "safe-haven demand [convention]" },
  { symbol: "US30", channel: "risk_sentiment", lean: "sell", lean_why: "risk-off [convention]" },
  { symbol: "EURUSD", channel: "usd_relationship", lean: "mixed", lean_why: "rate link contested [Layer2]" },
];

test("each instrument shows its own buy / sell-off / no-clear-lean label", () => {
  const html = affectsLineHtml(WITH_LEANS);
  assert.match(html, /XAUUSD \(safe haven\)[\s\S]*potential BUY/);
  assert.match(html, /US30 \(risk sentiment\)[\s\S]*potential SELL-OFF/);
  assert.match(html, /EURUSD \(usd relationship\)[\s\S]*no clear lean/);
  assert.match(html, /Typical reaction, not a trade signal\./);
});

test("the reason is shown but the provenance tags are not", () => {
  const html = affectsLineHtml(WITH_LEANS);
  assert.ok(html.includes("risk-off"));
  assert.ok(!html.includes("[convention]"));
  assert.ok(!html.includes("[Layer2]"));
});

test("rows stored before leans existed keep the compact one-line form", () => {
  const html = affectsLineHtml([
    { symbol: "XAUUSD", channel: "safe_haven" },
    { symbol: "US30", channel: "risk_sentiment" },
  ]);
  assert.equal(html, "XAUUSD (safe_haven), US30 (risk_sentiment)");
});

test("no tracked instruments says so", () => {
  assert.equal(affectsLineHtml([]), "none currently tracked");
  assert.equal(affectsLineHtml(undefined), "none currently tracked");
});

test("an unrecognized lean value falls back to no clear lean instead of throwing", () => {
  assert.match(affectsLineHtml([{ symbol: "XAUUSD", channel: "c", lean: "moon" }]), /no clear lean/);
});

test("symbol, channel and reason text are HTML-escaped", () => {
  const html = affectsLineHtml([{ symbol: "<b>X</b>", channel: "c", lean: "buy", lean_why: "<script>alert(1)</script>" }]);
  assert.ok(!html.includes("<script>"));
  assert.ok(!html.includes("<b>X</b>"));
});
