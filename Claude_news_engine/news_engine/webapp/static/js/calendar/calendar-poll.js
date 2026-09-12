// webapp/static/js/calendar/calendar-poll.js
import { html, render } from "../../vendor/lit-html.js";
import { fetchCalendar, fetchCalendarMonthAhead } from "../api.js";
import { buildCalendarGridViewModel } from "./grid-view-model.js";
import { calendarGridTemplate } from "./grid.js";
import { showDatePanel } from "./date-panel.js";
import { renderFeedStaleness } from "../staleness.js";

const calendarGridEl = document.getElementById("calendar-grid");
const calendarStaleNoticeEl = document.getElementById("calendar-stale-notice");
const calendarPollErrorEl = document.getElementById("calendar-poll-error-notice");

// Sticky across polls (same idea as before this refactor — this was
// already correct JS state, not a DOM-inspection hack; kept as-is for
// consistency with the new module structure).
const panelState = { selectedCalendarDateStr: null, calendarPanelClosed: false };

document.getElementById("calendar-date-panel-close").addEventListener("click", () => {
  panelState.calendarPanelClosed = true;
  document.getElementById("calendar-date-panel").style.display = "none";
});

export async function refreshCalendar() {
  let data;
  try {
    data = await fetchCalendar();
  } catch (err) {
    console.error("refreshCalendar: poll failed", err);
    calendarPollErrorEl.textContent = "Couldn't reach the server — showing the last data received.";
    calendarPollErrorEl.style.display = "";
    return;
  }
  calendarPollErrorEl.style.display = "none";
  const events = data.events || [];
  renderFeedStaleness(data.feed_staleness_seconds);

  if (data.error) {
    calendarStaleNoticeEl.textContent = data.error;
    calendarStaleNoticeEl.style.display = "";
  } else {
    calendarStaleNoticeEl.textContent = "";
    calendarStaleNoticeEl.style.display = "none";
  }

  let estimatedOnlyEvents = [];
  try {
    const monthAheadData = await fetchCalendarMonthAhead();
    estimatedOnlyEvents = (monthAheadData.events || []).filter((e) => e.estimated);
  } catch {
    estimatedOnlyEvents = [];  // macro view is a nice-to-have overlay — a fetch failure here must not break the calendar tab
  }

  const today = new Date();
  const gridViewModel = buildCalendarGridViewModel(events, estimatedOnlyEvents, today);

  render(calendarGridTemplate(gridViewModel, (dateStr) => showDatePanel(dateStr, panelState)), calendarGridEl);

  if (!panelState.calendarPanelClosed) {
    await showDatePanel(panelState.selectedCalendarDateStr || gridViewModel.defaultDateStr, panelState);
  }
}
