const POLL_INTERVAL_MS = 60_000;

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

const cardsEl = document.getElementById("cards");
const calendarGridEl = document.getElementById("calendar-grid");
const calendarListEl = document.getElementById("calendar-list");
const addForm = document.getElementById("add-symbol-form");
const addInput = document.getElementById("add-symbol-input");
const calendarStaleNoticeEl = document.getElementById("calendar-stale-notice");
const predictionsStaleNoticeEl = document.getElementById("predictions-stale-notice");

function formatEventDateTime(eventTimeUtc) {
  return new Date(eventTimeUtc).toLocaleString();
}

document.getElementById("tab-dashboard").addEventListener("click", () => showView("dashboard"));
document.getElementById("tab-calendar").addEventListener("click", () => showView("calendar"));

function showView(name) {
  document.getElementById("view-dashboard").style.display = name === "dashboard" ? "" : "none";
  document.getElementById("view-calendar").style.display = name === "calendar" ? "" : "none";
  document.getElementById("tab-dashboard").classList.toggle("active", name === "dashboard");
  document.getElementById("tab-calendar").classList.toggle("active", name === "calendar");
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

async function removeSymbol(ticker) {
  await fetch(`/api/symbols/${ticker}`, { method: "DELETE" });
  await refreshDashboard();
}

function directionLabel(direction) {
  if (direction === "bullish") return "BUY";
  if (direction === "bearish") return "SELL";
  return "HOLD";
}

function directionClass(direction) {
  if (direction === "bullish") return "bullish";
  if (direction === "bearish") return "bearish";
  return "neutral";
}

function gaugeSvg(probability, direction) {
  const pct = Math.round(probability * 100);
  const color = direction === "bullish" ? "#2e7d32" : direction === "bearish" ? "#c62828" : "#888";
  const circumference = 2 * Math.PI * 26;
  const filled = (pct / 100) * circumference;
  return `
    <svg width="70" height="70" viewBox="0 0 70 70">
      <circle cx="35" cy="35" r="26" fill="none" stroke="#eee" stroke-width="7"/>
      <circle cx="35" cy="35" r="26" fill="none" stroke="${color}" stroke-width="7"
        stroke-dasharray="${filled} ${circumference}" stroke-linecap="round"
        transform="rotate(-90 35 35)"/>
      <text x="35" y="39" text-anchor="middle" font-size="13" font-weight="bold">${pct}%</text>
    </svg>`;
}

function diffPieSvg(previousPct, delta) {
  const isUp = delta >= 0;
  const baseColor = "#a5d6a7";
  const deltaColor = isUp ? "#2e7d32" : "#c62828";
  const basePct = isUp ? previousPct : previousPct + delta; // the smaller of the two — the part that's "still true"
  const deltaAbs = Math.abs(delta);
  return `
    <svg width="44" height="44" viewBox="0 0 32 32">
      <circle r="14" cx="16" cy="16" fill="#eee" pathLength="100"/>
      <circle r="14" cx="16" cy="16" fill="transparent" stroke="${baseColor}" stroke-width="14" pathLength="100"
        stroke-dasharray="${basePct} 100" transform="rotate(-90 16 16)"/>
      <circle r="14" cx="16" cy="16" fill="transparent" stroke="${deltaColor}" stroke-width="14" opacity="0.9" pathLength="100"
        stroke-dasharray="${deltaAbs} 100" stroke-dashoffset="${-basePct}" transform="rotate(-90 16 16)"/>
    </svg>`;
}

function dayStripHtml(eventTimeUtc) {
  const today = new Date();
  const eventDate = new Date(eventTimeUtc);
  const cells = [];
  for (let offset = -4; offset <= 10; offset++) {
    const d = new Date(today);
    d.setDate(d.getDate() + offset);
    const isToday = offset === 0;
    const isEvent = d.toDateString() === eventDate.toDateString();
    const classes = ["day-cell"];
    if (isToday) classes.push("today");
    if (isEvent) classes.push("event");
    cells.push(`<div class="${classes.join(" ")}">${d.getDate()}</div>`);
  }
  return `<div class="day-strip">${cells.join("")}</div>`;
}

function renderCard(symbolEntry) {
  const { symbol, symbol_class, events } = symbolEntry;
  const el = document.createElement("div");
  el.className = "card";

  let body = `<div class="card-header"><h3>${symbol}</h3><button class="remove-btn" data-symbol="${symbol}">Remove</button></div>`;

  if (symbol_class === "fx_cross") {
    body += `<div class="not-applicable">No USD exposure for tracked events</div>`;
    el.innerHTML = body;
    el.querySelector(".remove-btn").addEventListener("click", () => removeSymbol(symbol));
    return el;
  }

  if (!events || events.length === 0) {
    body += `<div class="pending">Awaiting next tracked event</div>`;
    el.innerHTML = body;
    el.querySelector(".remove-btn").addEventListener("click", () => removeSymbol(symbol));
    return el;
  }

  const next = events[0];

  if (next.direction === "pending") {
    // The event/when data is already in the response — showing it here
    // instead of a generic placeholder tells the user WHAT they're
    // actually waiting on, not just that something is pending.
    body += `<div class="pending">Awaiting: ${escapeHtml(next.event_title)}<br>
      <span style="font-size:12px;color:#888">${formatEventDateTime(next.event_time_utc)}</span></div>`;
    el.innerHTML = body;
    el.querySelector(".remove-btn").addEventListener("click", () => removeSymbol(symbol));
    return el;
  }

  const pct = Math.round(next.probability * 100);
  const dirClass = directionClass(next.direction);

  // A pending -> real transition is a first real score, not a diff — only
  // show the two-tone diff strip for real -> real changes.
  const hasPreviousChange = next.previous_probability !== null && next.previous_probability !== undefined
    && next.previous_direction !== "pending"
    && Math.abs(next.previous_probability - next.probability) > 1e-6;

  // The event just released this cycle (previous row was pending, this one
  // is a real score) — no percentage to diff against, but this is the
  // single most informative moment for a user, so call it out distinctly
  // instead of silently falling through to the plain gauge.
  const justReleased = next.previous_direction === "pending" && next.direction !== "pending";

  if (justReleased) {
    body += `<div class="just-released ${dirClass}">🎯 Just released — ${directionLabel(next.direction)} ${pct}%</div>`;
  }

  if (hasPreviousChange) {
    const prevPct = Math.round(next.previous_probability * 100);
    const delta = pct - prevPct;
    if (delta !== 0) {
      body += `<div class="diff-strip">${diffPieSvg(prevPct, delta)}
        <div>Previous: <b>${directionLabel(next.previous_direction)} ${prevPct}%</b><br>
        <span class="${delta >= 0 ? 'delta-up' : 'delta-down'}">${delta >= 0 ? '▲' : '▼'} ${delta >= 0 ? '+' : ''}${delta}pp → now ${pct}%</span></div>
      </div>`;
    }
  }

  body += `<div class="gauge-row">${gaugeSvg(next.probability, next.direction)}
    <div><div class="gauge-label ${dirClass}">${directionLabel(next.direction)} ${pct}%</div>
    <div style="font-size:12px;color:#888">${escapeHtml(next.event_title)}</div></div></div>`;
  body += dayStripHtml(next.event_time_utc);

  el.innerHTML = body;
  el.querySelector(".remove-btn").addEventListener("click", () => removeSymbol(symbol));
  return el;
}

async function refreshDashboard() {
  const resp = await fetch("/api/predictions");
  const data = await resp.json();

  if (data.error) {
    predictionsStaleNoticeEl.textContent = `Predictions may be stale — last calendar refresh failed (${data.error})`;
    predictionsStaleNoticeEl.style.display = "";
  } else {
    predictionsStaleNoticeEl.textContent = "";
    predictionsStaleNoticeEl.style.display = "none";
  }

  cardsEl.innerHTML = "";
  (data.predictions || []).forEach((entry) => cardsEl.appendChild(renderCard(entry)));
}

async function refreshCalendar() {
  const resp = await fetch("/api/calendar");
  const data = await resp.json();
  const events = data.events || [];

  if (data.error) {
    calendarStaleNoticeEl.textContent = `Calendar data may be stale — last refresh failed (${data.error})`;
    calendarStaleNoticeEl.style.display = "";
  } else {
    calendarStaleNoticeEl.textContent = "";
    calendarStaleNoticeEl.style.display = "none";
  }

  const today = new Date();
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

  let cells = "";
  for (let i = 0; i < startWeekday; i++) cells += `<div class="cal-cell"></div>`;
  for (let day = 1; day <= daysInMonth; day++) {
    const cellDate = new Date(year, month, day);
    const isToday = cellDate.toDateString() === today.toDateString();
    const dayEvents = eventsByDate[cellDate.toDateString()] || [];
    const dots = dayEvents.map(() => `<span class="cal-dot"></span>`).join("");
    cells += `<div class="cal-cell ${isToday ? "today" : ""}">${day}<br>${dots}</div>`;
  }
  calendarGridEl.innerHTML = cells;

  calendarListEl.innerHTML = events
    .map((e) => `<li>${new Date(e.event_time_utc).toLocaleString()} — ${escapeHtml(e.title)} (${escapeHtml(e.impact)})</li>`)
    .join("");
}

async function refreshAll() {
  await refreshDashboard();
  await refreshCalendar();
}

refreshAll();
setInterval(refreshAll, POLL_INTERVAL_MS);
