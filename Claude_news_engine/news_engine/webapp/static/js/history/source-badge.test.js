// webapp/static/js/history/source-badge.test.js
import test from "node:test";
import assert from "node:assert/strict";
import { sourceBadge } from "./source-badge.js";

test("sourceBadge labels each official publisher", () => {
  assert.equal(sourceBadge("bls"), ' <span class="meta-text-sm">(BLS)</span>');
  assert.equal(sourceBadge("bea"), ' <span class="meta-text-sm">(BEA)</span>');
  assert.equal(sourceBadge("census"), ' <span class="meta-text-sm">(Census)</span>');
  assert.equal(sourceBadge("eia"), ' <span class="meta-text-sm">(EIA)</span>');
  assert.equal(sourceBadge("fed"), ' <span class="meta-text-sm">(Fed)</span>');
  assert.equal(sourceBadge("treasury"), ' <span class="meta-text-sm">(Treasury)</span>');
});

test("sourceBadge keeps the existing seeded and fallback labels unchanged", () => {
  assert.equal(sourceBadge("seeded"), ' <span class="meta-text-sm">(seeded)</span>');
  assert.equal(sourceBadge("live_web_fallback"), ' <span class="meta-text-sm">(web-sourced)</span>');
  assert.equal(sourceBadge("cloud_web_fallback"), ' <span class="meta-text-sm">(cloud-researched)</span>');
});

test("sourceBadge shows nothing for live, fred, unknown or inherited keys", () => {
  assert.equal(sourceBadge("live"), "");
  assert.equal(sourceBadge("fred"), "");
  assert.equal(sourceBadge(undefined), "");
  assert.equal(sourceBadge("constructor"), "");
});
