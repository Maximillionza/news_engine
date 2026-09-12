// webapp/static/js/calendar/render.test.js
//
// Fix round 1, Finding 3: Task 4's double-escaping fix (escapeHtml()
// through a normal lit-html `${}` binding double-escapes, since lit-html
// already escapes `${}` bindings itself) never propagated to the Calendar
// modules written in Task 7. These tests render date-panel.js's and
// grid.js's templates through the real vendored lit-html against a real
// jsdom document and confirm HTML-sensitive characters come out exactly
// once, matching the pattern of card.test.js's own double-escaping
// regression test.
//
// Must import ../dashboard/test-dom-setup.js FIRST (before anything that
// imports the vendored lit-html.js) — see that file's header comment.
import "../dashboard/test-dom-setup.js";
import test from "node:test";
import assert from "node:assert/strict";
import { render } from "../../vendor/lit-html.js";
import { eventTemplate, callLineTemplate } from "./date-panel.js";
import { calendarGridTemplate } from "./grid.js";
import { buildCalendarCellViewModel } from "./grid-view-model.js";

test("date-panel eventTemplate renders a title with &/'/< exactly once, not double-escaped", () => {
  const e = {
    title: "Fed's Beige Book <2026> & Outlook",
    impact: "High",
    forecast: "1.2",
    previous: "1.1",
    actual: "1.3",
    calls: {},
  };
  const container = document.createElement("div");
  render(eventTemplate(e), container);
  assert.ok(
    container.textContent.includes("Fed's Beige Book <2026> & Outlook"),
    `expected the real characters in textContent, got: ${container.textContent}`,
  );
  assert.ok(!container.innerHTML.includes("&#39;"), "must not be entity-encoded — lit-html's normal ${} binding already prevents injection without escapeHtml()");
  assert.ok(!container.innerHTML.includes("&amp;amp;"), "must not be double-escaped ampersands");
});

test("date-panel callLineTemplate renders a symbol/print-direction with special characters exactly once", () => {
  const call = { direction: "pending", print_prediction: { direction: "Higher & Hawkish", confidence: 0.8 } };
  const container = document.createElement("div");
  render(callLineTemplate("XAU'USD", call), container);
  assert.ok(container.textContent.includes("XAU'USD"), `expected the real apostrophe in textContent, got: ${container.textContent}`);
  assert.ok(container.textContent.includes("Higher & Hawkish"), `expected the real ampersand in textContent, got: ${container.textContent}`);
  assert.ok(!container.innerHTML.includes("&#39;"), "must not be entity-encoded");
});

test("calendar grid cellTemplate renders a dot's title attribute with special characters exactly once", () => {
  const today = new Date(2026, 8, 11);
  const cellVm = buildCalendarCellViewModel(new Date(2026, 8, 11), [{ title: "CPI m/m & Core <YoY>", impact: "High" }], [], today, null);
  const gridVm = { leadingBlanks: 0, cells: [cellVm] };
  const container = document.createElement("div");
  render(calendarGridTemplate(gridVm, () => {}), container);
  const dot = container.querySelector(".cal-dot");
  assert.ok(dot, "expected a rendered dot");
  assert.ok(
    dot.getAttribute("title").includes("CPI m/m & Core <YoY>"),
    `expected the real characters in the title attribute, got: ${dot.getAttribute("title")}`,
  );
  assert.ok(!dot.getAttribute("title").includes("&amp;"), "the title attribute must not be double-escaped");
});
