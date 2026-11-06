// webapp/static/js/api.test.js
import test from "node:test";
import assert from "node:assert/strict";
import { articleHistoryUrl } from "./api.js";

test("articleHistoryUrl: the Dashboard flip card sends no event time", () => {
  assert.equal(
    articleHistoryUrl("XAUUSD", "CPI m/m"),
    "/api/predictions/XAUUSD/article_history?event_title=CPI%20m%2Fm",
  );
});

test("articleHistoryUrl: the History why panel scopes to one occurrence, with its offset encoded", () => {
  // A bare '+' in a query string decodes to a space, which the server would reject as a malformed time.
  assert.equal(
    articleHistoryUrl("XAUUSD", "CPI m/m", "2026-11-06T13:30:00+00:00"),
    "/api/predictions/XAUUSD/article_history?event_title=CPI%20m%2Fm&event_time_utc=2026-11-06T13%3A30%3A00%2B00%3A00",
  );
});
