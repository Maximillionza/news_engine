// webapp/static/js/stats/info.test.js
import test from "node:test";
import assert from "node:assert/strict";
import { componentsHtml } from "./info.js";

test("lists every component with its source", () => {
  const html = componentsHtml({ title: "T", summary: "S", note: "N",
    components: [{ name: "Brent crude (daily)", detail: "d", source: "EIA" }] });
  assert.ok(html.includes("Brent crude (daily)") && html.includes("EIA") && html.includes("N"));
});

test("escapes component text", () => {
  assert.ok(!componentsHtml({ title: "<b>", summary: "", components: [] }).includes("<b>"));
});
