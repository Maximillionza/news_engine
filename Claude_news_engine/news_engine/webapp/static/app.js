import { refreshDashboard } from "./js/dashboard/dashboard-poll.js";
import { refreshCalendar } from "./js/calendar/calendar-poll.js";
import { loadHistoryIfNeeded } from "./js/history/table.js";
// Side-effecting import (2026-09-13): registers the "+ Add symbol"
// picker's own listeners at module load, same pattern calendar-poll.js's
// close-button listener already uses. Replaces the old free-text
// "Add symbol e.g. EURUSD" form entirely.
import "./js/dashboard/symbol-picker.js";

const POLL_INTERVAL_MS = 60_000;

document.getElementById("tab-dashboard").addEventListener("click", () => showView("dashboard"));
document.getElementById("tab-calendar").addEventListener("click", () => showView("calendar"));
document.getElementById("tab-history").addEventListener("click", () => {
  showView("history");
  loadHistoryIfNeeded();
});

function showView(name) {
  document.getElementById("view-dashboard").style.display = name === "dashboard" ? "" : "none";
  document.getElementById("view-calendar").style.display = name === "calendar" ? "" : "none";
  document.getElementById("view-history").style.display = name === "history" ? "" : "none";
  document.getElementById("tab-dashboard").classList.toggle("active", name === "dashboard");
  document.getElementById("tab-calendar").classList.toggle("active", name === "calendar");
  document.getElementById("tab-history").classList.toggle("active", name === "history");
  // Accessibility fix (2026-09-13): aria-selected is what actually tells a
  // screen reader which tab is current — the "active" class above is a
  // visual-only signal it can't read.
  document.getElementById("tab-dashboard").setAttribute("aria-selected", String(name === "dashboard"));
  document.getElementById("tab-calendar").setAttribute("aria-selected", String(name === "calendar"));
  document.getElementById("tab-history").setAttribute("aria-selected", String(name === "history"));
}

async function refreshAll() {
  await refreshDashboard();
  await refreshCalendar();
}

refreshAll();
setInterval(refreshAll, POLL_INTERVAL_MS);
