// webapp/static/js/stats/impact-filter.test.js
import test from "node:test";
import assert from "node:assert/strict";
import { DEFAULT_IMPACTS, impactsParam, toggleImpact, chipsHtml } from "./impact-filter.js";

// The pressed state of one chip, read back from the markup.
function pressed(html, name) {
  const m = new RegExp(`data-impact="${name}"[^>]*aria-pressed="(true|false)"`).exec(html);
  assert.ok(m, `chip ${name} not found`);
  return m[1] === "true";
}

test("the default selection is High + Unrated", () => {
  assert.deepEqual(DEFAULT_IMPACTS, ["High", "Unrated"]);
});

test("default chips: four chips, High and Unrated pressed, Medium and Low not", () => {
  const html = chipsHtml(DEFAULT_IMPACTS);
  assert.equal((html.match(/data-impact=/g) || []).length, 4);
  assert.equal(pressed(html, "High"), true);
  assert.equal(pressed(html, "Unrated"), true);
  assert.equal(pressed(html, "Medium"), false);
  assert.equal(pressed(html, "Low"), false);
});

test("chip labels: High, Medium, Low and 'Unrated (inferred)'", () => {
  const html = chipsHtml(DEFAULT_IMPACTS);
  for (const label of [">High<", ">Medium<", ">Low<", ">Unrated (inferred)<"]) assert.ok(html.includes(label), label);
});

test("selected chips are styled, unselected ones are not", () => {
  const html = chipsHtml(["Low"]);
  const lowTag = /<button[^>]*data-impact="Low"[^>]*>/.exec(html)[0];
  const highTag = /<button[^>]*data-impact="High"[^>]*>/.exec(html)[0];
  assert.ok(lowTag.includes("impact-chip-on") && !highTag.includes("impact-chip-on"));
});

test("an empty selection presses no chip", () => {
  const html = chipsHtml([]);
  for (const name of ["High", "Medium", "Low", "Unrated"]) assert.equal(pressed(html, name), false);
});

test("toggleImpact adds an unselected level and removes a selected one, keeping canonical order", () => {
  assert.deepEqual(toggleImpact(["High", "Unrated"], "Low"), ["High", "Low", "Unrated"]);
  assert.deepEqual(toggleImpact(["High", "Unrated"], "High"), ["Unrated"]);
  assert.deepEqual(toggleImpact(["High"], "High"), []);
  assert.deepEqual(toggleImpact([], "Medium"), ["Medium"]);
});

test("toggleImpact does not mutate its input and ignores unknown names", () => {
  const input = ["High", "Unrated"];
  toggleImpact(input, "Low");
  assert.deepEqual(input, ["High", "Unrated"]);
  assert.deepEqual(toggleImpact(input, "Bogus"), ["High", "Unrated"]);
});

test("impactsParam is a comma list in the canonical order whatever the input order", () => {
  assert.equal(impactsParam(["High", "Unrated"]), "High,Unrated");
  assert.equal(impactsParam(["Unrated", "Low", "High", "Medium"]), "High,Medium,Low,Unrated");
  assert.equal(impactsParam(["Low"]), "Low");
});

test("impactsParam of an empty selection is the empty string; unknown names are dropped", () => {
  assert.equal(impactsParam([]), "");
  assert.equal(impactsParam(["Bogus"]), "");
  assert.equal(impactsParam(["Bogus", "High"]), "High");
});
