// webapp/static/js/shock-alerts/table.test.js
//
// jsdom test: a rejected or failed date-range fetch shows a notice instead of failing silently.
import test from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";

test("a rejected range shows the server's error text in the notice", async () => {
  const dom = new JSDOM(`<!doctype html><html><body>
    <form id="shock-range"><input id="shock-range-from" value="2026-10-20"><input id="shock-range-to" value="2026-10-01"></form>
    <div id="shock-grading-summary"></div><div id="shock-grading-table"></div>
    <div id="shock-alerts-empty-notice" style="display:none">No shock alerts in this date range.</div>
    <div id="shock-alerts-list"></div><div id="shock-alerts-low-details"></div><div id="shock-alerts-low-list"></div>
  </body></html>`);
  global.window = dom.window;
  global.document = dom.window.document;
  global.fetch = async () => ({
    ok: false, status: 400, json: async () => ({ error: "from must not be after to" }),
  });
  const origError = console.error;
  console.error = () => {};
  try {
    const { wireRangeForm } = await import("./table.js");
    wireRangeForm();
    document.getElementById("shock-range").dispatchEvent(new dom.window.Event("submit", { cancelable: true }));
    await new Promise((resolve) => setTimeout(resolve, 20));
  } finally {
    console.error = origError;
  }
  const notice = document.getElementById("shock-alerts-empty-notice");
  assert.equal(notice.style.display, "");
  assert.ok(notice.textContent.includes("from must not be after to"), notice.textContent);
});
