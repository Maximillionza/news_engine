// webapp/static/js/stats/latest.test.js
import test from "node:test";
import assert from "node:assert/strict";
import { createLatestGuard } from "./latest.js";

// A promise whose outcome the test decides.
function deferred() {
  let resolve; let reject;
  const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

test("a lone task reports its value as current", async () => {
  const guard = createLatestGuard();
  assert.deepEqual(await guard.run(async () => 7), { current: true, value: 7 });
});

test("an older task that succeeds late is stale", async () => {
  const guard = createLatestGuard();
  const slow = deferred();
  const older = guard.run(() => slow.promise);
  const newer = await guard.run(async () => "new");
  slow.resolve("old");
  assert.equal(newer.current, true);
  assert.deepEqual(await older, { current: false });
});

test("an older task that FAILS after a newer one started is swallowed, not thrown", async () => {
  const guard = createLatestGuard();
  const slow = deferred();
  const older = guard.run(() => slow.promise);
  const newer = await guard.run(async () => "new");
  slow.reject(new Error("boom"));
  assert.deepEqual(await older, { current: false });
  assert.equal(newer.value, "new");
});

test("the latest task's failure is thrown so the caller can show it", async () => {
  const guard = createLatestGuard();
  await assert.rejects(guard.run(async () => { throw new Error("boom"); }), /boom/);
});
