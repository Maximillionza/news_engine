import { refreshDashboard } from "./js/dashboard/dashboard-poll.js";
import { refreshCalendar } from "./js/calendar/calendar-poll.js";
import { loadHistoryIfNeeded } from "./js/history/table.js";

const POLL_INTERVAL_MS = 60_000;

const addForm = document.getElementById("add-symbol-form");
const addInput = document.getElementById("add-symbol-input");

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

addForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const ticker = addInput.value.trim().toUpperCase();
  if (!ticker) return;
  const resp = await fetch("/api/symbols", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker }),
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    alert(body.error || "Could not add symbol");
    return;
  }
  addInput.value = "";
  await refreshDashboard();
});

async function refreshAll() {
  await refreshDashboard();
  await refreshCalendar();
}

refreshAll();
setInterval(refreshAll, POLL_INTERVAL_MS);
