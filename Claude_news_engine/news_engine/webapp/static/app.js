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
  return "INDECISIVE";
}

function directionClass(direction) {
  if (direction === "bullish") return "bullish";
  if (direction === "bearish") return "bearish";
  return "neutral";
}

// `probability` is P(bullish) throughout this whole system (0-100%, 50%
// = neutral) - the SAME single number for either direction, which is
// exactly what made "SELL 39%" ambiguous (is 39% the sell confidence, or
// the leftover bullish reading?). This returns P(that specific direction)
// instead: BUY shows the raw number as-is, SELL shows its complement
// (100 - raw) - e.g. a raw 39% BUY-probability reads as "SELL 61%", each
// direction now genuinely "out of its own 100," never sharing one scale.
function directionPct(probability, direction) {
  const raw = Math.round(probability * 100);
  return direction === "bearish" ? 100 - raw : raw;
}

function gaugeSvg(pct, direction) {
  // `pct` is already the per-direction display percentage (directionPct())
  // — the arc fills to match the number shown, not the raw shared-scale
  // probability, so a "SELL 61%" gauge visually reads as 61% filled, not 39%.
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

let _bullBearScaleCounter = 0;

// Bear(red)<->Bull(green) horizontal scale with a sliding indicator at
// `probability` (0.0-1.0) — where the article-based read sits relative to
// full-bear/full-bull, not "confidence in the shown direction." Directly
// addresses the ambiguity of a bare "SELL 39%" label: visually, 39% is
// obviously a mild lean toward the red end, not a strong one, without
// requiring the reader to do (100 - 39)% math in their head.
function bullBearScaleSvg(probability) {
  const id = `bbgrad-${_bullBearScaleCounter++}`;
  const pct = Math.max(0, Math.min(100, probability * 100));
  const trackX = 4, trackWidth = 172;
  const indicatorX = trackX + (pct / 100) * trackWidth;
  return `
    <svg width="180" height="34" viewBox="0 0 180 34">
      <defs>
        <linearGradient id="${id}" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#c62828"/>
          <stop offset="50%" stop-color="#ddd"/>
          <stop offset="100%" stop-color="#2e7d32"/>
        </linearGradient>
      </defs>
      <rect x="${trackX}" y="12" width="${trackWidth}" height="7" rx="3.5" fill="url(#${id})"/>
      <line x1="90" y1="8" x2="90" y2="23" stroke="#999" stroke-width="1"/>
      <circle cx="${indicatorX}" cy="15.5" r="6.5" fill="#222" stroke="#fff" stroke-width="2"/>
      <text x="${trackX}" y="33" font-size="9" fill="#c62828" font-weight="bold">BEAR</text>
      <text x="${trackX + trackWidth}" y="33" font-size="9" fill="#2e7d32" font-weight="bold" text-anchor="end">BULL</text>
    </svg>`;
}

// Shared by the essence-only gauge and the article-based read — both
// compare a previous (direction, probability) pair against a current one.
// previous_probability/probability are remapped onto THEIR OWN direction's
// basis via directionPct(), same as everywhere else — comparing
// "confidence within the same call" only makes sense when the direction
// didn't change. A flip (e.g. previous BUY -> now SELL) isn't a numeric
// delta at all; showing "-9pp" for a full reversal would misrepresent it
// as a minor wobble instead of the call flipping entirely. Returns '' if
// there's nothing meaningful to show (identical direction+probability).
function buildDiffStripHtml(prevDirection, prevProbability, currDirection, currProbability) {
  const prevPct = directionPct(prevProbability, prevDirection);
  const currPct = directionPct(currProbability, currDirection);

  if (prevDirection !== currDirection) {
    return `<div class="diff-strip reversed">
      <div>↔ Reversed: was <b>${directionLabel(prevDirection)} ${prevPct}%</b> → now <b>${directionLabel(currDirection)} ${currPct}%</b></div>
    </div>`;
  }

  const delta = currPct - prevPct;
  if (delta === 0) return '';
  return `<div class="diff-strip">${diffPieSvg(prevPct, delta)}
    <div>Previous: <b>${directionLabel(prevDirection)} ${prevPct}%</b><br>
    <span class="${delta >= 0 ? 'delta-up' : 'delta-down'}">${delta >= 0 ? '▲' : '▼'} ${delta >= 0 ? '+' : ''}${delta}pp → now ${currPct}%</span></div>
  </div>`;
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

  // article_prediction is the accumulator's own REAL prediction (direction
  // + probability), made BLIND from real articles BEFORE the event
  // resolves — it's independent of the essence-only score above and can
  // exist (and disagree) even while that score is still "pending". This is
  // the actual answer to "which way will this move" that the article-based
  // pipeline exists to produce — showing only the article COUNT and hiding
  // the call itself defeats the point, so this renders as a real headline,
  // not a footnote. Only present for events the accumulator has
  // independently processed (High-impact XAUUSD/US30 only, budget-capped) —
  // absent for everything else, which is expected.
  function articlePredictionHtml(pred, prevPred) {
    if (!pred) return '';
    const pct = directionPct(pred.probability, pred.direction);
    const dClass = directionClass(pred.direction);
    // Unlike the essence-only score (a fresh row most cycles),
    // scoring/backtest_accumulator.py only records a snapshot on a
    // material change — so any previous_article_prediction present here
    // is a genuine shift worth showing, never noise.
    const diffHtml = prevPred
      ? buildDiffStripHtml(prevPred.direction, prevPred.probability, pred.direction, pred.probability)
      : '';
    return `<div class="article-prediction ${dClass}">
      📰 Article-based read: <b>${directionLabel(pred.direction)} ${pct}%</b>
      <span style="font-size:12px;color:#888">(backed by ${pred.article_count} article${pred.article_count === 1 ? '' : 's'})</span>
      <div class="bull-bear-scale">${bullBearScaleSvg(pred.probability)}</div>
      ${diffHtml}
    </div>`;
  }
  const articlePredictionLine = articlePredictionHtml(next.article_prediction, next.previous_article_prediction);

  // print_prediction is the accumulator's separate "will THIS number beat
  // or miss forecast" call (scoring/print_direction.py), distinct from
  // article_prediction's price-direction call above. Absent (null) for
  // events with no PRINT_SURPRISE_LEXICON coverage or no call made yet —
  // rendered as nothing, never a fabricated placeholder.
  function printPredictionHtml(printPred) {
    if (!printPred) return '';
    const label = printPred.direction === 'higher' ? 'HIGHER than forecast'
      : printPred.direction === 'lower' ? 'LOWER than forecast' : 'IN LINE with forecast';
    const confPct = Math.round(printPred.confidence * 100);
    return `<div class="print-prediction">
      📊 Print call: likely <b>${label}</b> <span style="font-size:12px;color:#888">(${confPct}% confidence)</span>
    </div>`;
  }
  const printPredictionLine = printPredictionHtml(next.print_prediction);

  if (next.direction === "pending") {
    // The event/when data is already in the response — showing it here
    // instead of a generic placeholder tells the user WHAT they're
    // actually waiting on, not just that something is pending.
    const hasAnySignal = articlePredictionLine || printPredictionLine;
    const heading = hasAnySignal
      ? `Awaiting essence score: ${escapeHtml(next.event_title)}`
      : `Awaiting: ${escapeHtml(next.event_title)}`;
    body += `<div class="pending">${heading}<br>
      <span style="font-size:12px;color:#888">${formatEventDateTime(next.event_time_utc)}</span></div>
      ${articlePredictionLine}${printPredictionLine}`;
    el.innerHTML = body;
    el.querySelector(".remove-btn").addEventListener("click", () => removeSymbol(symbol));
    return el;
  }

  const pct = directionPct(next.probability, next.direction);
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
    body += buildDiffStripHtml(next.previous_direction, next.previous_probability, next.direction, next.probability);
  }

  body += `<div class="gauge-row">${gaugeSvg(pct, next.direction)}
    <div><div class="gauge-label ${dirClass}">${directionLabel(next.direction)} ${pct}%</div>
    <div style="font-size:12px;color:#888">${escapeHtml(next.event_title)}</div>
    ${articlePredictionLine}${printPredictionLine}</div></div>
    <div class="bull-bear-scale">${bullBearScaleSvg(next.probability)}</div>`;
  body += dayStripHtml(next.event_time_utc);
  const historyToggleId = `history-${symbol}-${next.event_title.replace(/[^a-zA-Z0-9]/g, '')}`;
  body += `<div class="history-toggle">
    <button class="history-toggle-btn" data-event-title="${escapeHtml(next.event_title)}" data-target="${historyToggleId}">History ▾</button>
    <div class="history-panel" id="${historyToggleId}" style="display:none"></div>
  </div>`;

  el.innerHTML = body;
  el.querySelector(".remove-btn").addEventListener("click", () => removeSymbol(symbol));

  const historyBtn = el.querySelector(".history-toggle-btn");
  if (historyBtn) {
    historyBtn.addEventListener("click", async () => {
      const panel = document.getElementById(historyBtn.dataset.target);
      if (panel.style.display !== "none") {
        panel.style.display = "none";
        return;
      }
      panel.style.display = "";
      if (panel.dataset.loaded === "true") {
        return;  // already fetched and rendered on an earlier expand — reuse it, don't re-fetch
      }
      panel.innerHTML = "Loading…";
      const resp = await fetch(`/api/event_history?title=${encodeURIComponent(historyBtn.dataset.eventTitle)}`);
      const data = await resp.json();
      panel.dataset.loaded = "true";
      if (!data.occurrences || data.occurrences.length === 0) {
        panel.innerHTML = "<div style=\"font-size:12px;color:#888\">No history recorded yet</div>";
        return;
      }
      const rows = data.occurrences.map((o) => {
        const dateLabel = new Date(o.event_time_utc).toLocaleDateString(undefined, { year: "numeric", month: "short" });
        const surpriseLabel = o.surprise_direction
          ? `(${escapeHtml(o.surprise_direction.replace("_", "-"))})`
          : (o.actual ? "(untracked)" : "(pending)");
        return `<div>${dateLabel}: forecast ${escapeHtml(o.forecast ?? "—")}, previous ${escapeHtml(o.previous ?? "—")}, actual ${escapeHtml(o.actual ?? "—")} ${surpriseLabel}</div>`;
      }).join("");
      panel.innerHTML = `${rows}<div style="margin-top:4px;font-weight:bold">→ ${escapeHtml(data.trend_summary)}</div>`;
    });
  }

  return el;
}

async function refreshDashboard() {
  const resp = await fetch("/api/predictions");
  const data = await resp.json();

  // "error" here means the background loop (webapp/scheduler.py) hasn't
  // completed its first successful fetch yet — not "a live request just
  // failed," since no route ever fetches live anymore. Once a snapshot
  // exists, it's shown as current until the background loop persists new
  // data — no per-request staleness, so this notice only ever appears
  // before the very first fetch (fresh install / recent restart).
  if (data.error) {
    predictionsStaleNoticeEl.textContent = data.error;
    predictionsStaleNoticeEl.style.display = "";
  } else {
    predictionsStaleNoticeEl.textContent = "";
    predictionsStaleNoticeEl.style.display = "none";
  }

  // Capture which History panels are currently expanded so a fresh
  // re-render below (which rebuilds every card from scratch, wiping
  // panel state and the data-loaded fetch cache) can restore them
  // afterward instead of silently collapsing them every 60s.
  const expandedHistoryIds = Array.from(cardsEl.querySelectorAll('.history-panel'))
    .filter((p) => p.style.display !== 'none')
    .map((p) => p.id);

  cardsEl.innerHTML = "";
  (data.predictions || []).forEach((entry) => cardsEl.appendChild(renderCard(entry)));

  // Re-expand (and re-fetch, since event_history may genuinely have
  // changed) any panel that survives under the same deterministic id —
  // i.e. this card's `next` event is still the same symbol+title.
  expandedHistoryIds.forEach((id) => {
    if (!document.getElementById(id)) return;  // that event is no longer this card's `next` — nothing to restore
    const btn = document.querySelector(`[data-target="${id}"]`);
    if (btn) btn.click();
  });
}

async function refreshCalendar() {
  const resp = await fetch("/api/calendar");
  const data = await resp.json();
  const events = data.events || [];

  if (data.error) {
    calendarStaleNoticeEl.textContent = data.error;
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

let historyLoaded = false;

async function loadHistoryIfNeeded() {
  if (historyLoaded) return;  // fetched once per page load, not on the dashboard's poll cycle
  historyLoaded = true;
  const resp = await fetch("/api/history");
  const data = await resp.json();
  renderHistoryTable(data.rows || []);
}

function renderHistoryTable(rows) {
  const table = document.getElementById("history-table");
  const emptyNotice = document.getElementById("history-empty-notice");
  const tbody = document.getElementById("history-tbody");

  if (rows.length === 0) {
    table.style.display = "none";
    emptyNotice.style.display = "";
    return;
  }

  emptyNotice.style.display = "none";
  table.style.display = "";
  tbody.innerHTML = rows.map((r) => {
    const dateLabel = new Date(r.event_time_utc).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
    const actualCell = r.unchanged_vs_previous
      ? `${escapeHtml(r.actual ?? "—")} <span style="color:#888;font-size:11px">(= prev)</span>`
      : escapeHtml(r.actual ?? "—");
    const sourceBadge = r.source === "seeded"
      ? ' <span style="color:#888;font-size:11px;font-weight:normal">(seeded)</span>'
      : "";
    // Numeric rows use higher/lower/in_line; text-event fallback rows use bullish/bearish/neutral.
    const predictionLabel = { higher: "Higher", lower: "Lower", in_line: "In-line", bullish: "Bullish", bearish: "Bearish", neutral: "Neutral" }[r.ne_prediction] || escapeHtml(r.ne_prediction);
    const outcomeLabel = r.outcome === null
      ? `<span style="color:#888">${
          r.unjudged_reason === "pending" ? "Awaiting confirmation"
          : r.unjudged_reason === "unknown_surprise" ? "Actual not comparable"
          : "No strong call"
        }</span>`
      : r.outcome === "Confirmed"
        ? '<span style="color:#2e7d32;font-weight:bold">Confirmed</span>'
        : '<span style="color:#c62828;font-weight:bold">Missed</span>';
    return `<tr>
      <td>${escapeHtml(r.event_title)}${sourceBadge}<br><span style="font-size:11px;color:#888">${dateLabel}</span></td>
      <td>${escapeHtml(r.instrument ?? "")}</td>
      <td>${escapeHtml(r.previous ?? "—")}</td>
      <td>${escapeHtml(r.forecast ?? "—")}</td>
      <td>${actualCell}</td>
      <td>${predictionLabel} <span style="font-size:11px;color:#888">(${Math.round(r.ne_confidence * 100)}% conf.)</span></td>
      <td>${outcomeLabel}</td>
    </tr>`;
  }).join("");
}
