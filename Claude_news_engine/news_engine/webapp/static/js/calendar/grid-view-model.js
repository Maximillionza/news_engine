// webapp/static/js/calendar/grid-view-model.js
//
// Pure functions computing one calendar cell's view model — extracted
// from the original refreshCalendar()'s inline cell-building loop.

import { toIsoDateLocal } from "../format.js";

export function buildCalendarCellViewModel(cellDate, dayEvents, dayEstimated, today, nearestUpcomingDateStr) {
  const isToday = cellDate.toDateString() === today.toDateString();
  const isNearestUpcoming = cellDate.toDateString() === nearestUpcomingDateStr;
  const dots = dayEvents.map((e) => ({
    impactClass: e.impact === "High" ? "impact-high" : e.impact === "Medium" ? "impact-medium" : "impact-low",
    title: `${e.title} (${e.impact})`,
  }));
  const estimatedDots = dayEstimated.map((e) => ({
    title: `${e.title} (estimated — not yet confirmed by Forex Factory)`,
  }));
  return {
    dateStr: toIsoDateLocal(cellDate),
    day: cellDate.getDate(),
    isToday, isNearestUpcoming,
    hasEstimatedOnly: dayEvents.length === 0 && dayEstimated.length > 0,
    dots, estimatedDots,
  };
}

export function buildCalendarGridViewModel(events, estimatedOnlyEvents, today) {
  const upcoming = events
    .map((e) => new Date(e.event_time_utc))
    .filter((d) => d >= today)
    .sort((a, b) => a - b);
  const nearestUpcomingDateStr = upcoming.length > 0 ? upcoming[0].toDateString() : null;

  const year = today.getFullYear();
  const month = today.getMonth();
  const firstDay = new Date(year, month, 1);
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const startWeekday = firstDay.getDay();

  const eventsByDate = {};
  events.forEach((e) => {
    const d = new Date(e.event_time_utc).toDateString();
    (eventsByDate[d] = eventsByDate[d] || []).push(e);
  });
  const estimatedByDate = {};
  estimatedOnlyEvents.forEach((e) => {
    const d = new Date(e.event_time_utc).toDateString();
    (estimatedByDate[d] = estimatedByDate[d] || []).push(e);
  });

  const leadingBlanks = startWeekday;
  const cells = [];
  for (let day = 1; day <= daysInMonth; day++) {
    const cellDate = new Date(year, month, day);
    cells.push(buildCalendarCellViewModel(
      cellDate,
      eventsByDate[cellDate.toDateString()] || [],
      estimatedByDate[cellDate.toDateString()] || [],
      today, nearestUpcomingDateStr,
    ));
  }

  const defaultDateStr = upcoming.length > 0 ? toIsoDateLocal(upcoming[0]) : toIsoDateLocal(today);
  return { leadingBlanks, cells, defaultDateStr };
}
