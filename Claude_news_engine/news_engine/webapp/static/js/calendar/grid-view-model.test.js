import test from "node:test";
import assert from "node:assert/strict";
import { buildCalendarCellViewModel, buildCalendarGridViewModel } from "./grid-view-model.js";

test("buildCalendarCellViewModel marks today correctly and produces one dot per event", () => {
  const today = new Date(2026, 8, 11);
  const vm = buildCalendarCellViewModel(
    new Date(2026, 8, 11),
    [{ title: "CPI m/m", impact: "High" }],
    [],
    today, null,
  );
  assert.equal(vm.isToday, true);
  assert.equal(vm.dots.length, 1);
  assert.equal(vm.dots[0].impactClass, "impact-high");
  assert.equal(vm.dateStr, "2026-09-11");
});

test("buildCalendarCellViewModel: hasEstimatedOnly true only when zero real events AND at least one estimated", () => {
  const today = new Date(2026, 8, 11);
  const vm = buildCalendarCellViewModel(new Date(2026, 8, 15), [], [{ title: "PPI m/m" }], today, null);
  assert.equal(vm.hasEstimatedOnly, true);
});

test("buildCalendarGridViewModel produces exactly one cell per day in the month, with the right leading-blank count", () => {
  const today = new Date(2026, 8, 11); // September 2026 has 30 days
  const vm = buildCalendarGridViewModel([], [], today);
  assert.equal(vm.cells.length, 30);
  assert.equal(vm.leadingBlanks, new Date(2026, 8, 1).getDay());
});

test("buildCalendarGridViewModel's defaultDateStr is the nearest upcoming event's date, or today if none", () => {
  const today = new Date(2026, 8, 11, 6, 0, 0);
  const events = [{ event_time_utc: new Date(2026, 8, 14, 12, 30).toISOString() }];
  const vm = buildCalendarGridViewModel(events, [], today);
  assert.equal(vm.defaultDateStr, "2026-09-14");
});
