// webapp/static/js/health/health-strip.test.js
import test from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";
import { formatAge, healthStripModel, renderHealthStrip, renderHealthUnavailable } from "./health-strip.js";

function item(key, status, detail = "", age = 60) {
  return {
    key, label: `Label ${key}`, status, last_success_utc: null, age_seconds: age,
    expected_every_seconds: 120, detail,
  };
}

function stripEl() {
  const dom = new JSDOM("<!doctype html><html><body><div id='health-strip'></div></body></html>");
  return dom.window.document.getElementById("health-strip");
}

test("formatAge picks seconds, minutes, hours or days", () => {
  assert.equal(formatAge(null), "never");
  assert.equal(formatAge(45), "45s");
  assert.equal(formatAge(90), "2m");
  assert.equal(formatAge(7200), "2.0h");
  assert.equal(formatAge(172800), "2.0d");
});

test("model lists red before amber, keeps payload order within each, drops ok", () => {
  const payload = {
    overall: "red",
    items: [
      item("a", "amber", "a detail"), item("b", "ok"), item("c", "red", "c detail"),
      item("d", "amber", "", 7200), item("e", "red", "e detail"),
    ],
  };
  const model = healthStripModel(payload);
  assert.equal(model.overall, "red");
  assert.deepEqual(model.chips.map((c) => c.status), ["red", "red", "amber", "amber"]);
  assert.deepEqual(model.chips.map((c) => c.text), [
    "Label c: c detail", "Label e: e detail", "Label a: a detail", "Label d: last success 2.0h ago",
  ]);
});

test("all-ok payload has no chips", () => {
  const model = healthStripModel({ overall: "ok", items: [item("a", "ok"), item("b", "ok")] });
  assert.equal(model.overall, "ok");
  assert.deepEqual(model.chips, []);
});

test("render escapes details and sets the overall class", () => {
  const el = stripEl();
  renderHealthStrip(el, { overall: "red", items: [item("x", "red", "<b>bad</b>")] });
  assert.equal(el.className, "health-strip red");
  assert.ok(!el.innerHTML.includes("<b>"));
  assert.match(el.innerHTML, /&lt;b&gt;bad&lt;\/b&gt;/);
  const chip = el.querySelector("span.health-chip.red");
  assert.ok(chip);
  assert.equal(chip.textContent, "Label x: <b>bad</b>");
});

test("render with nothing wrong says so", () => {
  const el = stripEl();
  renderHealthStrip(el, { overall: "ok", items: [item("a", "ok")] });
  assert.equal(el.className, "health-strip ok");
  assert.equal(el.textContent, "All jobs and feeds healthy");
});

test("unavailable is amber", () => {
  const el = stripEl();
  renderHealthUnavailable(el);
  assert.equal(el.className, "health-strip amber");
  assert.equal(el.textContent, "Health check unavailable");
});
