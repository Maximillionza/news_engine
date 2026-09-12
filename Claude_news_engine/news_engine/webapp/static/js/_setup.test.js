import test from "node:test";
import assert from "node:assert/strict";

test("node --test runner is wired up correctly", () => {
  assert.equal(1 + 1, 2);
});
