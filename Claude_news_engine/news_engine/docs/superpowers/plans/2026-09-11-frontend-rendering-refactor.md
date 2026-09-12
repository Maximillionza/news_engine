# Frontend Rendering Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `webapp/static/app.js`'s full-DOM-teardown polling (Dashboard cards, Calendar grid) with keyed, lit-html-based rendering, breaking the file into named ES modules with real automated test coverage.

**Architecture:** Vendor `lit-html` as a single local file; convert `app.js` into an ES-module entrypoint importing from `webapp/static/js/**`; move UI-only state (card flip, expanded panels, lazy-loaded article history) into explicit JS state maps read by pure view-model functions, rendered via `lit-html`'s keyed `repeat()` directive so DOM nodes persist across polls instead of being destroyed and recreated.

**Tech Stack:** Vanilla JS (ES modules, no bundler), `lit-html` (vendored), Node's built-in `node --test` + `jsdom` for tests (first `package.json` in this repo, test-only).

**Spec:** `docs/superpowers/specs/2026-09-11-frontend-rendering-refactor-design.md`

## Global Constraints

- Output HTML/behavior must be identical to today's for every existing signal (article prediction, Tier 1, Tier 1 sentiment conflict, Tier 1 confidence downgrade, essence/article dual-labeling, print call, Kalshi read, trend signal, other-events, other-tracked-events, day strip, History/breakdown toggles, card flip). This is a refactor, not a feature change — any visual/behavioral difference found during a task's live-verify step is a bug in that task, not a deliberate change.
- No CDN dependency at runtime — `lit-html` is vendored as a local static file under `webapp/static/vendor/`.
- No build step / bundler for the shipped frontend — browsers load ES modules directly.
- `package.json` / `jsdom` is test-only tooling. Never referenced from anything under `webapp/static/` at runtime.
- The History tab's rendering logic itself is out of scope — Task 8 moves its functions verbatim to a new file location; their internals do not change.
- Every task that touches `webapp/static/**` ends with a live browser-verification step (via the Browser pane tooling), in addition to its automated tests — this is a live trading dashboard; no task may leave it regressed.

---

### Task 1: Vendor lit-html, convert to ES module script

**Files:**
- Create: `webapp/static/vendor/lit-html.js`
- Modify: `webapp/static/index.html`

**Interfaces:**
- Consumes: none.
- Produces: `webapp/static/vendor/lit-html.js` exporting `html`, `render`, `repeat` (via `lit-html/directives/repeat.js` bundled into the same file or a second vendored file `webapp/static/vendor/lit-html-repeat.js`) — Tasks 4, 6, 7 import from this path by exact name.

- [ ] **Step 1: Download lit-html as a local ESM bundle**

Run (from the `news_engine` project root):
```bash
curl -o webapp/static/vendor/lit-html.js https://cdn.jsdelivr.net/npm/lit-html@3.2.1/lit-html.js
mkdir -p webapp/static/vendor/directives
curl -o webapp/static/vendor/directives/repeat.js https://cdn.jsdelivr.net/npm/lit-html@3.2.1/directives/repeat.js
```
Verify both files were actually downloaded (non-empty, contain `export`):
```bash
wc -l webapp/static/vendor/lit-html.js webapp/static/vendor/directives/repeat.js
grep -c "^export" webapp/static/vendor/lit-html.js webapp/static/vendor/directives/repeat.js
```
Expected: both files have real content (lit-html.js is typically 400-600 lines minified-ish but readable; repeat.js is short) and at least one `export` line each. If `curl` isn't available, use `curl.exe` (Windows) or fetch the URL contents another way — the file must be the REAL, complete lit-html 3.2.1 source, never a stub.

**Important:** `repeat.js`'s own internal import (`import {noChange} from '../lit-html.js';` or similar relative import) must resolve correctly given the two files' relative location — confirm by opening `webapp/static/vendor/directives/repeat.js` and checking its import path is `../lit-html.js` (one level up from `directives/`), matching the directory structure created above. If the downloaded file uses a different relative path, adjust the local directory structure to match it exactly rather than editing the vendored file's import path.

- [ ] **Step 2: Convert the script tag to a module**

In `webapp/static/index.html`, find:
```html
<script src="/static/app.js"></script>
```
Replace with:
```html
<script type="module" src="/static/app.js"></script>
```

- [ ] **Step 3: Confirm app.js still runs as a module with zero other changes**

`app.js` currently has no `import`/`export` statements, so it is already valid as an ES module without modification. Start the dashboard (`python -m webapp.app` per `.claude/launch.json`, or use the Browser pane's `preview_start` with `{name: "news-engine-webapp"}`), navigate to `http://127.0.0.1:5001`, and check the browser console for errors.

- [ ] **Step 4: Live-verify**

Using the Browser pane tooling: `preview_start` (or `navigate`) to the dashboard, take a screenshot, confirm the Dashboard tab renders cards exactly as before, switch to the Calendar tab and confirm the grid renders, check `read_console_messages` for any new errors (a module-loading MIME-type error would show here — Flask must serve `.js` files with `Content-Type: application/javascript` or `text/javascript` for `type="module"` to work; if this fails, check `webapp/app.py`'s static file serving and Flask's default MIME type handling for `.js` — this should already work since Flask's default static handler infers Content-Type from extension, but confirm via `read_network_requests` on the `app.js` request).

- [ ] **Step 5: Commit**

```bash
git add webapp/static/vendor webapp/static/index.html
git commit -m "chore: vendor lit-html, convert app.js to an ES module"
```

---

### Task 2: Test infrastructure (package.json + jsdom)

**Files:**
- Create: `package.json` (at the `news_engine/` project root)
- Create: `webapp/static/js/_setup.test.js` (placeholder, deleted in a later task once real tests exist — see Step 4)

**Interfaces:**
- Consumes: none.
- Produces: a working `node --test` command and an installed `jsdom` — Tasks 3-7 add real `*.test.js` files that this infrastructure runs.

- [ ] **Step 1: Create package.json**

```json
{
  "name": "news-engine-frontend-tests",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "description": "Test-only tooling for webapp/static/js. Never shipped to webapp/static/ at runtime — see docs/superpowers/specs/2026-09-11-frontend-rendering-refactor-design.md's Global Constraints.",
  "scripts": {
    "test": "node --test webapp/static/js"
  },
  "devDependencies": {
    "jsdom": "^25.0.1"
  }
}
```

- [ ] **Step 2: Install**

```bash
npm install
```
Expected: creates `node_modules/` and `package-lock.json`. Confirm `node_modules/jsdom` exists.

- [ ] **Step 3: Add `.gitignore` entry for node_modules**

Check `.gitignore` (repo root, `C:\Users\Masoodt\Documents\Claude\Projects\.gitignore`) for an existing `node_modules` entry. If none exists for this path, add one scoped to this project:
```
Claude_news_engine/news_engine/node_modules/
```

- [ ] **Step 4: Write and run a trivial placeholder test to confirm the runner works**

```javascript
// webapp/static/js/_setup.test.js
import test from "node:test";
import assert from "node:assert/strict";

test("node --test runner is wired up correctly", () => {
  assert.equal(1 + 1, 2);
});
```

Run: `npm test`
Expected: `# pass 1`, `# fail 0`.

This placeholder file is deleted in Task 3's Step 1 once a real test file exists to prove the runner against — its only purpose is confirming the toolchain works before any real extraction begins.

- [ ] **Step 5: Commit**

```bash
git add package.json package-lock.json .gitignore webapp/static/js/_setup.test.js
git commit -m "chore: add package.json + jsdom test infrastructure"
```

---

### Task 3: Extract format.js's pure functions

**Files:**
- Create: `webapp/static/js/format.js`
- Create: `webapp/static/js/format.test.js`
- Modify: `webapp/static/app.js`
- Delete: `webapp/static/js/_setup.test.js`

**Interfaces:**
- Consumes: none.
- Produces: named exports `escapeHtml`, `directionLabel`, `directionClass`, `directionPct`, `confidenceColorClass`, `formatEventDateTime`, `toIsoDateLocal`, `gaugeSvg`, `bullBearScaleSvg`, `buildDiffStripHtml`, `diffPieSvg`, `dayStripHtml`, `tier1DirectionLabel` — Tasks 4 and 7 import all of these by exact name.

This is a **mechanical, byte-for-byte extraction** — every function below is moved verbatim from its current location in `webapp/static/app.js` (as of commit `41d0e00`), with zero logic change. `escapeHtml` needs a browser DOM (`document.createElement`) to work as originally written, which is not available under plain Node — Step 1 below adjusts ONLY `escapeHtml` to use string-replacement instead (behaviorally identical output, verified by the test in Step 2), and leaves every other function's body completely untouched.

- [ ] **Step 1: Write format.js**

```javascript
// webapp/static/js/format.js
//
// Pure formatting/label functions, zero DOM dependency (except where noted),
// extracted verbatim from the original monolithic app.js
// (docs/superpowers/specs/2026-09-11-frontend-rendering-refactor-design.md).

// escapeHtml originally used `document.createElement("div").textContent =`
// (DOM-dependent) -- rewritten here as pure string replacement so it can be
// unit-tested under plain Node with no jsdom, and so it works identically
// inside a lit-html template context. Escapes the same 5 characters the
// browser's own textContent/innerHTML round-trip would.
export function escapeHtml(str) {
  const s = str ?? "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Batch 10 (dashboard-review-2026-09-11.md live UI walkthrough): "1% and
// 100% render as identical plain text" — no threshold treatment
// distinguished a genuinely strong call from a noise-level one anywhere in
// the UI. Not a new scale — a visual rendering of the 3-tier split this
// codebase's own confidence language already uses elsewhere (Tier 1's
// Certain/Likely/Guessing tags).
export function confidenceColorClass(pct) {
  if (pct >= 66) return "confidence-high";
  if (pct >= 33) return "confidence-medium";
  return "confidence-low";
}

export function formatEventDateTime(eventTimeUtc) {
  return new Date(eventTimeUtc).toLocaleString();
}

// Local-calendar-date ISO string (YYYY-MM-DD). NOT Date.toISOString() —
// that converts to UTC first, which would shift the date for any
// non-UTC+0 local timezone (e.g. SAST/UTC+2 local midnight becomes the
// previous day at 22:00 UTC) and desync the cell's data-date from the
// cell's own displayed day number.
export function toIsoDateLocal(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function directionLabel(direction) {
  if (direction === "bullish") return "BUY";
  if (direction === "bearish") return "SELL";
  return "INDECISIVE";
}

export function directionClass(direction) {
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
export function directionPct(probability, direction) {
  const raw = Math.round(probability * 100);
  return direction === "bearish" ? 100 - raw : raw;
}

export function gaugeSvg(pct, direction) {
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
export function bullBearScaleSvg(probability) {
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
export function buildDiffStripHtml(prevDirection, prevProbability, currDirection, currProbability) {
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

export function diffPieSvg(previousPct, delta) {
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

export function dayStripHtml(eventTimeUtc) {
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

// tier1DirectionLabel (2026-09-07): Tier 1's own predicted_direction is
// "bullish"/"bearish"/"neutral" -- directionLabel() maps those to
// BUY/SELL/INDECISIVE. A Tier 1 row logged as confidence="Guessing" with
// no confident call also carries predicted_direction="neutral" by
// convention (see scoring/backtest.py's Tier1Prediction docstring) -- this
// wrapper exists so the label reads "NO CALL" for that specific case
// instead of the generic "INDECISIVE" a real neutral essence/article call
// would show, since Tier 1 neutral means something different (no
// confident directional judgment was possible) from essence/article
// neutral (a genuinely balanced read).
export function tier1DirectionLabel(tier1) {
  if (tier1.confidence === "Guessing" && tier1.predicted_direction === "neutral") return "NO CALL";
  return directionLabel(tier1.predicted_direction);
}
```

- [ ] **Step 2: Write format.test.js**

```javascript
// webapp/static/js/format.test.js
import test from "node:test";
import assert from "node:assert/strict";
import {
  escapeHtml, confidenceColorClass, formatEventDateTime, toIsoDateLocal,
  directionLabel, directionClass, directionPct, gaugeSvg, bullBearScaleSvg,
  buildDiffStripHtml, diffPieSvg, dayStripHtml, tier1DirectionLabel,
} from "./format.js";

test("escapeHtml escapes the 5 HTML-sensitive characters", () => {
  assert.equal(escapeHtml(`<script>&"'`), "&lt;script&gt;&amp;&quot;&#39;");
});

test("escapeHtml treats null/undefined as empty string, never 'null'/'undefined' text", () => {
  assert.equal(escapeHtml(null), "");
  assert.equal(escapeHtml(undefined), "");
});

test("confidenceColorClass: 3-tier split at 33/66", () => {
  assert.equal(confidenceColorClass(10), "confidence-low");
  assert.equal(confidenceColorClass(33), "confidence-medium");
  assert.equal(confidenceColorClass(65), "confidence-medium");
  assert.equal(confidenceColorClass(66), "confidence-high");
  assert.equal(confidenceColorClass(100), "confidence-high");
});

test("directionLabel maps bullish/bearish/neutral to BUY/SELL/INDECISIVE", () => {
  assert.equal(directionLabel("bullish"), "BUY");
  assert.equal(directionLabel("bearish"), "SELL");
  assert.equal(directionLabel("neutral"), "INDECISIVE");
});

test("directionClass maps bullish/bearish/neutral to bullish/bearish/neutral CSS classes", () => {
  assert.equal(directionClass("bullish"), "bullish");
  assert.equal(directionClass("bearish"), "bearish");
  assert.equal(directionClass("neutral"), "neutral");
});

test("directionPct: BUY shows raw probability, SELL shows its complement", () => {
  assert.equal(directionPct(0.71, "bullish"), 71);
  assert.equal(directionPct(0.39, "bearish"), 61);
});

test("gaugeSvg returns an svg string containing the percentage text", () => {
  const svg = gaugeSvg(61, "bearish");
  assert.match(svg, /<svg/);
  assert.match(svg, />61%</);
  assert.match(svg, /#c62828/);  // bearish color
});

test("bullBearScaleSvg returns an svg string with a unique gradient id per call", () => {
  const a = bullBearScaleSvg(0.5);
  const b = bullBearScaleSvg(0.5);
  assert.match(a, /<svg/);
  assert.notEqual(a, b, "each call must use a distinct gradient id or SVG defs collide across multiple cards on one page");
});

test("buildDiffStripHtml: a direction flip renders 'Reversed', not a numeric delta", () => {
  const html = buildDiffStripHtml("bullish", 0.52, "bearish", 0.54);
  assert.match(html, /Reversed/);
  assert.match(html, /BUY 52%/);
  assert.match(html, /SELL 54%/);
});

test("buildDiffStripHtml: same direction, no change returns empty string", () => {
  assert.equal(buildDiffStripHtml("bullish", 0.52, "bullish", 0.52), "");
});

test("buildDiffStripHtml: same direction, a real change renders a delta", () => {
  const html = buildDiffStripHtml("bullish", 0.50, "bullish", 0.55);
  assert.match(html, /\+5pp/);
});

test("diffPieSvg returns an svg string", () => {
  assert.match(diffPieSvg(50, 5), /<svg/);
});

test("dayStripHtml marks exactly one cell 'today' and one cell 'event' when the event falls within the strip", () => {
  const today = new Date();
  const html = dayStripHtml(today.toISOString());
  const todayCount = (html.match(/class="day-cell today event"/g) || []).length
    + (html.match(/class="day-cell event today"/g) || []).length
    + (html.match(/class="day-cell today"/g) || []).length;
  assert.ok(todayCount >= 1, "expected at least one cell marked today");
});

test("toIsoDateLocal formats a Date as YYYY-MM-DD using LOCAL date fields, not UTC", () => {
  const d = new Date(2026, 8, 11); // September 11 2026, local time, month is 0-indexed
  assert.equal(toIsoDateLocal(d), "2026-09-11");
});

test("formatEventDateTime returns a non-empty locale string for a real ISO timestamp", () => {
  const result = formatEventDateTime("2026-09-11T12:30:00Z");
  assert.ok(result.length > 0);
});

test("tier1DirectionLabel: Guessing+neutral (no confident call) reads 'NO CALL', not 'INDECISIVE'", () => {
  assert.equal(tier1DirectionLabel({ confidence: "Guessing", predicted_direction: "neutral" }), "NO CALL");
});

test("tier1DirectionLabel: a real neutral call (not Guessing) still reads INDECISIVE via directionLabel", () => {
  assert.equal(tier1DirectionLabel({ confidence: "Certain", predicted_direction: "neutral" }), "INDECISIVE");
});
```

- [ ] **Step 3: Delete the placeholder test, run the real suite**

```bash
rm webapp/static/js/_setup.test.js
npm test
```
Expected: all `format.test.js` tests pass, `_setup.test.js` no longer runs (deleted).

- [ ] **Step 4: Update app.js to import from format.js instead of defining these functions inline**

In `webapp/static/app.js`:
1. Remove the following function/variable definitions from `app.js` entirely (they now live in `format.js`): `escapeHtml`, `confidenceColorClass`, `formatEventDateTime`, `toIsoDateLocal`, `directionLabel`, `directionClass`, `directionPct`, `gaugeSvg`, `_bullBearScaleCounter`, `bullBearScaleSvg`, `buildDiffStripHtml`, `diffPieSvg`, `dayStripHtml`. Also remove `tier1DirectionLabel` from wherever it's currently nested inside `renderCard()` (it will be reintroduced as an import — its nested-closure copy is now redundant).
2. Add this import at the very top of `app.js`, before `const POLL_INTERVAL_MS = 60_000;`:
```javascript
import {
  escapeHtml, confidenceColorClass, formatEventDateTime, toIsoDateLocal,
  directionLabel, directionClass, directionPct, gaugeSvg, bullBearScaleSvg,
  buildDiffStripHtml, diffPieSvg, dayStripHtml, tier1DirectionLabel,
} from "./js/format.js";
```
3. Inside `renderCard()`, delete the old nested `function tier1DirectionLabel(tier1) { ... }` definition (now shadowed by the top-level import) — every call site (`tier1DirectionLabel(tier1)` inside `tier1PredictionHtml`/`otherEventTier1MarkerHtml`) needs no change since the imported name is identical.

- [ ] **Step 5: Live-verify**

Restart the dashboard server (static file + module import changes need a fresh page load, not a server restart, but confirm no stale server process is serving an old cached `app.js` — see this project's own prior sessions' PID-restart steps if a stray process is squatting on the port). Reload the dashboard in the Browser pane, screenshot the Dashboard tab, confirm every card renders identically to before (gauges, bull-bear scale, diff strips, day strip all present and visually unchanged). Check `read_console_messages` for import errors (a wrong relative path in the `import` statement is the most likely failure mode here — `./js/format.js` is relative to `app.js`'s own location at `webapp/static/app.js`, so it resolves to `webapp/static/js/format.js`, which is where Step 1 created it).

- [ ] **Step 6: Commit**

```bash
git add webapp/static/js/format.js webapp/static/js/format.test.js webapp/static/app.js
git commit -m "refactor: extract format.js's pure formatting functions from app.js"
```

---

### Task 4: card-view-model.js + card.js (built alongside the old renderCard(), not wired in yet)

**Files:**
- Create: `webapp/static/js/dashboard/card-view-model.js`
- Create: `webapp/static/js/dashboard/card-view-model.test.js`
- Create: `webapp/static/js/dashboard/card.js`
- Create: `webapp/static/js/dashboard/card.test.js`

**Interfaces:**
- Consumes: `format.js`'s exports (Task 3); `webapp/static/vendor/lit-html.js`'s `html` and `webapp/static/vendor/directives/repeat.js`'s `repeat` (Task 1).
- Produces: `buildCardViewModel(prediction, cardUiState) -> object` and `cardTemplate(viewModel) -> lit-html TemplateResult` — Task 5 (interactions) and Task 6 (keyed rendering wiring) import both by exact name. `cardUiState` shape: `{ flipped: bool, articleHistoryLoaded: bool, articleHistory: array|null, historyPanelOpen: bool, historyPanelLoaded: bool, historyPanelData: object|null, breakdownPanelOpen: bool }` — every field optional/undefined-safe (a card with no prior UI state, `{}`, must render exactly as the very first paint does today).

This task builds the NEW modules alongside the untouched OLD `renderCard()` — nothing is wired into the live poll yet (that's Task 6). Every decision `renderCard()`'s nested closures currently make gets pulled into `buildCardViewModel()` as a plain, testable computation; `card.js`'s templates become thin — mostly interpolating already-decided values.

- [ ] **Step 1: Write card-view-model.js**

```javascript
// webapp/static/js/dashboard/card-view-model.js
//
// Pure functions: given one prediction event dict (from /api/predictions'
// events[0]) plus this card's UI-only state, compute every value the
// template needs already decided. Extracted from the original
// monolithic renderCard()'s ~20 nested closures — same responsibilities,
// now testable without a DOM. See
// docs/superpowers/specs/2026-09-11-frontend-rendering-refactor-design.md.

import { directionLabel, directionClass, directionPct, tier1DirectionLabel } from "../format.js";

export function buildArticlePredictionViewModel(pred, prevPred) {
  if (!pred) return null;
  return {
    direction: pred.direction,
    dirClass: directionClass(pred.direction),
    pct: directionPct(pred.probability, pred.direction),
    articleCount: pred.article_count,
    probability: pred.probability,
    hasDiff: !!prevPred,
    prevDirection: prevPred?.direction,
    prevProbability: prevPred?.probability,
    currDirection: pred.direction,
    currProbability: pred.probability,
  };
}

export function buildArticlePredictionConflictViewModel(conflict) {
  if (!conflict) return null;
  return { titles: conflict.titles };
}

export function buildTier1PredictionViewModel(tier1, symbolForCard) {
  if (!tier1) return null;
  return {
    symbolForCard,
    directionLabel: tier1DirectionLabel(tier1),
    dirClass: directionClass(tier1.predicted_direction),
    confidence: tier1.confidence,
    source: tier1.source,
    value: tier1.value,
  };
}

export function buildTier1SentimentConflictViewModel(conflict) {
  if (!conflict) return null;
  return {
    tier1DirectionLabel: directionLabel(conflict.tier1_direction),
    sentimentDirectionLabel: directionLabel(conflict.sentiment_direction),
  };
}

export function buildTier1ConfidenceDowngradeViewModel(downgrade) {
  if (!downgrade) return null;
  return {
    displayedConfidence: downgrade.displayed_confidence,
    originalConfidence: downgrade.original_confidence,
    series: downgrade.series,
    reason: downgrade.reason || null,
  };
}

export function buildPrintPredictionViewModel(printPred) {
  if (!printPred) return null;
  const label = printPred.direction === "higher" ? "HIGHER than forecast"
    : printPred.direction === "lower" ? "LOWER than forecast" : "IN LINE with forecast";
  const confPct = Math.round(printPred.confidence * 100);
  return { label, confPct };
}

export function buildKalshiReadViewModel(kalshi) {
  if (!kalshi) return null;
  const label = kalshi.implied_direction === "higher" ? "HIGHER than forecast"
    : kalshi.implied_direction === "lower" ? "LOWER than forecast" : "IN LINE with forecast";
  return {
    label,
    pct: Math.round(kalshi.implied_probability * 100),
    openInterest: Math.round(kalshi.open_interest),
  };
}

export function buildTrendSignalViewModel(trend) {
  if (!trend) return null;
  const lean = trend.instrument_lean;
  return {
    direction: trend.direction,
    strength: trend.strength.toFixed(2),
    leanLabel: lean ? (lean === "bullish" ? "BUY" : "SELL") : null,
  };
}

export function buildBreakdownPanelViewModel(prediction) {
  const rows = [];
  if (prediction.article_prediction) {
    rows.push({ icon: "📰", text: `Article sentiment: ${directionLabel(prediction.article_prediction.direction)} (${prediction.article_prediction.article_count} articles)` });
  }
  if (prediction.print_prediction) {
    rows.push({ icon: "📊", text: `Print-direction lexicon: ${prediction.print_prediction.direction} (${Math.round(prediction.print_prediction.confidence * 100)}% conf.)` });
  }
  if (prediction.trend_signal) {
    const lean = prediction.trend_signal.instrument_lean;
    const leanLabel = lean ? ` — lean: ${lean === "bullish" ? "BUY" : "SELL"}` : "";
    rows.push({ icon: "📈", text: `Trend streak: ${prediction.trend_signal.direction} (strength ${prediction.trend_signal.strength.toFixed(2)})${leanLabel}` });
  }
  if (prediction.kalshi_read) {
    rows.push({ icon: "💰", text: `Kalshi market: ${prediction.kalshi_read.implied_direction} (${Math.round(prediction.kalshi_read.implied_probability * 100)}% implied)` });
  }
  return { rows, isEmpty: rows.length === 0 };
}

export function buildEssenceArticleViewModel(e) {
  const essence = e.direction === "pending"
    ? { pending: true }
    : { pending: false, dirClass: directionClass(e.direction), label: directionLabel(e.direction), pct: directionPct(e.probability, e.direction) };
  const article = e.article_prediction
    ? { dirClass: directionClass(e.article_prediction.direction), label: directionLabel(e.article_prediction.direction), pct: directionPct(e.article_prediction.probability, e.article_prediction.direction) }
    : null;
  return { essence, article };
}

export function buildOtherEventTier1MarkerViewModel(tier1, symbolForCard) {
  if (!tier1) return null;
  return { symbolForCard, dirClass: directionClass(tier1.predicted_direction), label: tier1DirectionLabel(tier1) };
}

// Sibling/other-tracked-event row view model: title, when-label (optional,
// only for otherTrackedEventsHtml's cross-day list, not the same-time
// otherEventsHtml list), essence/article dual-numbers, and every marker
// (tier1, tier1 conflict, tier1 downgrade).
export function buildOtherEventRowViewModel(e, symbolForCard, includeWhenLabel) {
  return {
    title: e.event_title,
    whenLabel: includeWhenLabel ? e.event_time_utc : null,
    essenceArticle: buildEssenceArticleViewModel(e),
    tier1Marker: buildOtherEventTier1MarkerViewModel(e.tier1_prediction, symbolForCard),
    hasConflict: !!e.tier1_sentiment_conflict,
    hasDowngrade: !!e.tier1_confidence_downgrade,
    downgradeDisplayedConfidence: e.tier1_confidence_downgrade?.displayed_confidence ?? null,
  };
}

export function buildOtherEventsViewModel(events, symbolForCard) {
  if (!events || events.length === 0) return null;
  const simultaneous = events.slice(1).filter((e) => e.event_time_utc === events[0].event_time_utc);
  if (simultaneous.length === 0) return null;
  return {
    count: simultaneous.length,
    rows: simultaneous.map((e) => buildOtherEventRowViewModel(e, symbolForCard, false)),
  };
}

const OTHER_TRACKED_EVENTS_LIMIT = 3;

export function buildOtherTrackedEventsViewModel(allEvents, symbolForCard) {
  if (!allEvents || allEvents.length === 0) return null;
  const featuredTime = allEvents[0].event_time_utc;
  const candidates = allEvents.slice(1).filter((e) => e.event_time_utc !== featuredTime);
  const conflicts = candidates.filter((e) => e.tier1_sentiment_conflict);
  const nonConflicts = candidates.filter((e) => !e.tier1_sentiment_conflict);
  const rest = conflicts.concat(nonConflicts).slice(0, OTHER_TRACKED_EVENTS_LIMIT);
  if (rest.length === 0) return null;
  return { rows: rest.map((e) => buildOtherEventRowViewModel(e, symbolForCard, true)) };
}

// buildCardViewModel: the top-level entry point. `prediction` is one
// entry from /api/predictions' `predictions[].events[0]` PLUS its
// sibling `events` array (the whole symbol entry, per the API's actual
// shape: { symbol, symbol_class, events: [...] }). `uiState` is this
// card's entry from the cardState Map (Task 6), defaulting to {} for a
// card with no prior interaction.
export function buildCardViewModel(symbolEntry, uiState = {}) {
  const { symbol, symbol_class, events } = symbolEntry;
  const next = events[0];

  if (next.direction === "pending") {
    const articlePrediction = buildArticlePredictionViewModel(next.article_prediction, next.previous_article_prediction);
    const tier1Prediction = buildTier1PredictionViewModel(next.tier1_prediction, symbol);
    const printPrediction = buildPrintPredictionViewModel(next.print_prediction);
    const kalshiRead = buildKalshiReadViewModel(next.kalshi_read);
    const trendSignal = buildTrendSignalViewModel(next.trend_signal);
    const hasAnySignal = !!(articlePrediction || tier1Prediction || printPrediction || kalshiRead || trendSignal);
    return {
      symbol, isPending: true,
      pendingHeading: hasAnySignal ? `Awaiting essence score: ${next.event_title}` : `Awaiting: ${next.event_title}`,
      eventTimeUtc: next.event_time_utc,
      articlePrediction,
      articlePredictionConflict: articlePrediction ? null : buildArticlePredictionConflictViewModel(next.article_prediction_conflict),
      tier1Prediction,
      tier1SentimentConflict: buildTier1SentimentConflictViewModel(next.tier1_sentiment_conflict),
      tier1ConfidenceDowngrade: buildTier1ConfidenceDowngradeViewModel(next.tier1_confidence_downgrade),
      printPrediction, kalshiRead, trendSignal,
      otherEvents: buildOtherEventsViewModel(events, symbol),
      otherTrackedEvents: buildOtherTrackedEventsViewModel(events, symbol),
      next, uiState,
    };
  }

  const pct = directionPct(next.probability, next.direction);
  const dirClass = directionClass(next.direction);
  const hasPreviousChange = next.previous_probability !== null && next.previous_probability !== undefined
    && next.previous_direction !== "pending"
    && Math.abs(next.previous_probability - next.probability) > 1e-6;
  const justReleased = next.previous_direction === "pending" && next.direction !== "pending";
  const articlePrediction = buildArticlePredictionViewModel(next.article_prediction, next.previous_article_prediction);

  return {
    symbol, isPending: false,
    eventTitle: next.event_title, eventTimeUtc: next.event_time_utc,
    direction: next.direction, pct, dirClass, probability: next.probability,
    justReleased,
    hasPreviousChange,
    prevDirection: next.previous_direction, prevProbability: next.previous_probability,
    articlePrediction,
    articlePredictionConflict: articlePrediction ? null : buildArticlePredictionConflictViewModel(next.article_prediction_conflict),
    tier1Prediction: buildTier1PredictionViewModel(next.tier1_prediction, symbol),
    tier1SentimentConflict: buildTier1SentimentConflictViewModel(next.tier1_sentiment_conflict),
    tier1ConfidenceDowngrade: buildTier1ConfidenceDowngradeViewModel(next.tier1_confidence_downgrade),
    printPrediction: buildPrintPredictionViewModel(next.print_prediction),
    kalshiRead: buildKalshiReadViewModel(next.kalshi_read),
    trendSignal: buildTrendSignalViewModel(next.trend_signal),
    otherEvents: buildOtherEventsViewModel(events, symbol),
    otherTrackedEvents: buildOtherTrackedEventsViewModel(events, symbol),
    breakdownPanel: buildBreakdownPanelViewModel(next),
    next, uiState,
  };
}
```

- [ ] **Step 2: Write card-view-model.test.js**

```javascript
// webapp/static/js/dashboard/card-view-model.test.js
import test from "node:test";
import assert from "node:assert/strict";
import {
  buildArticlePredictionViewModel, buildTier1PredictionViewModel,
  buildTier1ConfidenceDowngradeViewModel, buildEssenceArticleViewModel,
  buildOtherEventsViewModel, buildOtherTrackedEventsViewModel, buildCardViewModel,
} from "./card-view-model.js";

test("buildArticlePredictionViewModel returns null when no prediction exists (never fabricated)", () => {
  assert.equal(buildArticlePredictionViewModel(null, null), null);
});

test("buildArticlePredictionViewModel computes dirClass/pct from a real prediction", () => {
  const vm = buildArticlePredictionViewModel({ direction: "bearish", probability: 0.44, article_count: 12 }, null);
  assert.equal(vm.dirClass, "bearish");
  assert.equal(vm.pct, 56); // directionPct complement for bearish
  assert.equal(vm.articleCount, 12);
  assert.equal(vm.hasDiff, false);
});

test("buildTier1PredictionViewModel returns null when no Tier1 row exists", () => {
  assert.equal(buildTier1PredictionViewModel(null, "XAUUSD"), null);
});

test("buildTier1PredictionViewModel: a Guessing/neutral row reads NO CALL", () => {
  const vm = buildTier1PredictionViewModel(
    { confidence: "Guessing", predicted_direction: "neutral", source: "Cleveland Fed", value: "no confident call" },
    "XAUUSD",
  );
  assert.equal(vm.directionLabel, "NO CALL");
  assert.equal(vm.symbolForCard, "XAUUSD");
});

test("buildTier1ConfidenceDowngradeViewModel returns null with no downgrade", () => {
  assert.equal(buildTier1ConfidenceDowngradeViewModel(null), null);
});

test("buildTier1ConfidenceDowngradeViewModel passes through reason=null honestly, never fabricated text", () => {
  const vm = buildTier1ConfidenceDowngradeViewModel({ displayed_confidence: "Likely", original_confidence: "Certain", series: "DXY", reason: null });
  assert.equal(vm.reason, null);
});

test("buildEssenceArticleViewModel: pending essence with no article prediction", () => {
  const vm = buildEssenceArticleViewModel({ direction: "pending", probability: null, article_prediction: null });
  assert.equal(vm.essence.pending, true);
  assert.equal(vm.article, null);
});

test("buildEssenceArticleViewModel: real essence AND a real article prediction both surface, independently", () => {
  const vm = buildEssenceArticleViewModel({
    direction: "bearish", probability: 0.5,
    article_prediction: { direction: "bullish", probability: 0.559 },
  });
  assert.equal(vm.essence.pending, false);
  assert.equal(vm.essence.label, "SELL");
  assert.equal(vm.article.label, "BUY");
});

test("buildOtherEventsViewModel returns null when no simultaneous sibling exists", () => {
  const events = [{ event_time_utc: "2026-09-11T12:30:00Z" }];
  assert.equal(buildOtherEventsViewModel(events, "XAUUSD"), null);
});

test("buildOtherEventsViewModel includes only genuinely simultaneous siblings", () => {
  const events = [
    { event_title: "Core CPI m/m", event_time_utc: "2026-09-11T12:30:00Z" },
    { event_title: "CPI m/m", event_time_utc: "2026-09-11T12:30:00Z" },
    { event_title: "Unrelated Later Event", event_time_utc: "2026-09-12T09:00:00Z" },
  ];
  const vm = buildOtherEventsViewModel(events, "XAUUSD");
  assert.equal(vm.count, 1);
  assert.equal(vm.rows[0].title, "CPI m/m");
});

test("buildOtherTrackedEventsViewModel promotes conflict-flagged rows to the front before bounding", () => {
  const events = [
    { event_title: "Featured", event_time_utc: "2026-09-11T12:30:00Z" },
    { event_title: "No Conflict A", event_time_utc: "2026-09-10T12:30:00Z" },
    { event_title: "Has Conflict", event_time_utc: "2026-09-09T12:30:00Z", tier1_sentiment_conflict: { tier1_direction: "bullish", sentiment_direction: "bearish" } },
    { event_title: "No Conflict B", event_time_utc: "2026-09-08T12:30:00Z" },
    { event_title: "No Conflict C", event_time_utc: "2026-09-07T12:30:00Z" },
  ];
  const vm = buildOtherTrackedEventsViewModel(events, "XAUUSD");
  assert.equal(vm.rows[0].title, "Has Conflict", "the conflict row must be promoted to the front, not lost to the 3-item bound");
  assert.equal(vm.rows.length, 3);
});

test("buildCardViewModel: pending branch produces isPending:true with the right heading when a signal exists", () => {
  const symbolEntry = {
    symbol: "XAUUSD", symbol_class: "metal",
    events: [{
      direction: "pending", event_title: "Prelim UoM Consumer Sentiment", event_time_utc: "2026-09-11T16:00:00Z",
      article_prediction: { direction: "bearish", probability: 0.56, article_count: 139 },
      previous_article_prediction: null, article_prediction_conflict: null,
      tier1_prediction: null, tier1_sentiment_conflict: null, tier1_confidence_downgrade: null,
      print_prediction: null, kalshi_read: null, trend_signal: null,
    }],
  };
  const vm = buildCardViewModel(symbolEntry, {});
  assert.equal(vm.isPending, true);
  assert.match(vm.pendingHeading, /Awaiting essence score/);
});

test("buildCardViewModel: resolved branch computes pct/dirClass and passes uiState through untouched", () => {
  const symbolEntry = {
    symbol: "XAUUSD", symbol_class: "metal",
    events: [{
      direction: "bearish", probability: 0.5, event_title: "Core CPI m/m", event_time_utc: "2026-09-11T12:30:00Z",
      previous_direction: "bullish", previous_probability: 0.53,
      article_prediction: null, article_prediction_conflict: null,
      tier1_prediction: null, tier1_sentiment_conflict: null, tier1_confidence_downgrade: null,
      print_prediction: null, kalshi_read: null, trend_signal: null,
    }],
  };
  const uiState = { flipped: true };
  const vm = buildCardViewModel(symbolEntry, uiState);
  assert.equal(vm.isPending, false);
  assert.equal(vm.dirClass, "bearish");
  assert.equal(vm.hasPreviousChange, true, "a direction reversal from previous must be flagged, even though buildDiffStripHtml renders it as Reversed, not a delta");
  assert.equal(vm.uiState, uiState, "uiState must pass through unchanged for card.js to read");
});
```

- [ ] **Step 3: Run the new tests, confirm they pass**

```bash
npm test
```
Expected: all `card-view-model.test.js` tests pass, no regressions in `format.test.js`.

- [ ] **Step 4: Write card.js**

```javascript
// webapp/static/js/dashboard/card.js
//
// lit-html templates for one Dashboard card. Thin — reads already-decided
// values from the view model (card-view-model.js); minimal branching of
// its own. Each sub-signal is its own named template function, matching
// the original renderCard()'s nested-closure boundaries.

import { html } from "../../vendor/lit-html.js";
import { escapeHtml, gaugeSvg, bullBearScaleSvg, buildDiffStripHtml, dayStripHtml } from "../format.js";

export function articlePredictionTemplate(vm) {
  if (!vm) return html``;
  const diffHtml = vm.hasDiff
    ? buildDiffStripHtml(vm.prevDirection, vm.prevProbability, vm.currDirection, vm.currProbability)
    : "";
  return html`<div class="article-prediction ${vm.dirClass}">
    📰 Article-based read: <b>${vm.dirClass === "bearish" ? "SELL" : vm.dirClass === "bullish" ? "BUY" : "INDECISIVE"} ${vm.pct}%</b>
    <span style="font-size:12px;color:#888">(backed by ${vm.articleCount} article${vm.articleCount === 1 ? "" : "s"})</span>
    <div class="bull-bear-scale">${html([bullBearScaleSvg(vm.probability)])}</div>
    ${html([diffHtml])}
  </div>`;
}

export function articlePredictionConflictTemplate(vm) {
  if (!vm) return html``;
  return html`<div class="article-prediction-conflict">
    ⚠ Conflicting signals across co-released events
    <span style="font-size:12px;color:#888">(${vm.titles.map(escapeHtml).join(", ")})</span>
  </div>`;
}

export function tier1PredictionTemplate(vm) {
  if (!vm) return html``;
  return html`<div class="tier1-prediction ${vm.dirClass}">
    🧮 Tier 1 (${escapeHtml(vm.symbolForCard)}): <b>${vm.directionLabel}</b>
    <span style="font-size:12px;color:#888">— ${escapeHtml(vm.confidence)}, ${escapeHtml(vm.source)}</span>
    <div style="font-size:11px;color:#999">${escapeHtml(vm.value)}</div>
  </div>`;
}

export function tier1SentimentConflictTemplate(vm) {
  if (!vm) return html``;
  return html`<div class="tier1-sentiment-conflict">
    ⚠ Tier 1 vs. sentiment disagree: <b>${vm.tier1DirectionLabel}</b> vs <b>${vm.sentimentDirectionLabel}</b>
  </div>`;
}

export function tier1ConfidenceDowngradeTemplate(vm) {
  if (!vm) return html``;
  return html`<div class="tier1-confidence-downgrade">
    ⚠ Confidence downgraded to <b>${vm.displayedConfidence}</b>
    (was ${vm.originalConfidence}) — unexplained ${vm.series} move${vm.reason ? html`: ${escapeHtml(vm.reason)}` : html``}
  </div>`;
}

export function printPredictionTemplate(vm) {
  if (!vm) return html``;
  return html`<div class="print-prediction">
    📊 Print call: likely <b>${vm.label}</b> <span class="confidence-${vm.confPct >= 66 ? "high" : vm.confPct >= 33 ? "medium" : "low"}">(${vm.confPct}% confidence)</span>
  </div>`;
}

export function kalshiReadTemplate(vm) {
  if (!vm) return html``;
  return html`<div class="kalshi-read">
    💰 Kalshi market: likely <b>${vm.label}</b> <span style="font-size:12px;color:#888">(${vm.pct}% implied, ${vm.openInterest} open interest)</span>
  </div>`;
}

export function trendSignalTemplate(vm) {
  if (!vm) return html``;
  return html`<div class="trend-signal">
    📈 Trend streak: <b>${vm.direction}</b> <span style="font-size:12px;color:#888">(strength ${vm.strength})</span>${vm.leanLabel ? html` — lean: <b>${vm.leanLabel}</b>` : html``}
  </div>`;
}

export function breakdownPanelTemplate(vm) {
  if (!vm || vm.isEmpty) return html`<div style="font-size:12px;color:#888">No structured signals fired for this event yet.</div>`;
  return html`${vm.rows.map((r) => html`<div>${r.icon} ${r.text}</div>`)}`;
}

export function otherEventTier1MarkerTemplate(vm) {
  if (!vm) return html``;
  return html`<span class="other-event-tier1 ${vm.dirClass}">🧮 Tier 1 (${escapeHtml(vm.symbolForCard)}): <b>${vm.label}</b></span>`;
}

export function otherEventTier1ConflictMarkerTemplate(hasConflict) {
  if (!hasConflict) return html``;
  return html`<span class="other-event-tier1-conflict">⚠ Tier 1 vs. sentiment disagree</span>`;
}

export function otherEventTier1DowngradeMarkerTemplate(hasDowngrade, displayedConfidence) {
  if (!hasDowngrade) return html``;
  return html`<span class="other-event-tier1-downgrade">⚠ Confidence downgraded to <b>${displayedConfidence}</b></span>`;
}

export function essenceArticleTemplate(vm) {
  const essenceHtml = vm.essence.pending
    ? html`<span class="other-event-pending">Essence: Pending</span>`
    : html`<span class="other-event-call ${vm.essence.dirClass}">Essence: ${vm.essence.label} ${vm.essence.pct}%</span>`;
  const articleHtml = vm.article
    ? html` <span class="other-event-article ${vm.article.dirClass}">Article: ${vm.article.label} ${vm.article.pct}%</span>`
    : html``;
  return html`${essenceHtml}${articleHtml}`;
}

function otherEventRowTemplate(row) {
  return html`<div class="other-event-row">
    <span class="other-event-title">${escapeHtml(row.title)}${row.whenLabel ? html` <span style="font-size:11px;color:#888">(${new Date(row.whenLabel).toLocaleString()})</span>` : html``}</span>
    ${essenceArticleTemplate(row.essenceArticle)}
    ${otherEventTier1MarkerTemplate(row.tier1Marker)}
    ${otherEventTier1ConflictMarkerTemplate(row.hasConflict)}
    ${otherEventTier1DowngradeMarkerTemplate(row.hasDowngrade, row.downgradeDisplayedConfidence)}
  </div>`;
}

export function otherEventsTemplate(vm) {
  if (!vm) return html``;
  return html`<div class="other-events">
    <div class="other-events-heading">${vm.count} more event${vm.count === 1 ? "" : "s"} at this time</div>
    ${vm.rows.map(otherEventRowTemplate)}
  </div>`;
}

export function otherTrackedEventsTemplate(vm) {
  if (!vm) return html``;
  return html`<div class="other-events">
    <div class="other-events-heading">Other tracked events</div>
    ${vm.rows.map(otherEventRowTemplate)}
  </div>`;
}

// cardTemplate: the top-level card. `flipHandlers` is an object of event
// handler functions supplied by card-flip.js (Task 5) — kept as a
// parameter rather than imported directly so card.js has zero dependency
// on cardState/interaction wiring, staying a pure function of (viewModel,
// handlers) -> TemplateResult.
export function cardTemplate(vm, flipHandlers) {
  const safeSymbol = escapeHtml(vm.symbol);
  if (vm.isPending) {
    return html`<div class="card">
      <div class="card-header">
        <h3 class="symbol-flip-trigger" data-symbol="${safeSymbol}" @click=${() => flipHandlers.onFlipClick(vm.symbol)}>${safeSymbol}</h3>
        <button class="remove-btn" @click=${() => flipHandlers.onRemoveClick(vm.symbol)}>Remove</button>
      </div>
      <div class="pending">${vm.pendingHeading}<br>
        <span style="font-size:12px;color:#888">${new Date(vm.eventTimeUtc).toLocaleString()}</span></div>
      ${articlePredictionTemplate(vm.articlePrediction)}${articlePredictionConflictTemplate(vm.articlePredictionConflict)}
      ${tier1PredictionTemplate(vm.tier1Prediction)}${tier1SentimentConflictTemplate(vm.tier1SentimentConflict)}${tier1ConfidenceDowngradeTemplate(vm.tier1ConfidenceDowngrade)}
      ${printPredictionTemplate(vm.printPrediction)}${kalshiReadTemplate(vm.kalshiRead)}${trendSignalTemplate(vm.trendSignal)}
      ${otherEventsTemplate(vm.otherEvents)}${otherTrackedEventsTemplate(vm.otherTrackedEvents)}
    </div>`;
  }

  return html`<div class="card ${vm.uiState.flipped ? "card-has-flip flipped" : ""}">
    <div class="card-flip-inner">
      <div class="card-flip-front">
        <div class="card-header">
          <h3 class="symbol-flip-trigger" data-symbol="${safeSymbol}" @click=${() => flipHandlers.onFlipClick(vm.symbol)}>${safeSymbol}</h3>
          <button class="remove-btn" @click=${() => flipHandlers.onRemoveClick(vm.symbol)}>Remove</button>
        </div>
        ${vm.justReleased ? html`<div class="just-released ${vm.dirClass}">🎯 Just released — ${vm.dirClass === "bearish" ? "SELL" : vm.dirClass === "bullish" ? "BUY" : "INDECISIVE"} ${vm.pct}%</div>` : html``}
        ${vm.hasPreviousChange ? html([buildDiffStripHtml(vm.prevDirection, vm.prevProbability, vm.direction, vm.probability)]) : html``}
        <div class="gauge-row">${html([gaugeSvg(vm.pct, vm.direction)])}
          <div><div class="gauge-label ${vm.dirClass}">Essence: ${vm.dirClass === "bearish" ? "SELL" : vm.dirClass === "bullish" ? "BUY" : "INDECISIVE"} ${vm.pct}%</div>
          <div style="font-size:12px;color:#888">${escapeHtml(vm.eventTitle)}</div>
          ${articlePredictionTemplate(vm.articlePrediction)}${articlePredictionConflictTemplate(vm.articlePredictionConflict)}
          ${tier1PredictionTemplate(vm.tier1Prediction)}${tier1SentimentConflictTemplate(vm.tier1SentimentConflict)}${tier1ConfidenceDowngradeTemplate(vm.tier1ConfidenceDowngrade)}
          ${printPredictionTemplate(vm.printPrediction)}${kalshiReadTemplate(vm.kalshiRead)}</div></div>
        <div class="bull-bear-scale">${html([bullBearScaleSvg(vm.probability)])}</div>
        ${otherEventsTemplate(vm.otherEvents)}${otherTrackedEventsTemplate(vm.otherTrackedEvents)}
        ${html([dayStripHtml(vm.eventTimeUtc)])}
        <div class="history-toggle">
          <button class="history-toggle-btn" @click=${() => flipHandlers.onHistoryToggle(vm.symbol, vm.eventTitle)}>History ▾</button>
          <div class="history-panel" style="display:${vm.uiState.historyPanelOpen ? "" : "none"}">${flipHandlers.historyPanelContent(vm.uiState)}</div>
        </div>
        <div class="history-toggle">
          <button class="breakdown-toggle-btn" @click=${() => flipHandlers.onBreakdownToggle(vm.symbol)}>Why this call ▾</button>
          <div class="history-panel" style="display:${vm.uiState.breakdownPanelOpen ? "" : "none"}">${breakdownPanelTemplate(vm.breakdownPanel)}</div>
        </div>
      </div>
      <div class="card-flip-back">
        <div class="card-header">
          <h3>${safeSymbol} — why this changed</h3>
          <button class="flip-back-btn" @click=${() => flipHandlers.onFlipClick(vm.symbol, false)}>✕ Back</button>
        </div>
        <div class="article-progression">${flipHandlers.articleProgressionContent(vm.uiState)}</div>
      </div>
    </div>
  </div>`;
}
```

Note on `html([someString])`: `lit-html`'s `html` tagged template function requires a template literal (a tagged-template call site), not a plain function call with a string argument — passing a pre-built HTML string through `html([...])` is a deliberate escape hatch for the handful of places (SVG builders in `format.js`, `buildDiffStripHtml`'s pre-built markup) that still return raw HTML strings rather than being rewritten as `lit-html` templates themselves. This keeps Task 4 focused on the card-level structure without also rewriting every SVG-generating helper into `lit-html` syntax — an explicitly acceptable interim step per the spec's YAGNI framing (`format.js`'s functions were extracted verbatim in Task 3 specifically to avoid also rewriting their internals here).

- [ ] **Step 5: Write card.test.js**

```javascript
// webapp/static/js/dashboard/card.test.js
import test from "node:test";
import assert from "node:assert/strict";
import {
  articlePredictionTemplate, tier1PredictionTemplate, tier1ConfidenceDowngradeTemplate,
  essenceArticleTemplate, otherEventsTemplate,
} from "./card.js";
import {
  buildArticlePredictionViewModel, buildTier1PredictionViewModel,
  buildTier1ConfidenceDowngradeViewModel, buildEssenceArticleViewModel, buildOtherEventsViewModel,
} from "./card-view-model.js";

// lit-html's `html` tagged template constructs a TemplateResult without
// touching the DOM — these tests inspect `.values` (the interpolated
// values, in template order) to confirm the right data reached the
// template, without needing jsdom.

test("articlePredictionTemplate returns an empty TemplateResult's strings for a null view model", () => {
  const result = articlePredictionTemplate(null);
  assert.equal(result.strings.join(""), "");
});

test("articlePredictionTemplate's values include the computed pct and article count", () => {
  const vm = buildArticlePredictionViewModel({ direction: "bearish", probability: 0.44, article_count: 12 }, null);
  const result = articlePredictionTemplate(vm);
  assert.ok(result.values.includes("SELL"));
  assert.ok(result.values.includes(56));
  assert.ok(result.values.some((v) => String(v).includes("12")));
});

test("tier1PredictionTemplate's values include NO CALL for a Guessing/neutral row", () => {
  const vm = buildTier1PredictionViewModel({ confidence: "Guessing", predicted_direction: "neutral", source: "src", value: "no call" }, "XAUUSD");
  const result = tier1PredictionTemplate(vm);
  assert.ok(result.values.includes("NO CALL"));
});

test("tier1ConfidenceDowngradeTemplate omits a reason clause's TemplateResult when reason is null", () => {
  const vm = buildTier1ConfidenceDowngradeViewModel({ displayed_confidence: "Likely", original_confidence: "Certain", series: "DXY", reason: null });
  const result = tier1ConfidenceDowngradeTemplate(vm);
  assert.ok(result.values.includes("Likely"));
  assert.ok(result.values.includes("Certain"));
  assert.ok(result.values.includes("DXY"));
});

test("essenceArticleTemplate: pending essence, no article — only one labeled span produced", () => {
  const vm = buildEssenceArticleViewModel({ direction: "pending", probability: null, article_prediction: null });
  const result = essenceArticleTemplate(vm);
  assert.equal(result.strings.join("").includes("Essence"), true);
});

test("otherEventsTemplate returns an empty TemplateResult when the view model is null (no simultaneous siblings)", () => {
  const vm = buildOtherEventsViewModel([{ event_time_utc: "2026-09-11T12:30:00Z" }], "XAUUSD");
  const result = otherEventsTemplate(vm);
  assert.equal(result.strings.join(""), "");
});
```

- [ ] **Step 6: Run the tests**

```bash
npm test
```
Expected: all tests pass, including the new `card.test.js` file.

- [ ] **Step 7: Live-verify (build-only, not wired in — confirms no syntax errors, no behavior change yet)**

Run `node --check webapp/static/js/dashboard/card-view-model.js webapp/static/js/dashboard/card.js` (both files are ES modules; `node --check` validates syntax without executing top-level import side effects against a missing DOM). Reload the dashboard in the Browser pane and confirm it still renders exactly as before — Task 4 adds new, unused files only, so no visual change is expected; this step exists only to confirm nothing was accidentally broken (e.g. a stray syntax error in `app.js`'s existing content).

- [ ] **Step 8: Commit**

```bash
git add webapp/static/js/dashboard/card-view-model.js webapp/static/js/dashboard/card-view-model.test.js webapp/static/js/dashboard/card.js webapp/static/js/dashboard/card.test.js
git commit -m "feat: build card-view-model.js + card.js alongside the old renderCard() (not yet wired in)"
```

---

### Task 5: api.js + card-flip.js (interaction handlers, cardState)

**Files:**
- Create: `webapp/static/js/api.js`
- Create: `webapp/static/js/dashboard/card-flip.js`
- Create: `webapp/static/js/dashboard/card-flip.test.js`

**Interfaces:**
- Consumes: none new.
- Produces: `fetchPredictions()`, `fetchCalendar()`, `fetchCalendarDate(dateStr)`, `fetchHistory()`, `fetchArticleHistory(symbol, eventTitle)`, `fetchEventHistory(eventTitle)` (all `-> Promise<object>`, throwing on a non-ok response) from `api.js`; `createCardFlipHandlers(cardState, callbacks)` from `card-flip.js`, where `callbacks` is `{ onRender, onSymbolRemoved }` — `onRender` is called after every state-only mutation (flip, history/breakdown toggle) and should be a cheap re-render of already-fetched data; `onSymbolRemoved` is called after a symbol is actually deleted server-side and must trigger a real re-fetch, not just a re-render, since the removed symbol's stale card otherwise lingers in already-cached data until the next natural poll. Returns the `flipHandlers` object `cardTemplate()` (Task 4) expects: `{ onFlipClick, onRemoveClick, onHistoryToggle, onBreakdownToggle, historyPanelContent, articleProgressionContent }` — Task 6 wires `onRender` to `renderDashboardNow()` and `onSymbolRemoved` to `refreshDashboard()`.

- [ ] **Step 1: Write api.js**

```javascript
// webapp/static/js/api.js
//
// Thin fetch wrappers. No DOM, no rendering — throws a real Error on a
// non-ok response so callers can catch/handle uniformly, same behavior
// dashboard-poll.js / calendar-poll.js (Tasks 6-7) already need.

async function fetchJson(url, options) {
  const resp = await fetch(url, options);
  if (!resp.ok) throw new Error(`HTTP ${resp.status} for ${url}`);
  return resp.json();
}

export function fetchPredictions() {
  return fetchJson("/api/predictions");
}

export function fetchCalendar() {
  return fetchJson("/api/calendar");
}

export function fetchCalendarMonthAhead() {
  return fetchJson("/api/calendar/monthahead");
}

export function fetchCalendarDate(dateStr) {
  return fetchJson(`/api/calendar/date/${dateStr}`);
}

export function fetchHistory() {
  return fetchJson("/api/history");
}

export function fetchHistoryStats() {
  return fetchJson("/api/history/stats");
}

export function fetchArticleHistory(symbol, eventTitle) {
  return fetchJson(`/api/predictions/${symbol}/article_history?event_title=${encodeURIComponent(eventTitle)}`);
}

export function fetchEventHistory(eventTitle) {
  return fetchJson(`/api/event_history?title=${encodeURIComponent(eventTitle)}`);
}

export async function postAddSymbol(ticker) {
  const resp = await fetch("/api/symbols", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker }),
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.error || "Could not add symbol");
  }
}

export function deleteSymbol(ticker) {
  return fetch(`/api/symbols/${ticker}`, { method: "DELETE" });
}
```

Confirm `/api/history/stats` is the real route `loadHistoryStats()` calls today — check `webapp/static/app.js`'s current `loadHistoryStats()` function (around line 1312) for the exact URL before assuming this name; use whatever URL that function actually fetches from.

- [ ] **Step 2: Write card-flip.js**

```javascript
// webapp/static/js/dashboard/card-flip.js
//
// Interaction handlers for one card: flip-to-see-progression, the
// History panel toggle, and the "Why this call" breakdown toggle. Each
// handler mutates `cardState` (a Map, symbol -> per-card UI state) and
// calls `onRender()` to trigger a cheap re-render — except a real symbol
// removal, which calls `onSymbolRemoved()` (a real re-fetch) instead,
// since a removed symbol's card must not linger in already-cached data.
// This file owns no rendering itself, only state transitions plus the
// lazy-fetches that used to live inline inside renderCard()'s DOM event
// listeners.

import { fetchArticleHistory, fetchEventHistory, deleteSymbol } from "../api.js";
import { articleProgressionEntryHtml } from "./article-progression.js";

export function createCardFlipHandlers(cardState, { onRender, onSymbolRemoved }) {
  function getState(symbol) {
    if (!cardState.has(symbol)) cardState.set(symbol, {});
    return cardState.get(symbol);
  }

  async function onFlipClick(symbol, show) {
    const state = getState(symbol);
    const nextFlipped = show === undefined ? !state.flipped : show;
    state.flipped = nextFlipped;
    onRender();
    if (!nextFlipped || state.articleHistoryLoaded) return;
    // Lazily fetches on first flip only (data-loaded guard, same pattern
    // as the History toggle) — flipping back and forth afterward is free.
    const eventTitle = state.currentEventTitle;
    const data = await fetchArticleHistory(symbol, eventTitle);
    state.articleHistoryLoaded = true;
    state.articleHistory = data.progression || [];
    onRender();
  }

  // A real server-side deletion, not a local state mutation — the removed
  // symbol's card must actually disappear now, not linger in
  // already-fetched data until the next natural poll. onSymbolRemoved
  // (wired to refreshDashboard() in dashboard-poll.js) does a real
  // re-fetch; calling onRender() here instead would be a real regression
  // from today's removeSymbol()'s own await-then-refresh behavior.
  async function onRemoveClick(symbol) {
    await deleteSymbol(symbol);
    await onSymbolRemoved();
  }

  async function onHistoryToggle(symbol, eventTitle) {
    const state = getState(symbol);
    state.currentEventTitle = eventTitle;
    state.historyPanelOpen = !state.historyPanelOpen;
    onRender();
    if (!state.historyPanelOpen || state.historyPanelLoaded) return;
    const data = await fetchEventHistory(eventTitle);
    state.historyPanelLoaded = true;
    state.historyPanelData = data;
    onRender();
  }

  function onBreakdownToggle(symbol) {
    const state = getState(symbol);
    state.breakdownPanelOpen = !state.breakdownPanelOpen;
    onRender();
  }

  function historyPanelContent(uiState) {
    if (!uiState.historyPanelOpen) return "";
    if (!uiState.historyPanelLoaded) return "Loading…";
    const occurrences = uiState.historyPanelData?.occurrences || [];
    if (occurrences.length === 0) return "No history recorded yet";
    const rows = occurrences.map((o) => {
      const dateLabel = new Date(o.event_time_utc).toLocaleDateString(undefined, { year: "numeric", month: "short" });
      const surpriseLabel = o.surprise_direction
        ? `(${o.surprise_direction.replace("_", "-")})`
        : (o.actual ? "(untracked)" : "(pending)");
      return `${dateLabel}: forecast ${o.forecast ?? "—"}, previous ${o.previous ?? "—"}, actual ${o.actual ?? "—"} ${surpriseLabel}`;
    }).join(" / ");
    return `${rows} → ${uiState.historyPanelData.trend_summary}`;
  }

  function articleProgressionContent(uiState) {
    if (!uiState.flipped) return "";
    if (!uiState.articleHistoryLoaded) return "Loading…";
    if (uiState.articleHistory.length === 0) return "No article-based read recorded for this event yet.";
    return uiState.articleHistory.map((entry, i) => articleProgressionEntryHtml(entry, i === 0)).join("");
  }

  return { onFlipClick, onRemoveClick, onHistoryToggle, onBreakdownToggle, historyPanelContent, articleProgressionContent };
}
```

Note: `historyPanelContent`/`articleProgressionContent` here return plain strings, matched to `card.js`'s `cardTemplate()` interpolating them directly rather than as nested `lit-html` templates — an intentional, small simplification for this task (these two panels' own internal HTML is not converted to `lit-html` syntax in this refactor; they keep the original string-building approach, unescaped exactly as the original `articleProgressionEntryHtml`/inline history-row functions already were). `article-progression.js` (containing `articleProgressionEntryHtml`, moved verbatim from the current `app.js`, around its existing line 790) must be created as part of this task's Step 2 (alongside `card-flip.js`, which is what imports it) — add it as a new file `webapp/static/js/dashboard/article-progression.js` exporting that one function, moved byte-for-byte from `app.js`'s current definition.

- [ ] **Step 3: Write card-flip.test.js**

```javascript
// webapp/static/js/dashboard/card-flip.test.js
import test from "node:test";
import assert from "node:assert/strict";
import { createCardFlipHandlers } from "./card-flip.js";

test("onFlipClick toggles state.flipped and calls onRender", async () => {
  const cardState = new Map();
  let renderCount = 0;
  const handlers = createCardFlipHandlers(cardState, { onRender: () => { renderCount++; }, onSymbolRemoved: async () => {} });
  await handlers.onFlipClick("XAUUSD");
  assert.equal(cardState.get("XAUUSD").flipped, true);
  assert.ok(renderCount >= 1);
});

test("onFlipClick(symbol, false) forces the flip closed regardless of prior state", async () => {
  const cardState = new Map([["XAUUSD", { flipped: true }]]);
  const handlers = createCardFlipHandlers(cardState, { onRender: () => {}, onSymbolRemoved: async () => {} });
  await handlers.onFlipClick("XAUUSD", false);
  assert.equal(cardState.get("XAUUSD").flipped, false);
});

test("onBreakdownToggle toggles independently of onHistoryToggle's state", () => {
  const cardState = new Map();
  const handlers = createCardFlipHandlers(cardState, { onRender: () => {}, onSymbolRemoved: async () => {} });
  handlers.onBreakdownToggle("XAUUSD");
  assert.equal(cardState.get("XAUUSD").breakdownPanelOpen, true);
  assert.equal(cardState.get("XAUUSD").historyPanelOpen, undefined, "breakdown and history panels must not share state");
});

test("historyPanelContent returns empty string when the panel is closed", () => {
  const cardState = new Map();
  const handlers = createCardFlipHandlers(cardState, { onRender: () => {}, onSymbolRemoved: async () => {} });
  assert.equal(handlers.historyPanelContent({ historyPanelOpen: false }), "");
});

test("historyPanelContent shows Loading… before the fetch resolves", () => {
  const cardState = new Map();
  const handlers = createCardFlipHandlers(cardState, { onRender: () => {}, onSymbolRemoved: async () => {} });
  assert.equal(handlers.historyPanelContent({ historyPanelOpen: true, historyPanelLoaded: false }), "Loading…");
});

test("onRemoveClick calls onSymbolRemoved (a real re-fetch), not onRender (a cheap re-render of stale data)", async () => {
  const cardState = new Map();
  let renderCount = 0, removedCount = 0;
  const handlers = createCardFlipHandlers(cardState, { onRender: () => { renderCount++; }, onSymbolRemoved: async () => { removedCount++; } });
  await handlers.onRemoveClick("XAUUSD");
  assert.equal(removedCount, 1);
  assert.equal(renderCount, 0, "removing a symbol must trigger a real re-fetch, not a render of data that still contains the deleted symbol");
});
```

- [ ] **Step 4: Run the tests**

```bash
npm test
```
Expected: all pass, including the new `card-flip.test.js` file. (These tests call real handler functions with no network — `onFlipClick`'s fetch only fires when `articleHistoryLoaded` is false AND `flipped` becomes true, and `onRemoveClick` always calls `deleteSymbol()`; if `fetch` is not available in the plain Node test environment, stub it: add `global.fetch = async () => ({ ok: true, json: async () => ({ progression: [] }) });` at the top of `card-flip.test.js`, before the tests run, matching Node's built-in global `fetch` — Node 18+ has `fetch` built in, so this stub is a test-only override, not a new dependency.)

- [ ] **Step 5: Live-verify**

Nothing is wired into the live poll yet — run `node --check` on both new files to confirm syntax validity, reload the dashboard, confirm it still renders exactly as before (no visual change expected from this task alone).

- [ ] **Step 6: Commit**

```bash
git add webapp/static/js/api.js webapp/static/js/dashboard/card-flip.js webapp/static/js/dashboard/card-flip.test.js webapp/static/js/dashboard/article-progression.js
git commit -m "feat: build api.js + card-flip.js interaction handlers (not yet wired in)"
```

---

### Task 6: Wire dashboard-poll.js — the actual keyed-render cutover

**Files:**
- Create: `webapp/static/js/dashboard/dashboard-poll.js`
- Create: `webapp/static/js/dashboard/dashboard-poll.test.js`
- Modify: `webapp/static/app.js`

**Interfaces:**
- Consumes: `cardTemplate`/`buildCardViewModel` (Task 4), `createCardFlipHandlers` (Task 5), `fetchPredictions` (Task 5), `repeat` from `webapp/static/vendor/directives/repeat.js` (Task 1), `render`/`html` from `webapp/static/vendor/lit-html.js` (Task 1).
- Produces: `refreshDashboard()` — Task 9's final cleanup confirms `app.js` calls this exact function name, same as it does today.

This is the task that actually removes the old `innerHTML=""` teardown and both restoration hacks — they become structurally impossible to need the instant keyed `repeat()` rendering lands, so removing them here (rather than leaving them as unreachable dead code) is the correct, non-optional part of this task, not a separate cleanup step.

- [ ] **Step 1: Write dashboard-poll.js**

```javascript
// webapp/static/js/dashboard/dashboard-poll.js
//
// refreshDashboard(): fetches /api/predictions, renders every card via
// lit-html's keyed repeat() (keyed by symbol), and owns the one render
// function called from both the poll timer and every card interaction —
// see docs/superpowers/specs/2026-09-11-frontend-rendering-refactor-design.md's
// "Data flow & state model" section.

import { html, render } from "../../vendor/lit-html.js";
import { repeat } from "../../vendor/directives/repeat.js";
import { fetchPredictions } from "../api.js";
import { buildCardViewModel } from "./card-view-model.js";
import { cardTemplate } from "./card.js";
import { createCardFlipHandlers } from "./card-flip.js";
import { renderAccumulatorStaleness } from "../staleness.js";

const cardsEl = document.getElementById("cards");
const predictionsStaleNoticeEl = document.getElementById("predictions-stale-notice");
const predictionsPollErrorEl = document.getElementById("predictions-poll-error-notice");

// symbol -> { flipped, historyPanelOpen, historyPanelLoaded, historyPanelData,
//             breakdownPanelOpen, articleHistoryLoaded, articleHistory, currentEventTitle }
const cardState = new Map();
let latestPredictionsData = null;

function renderDashboardNow() {
  const predictions = latestPredictionsData?.predictions ?? [];
  // onSymbolRemoved is refreshDashboard itself (a real re-fetch), not
  // renderDashboardNow (a cheap re-render of already-cached data) — see
  // card-flip.js's own comment on why this distinction matters.
  const flipHandlers = createCardFlipHandlers(cardState, { onRender: renderDashboardNow, onSymbolRemoved: refreshDashboard });
  render(
    html`${repeat(
      predictions,
      (p) => p.symbol,
      (p) => cardTemplate(buildCardViewModel(p, cardState.get(p.symbol) ?? {}), flipHandlers),
    )}`,
    cardsEl,
  );
}

export async function refreshDashboard() {
  // dashboard-review-2026-09-11.md: a transient network blip here used to
  // throw an unhandled rejection out of this function and silently freeze
  // the dashboard on stale data every subsequent poll, with no visible
  // sign anything was wrong. Caught here instead: leaves whatever's
  // already rendered in place and surfaces a visible, distinct-from-
  // "no data yet" notice. Cleared on the next successful poll.
  let data;
  try {
    data = await fetchPredictions();
  } catch (err) {
    console.error("refreshDashboard: poll failed", err);
    predictionsPollErrorEl.textContent = "Couldn't reach the server — showing the last data received.";
    predictionsPollErrorEl.style.display = "";
    return;
  }
  predictionsPollErrorEl.style.display = "none";

  // "error" here means the background loop (webapp/scheduler.py) hasn't
  // completed its first successful fetch yet — not "a live request just
  // failed," since no route ever fetches live anymore.
  if (data.error) {
    predictionsStaleNoticeEl.textContent = data.error;
    predictionsStaleNoticeEl.style.display = "";
  } else {
    predictionsStaleNoticeEl.textContent = "";
    predictionsStaleNoticeEl.style.display = "none";
  }

  renderAccumulatorStaleness(data.accumulator_staleness_seconds);

  latestPredictionsData = data;
  renderDashboardNow();
}
```

This introduces `webapp/static/js/staleness.js`, exporting `renderFeedStaleness`/`renderAccumulatorStaleness` — move these two verbatim from `app.js`'s current definitions (around lines 42-80) as part of this task's Step 1, same "byte-for-byte, zero logic change" discipline as Task 3, since they were never moved into `format.js` (they read/write specific DOM elements by id, unlike `format.js`'s pure functions).

- [ ] **Step 2: Write dashboard-poll.test.js**

```javascript
// webapp/static/js/dashboard/dashboard-poll.test.js
//
// jsdom test: the property this whole refactor exists to guarantee —
// repeat()'s keyed diffing genuinely preserves a card's DOM node (and
// therefore any state driven onto it) across two successive render()
// calls with the same key but different data.
import test from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";

test("repeat() keyed by symbol preserves the same DOM node across two renders with the same key", async () => {
  const dom = new JSDOM("<!doctype html><html><body><div id='cards'></div></body></html>");
  global.window = dom.window;
  global.document = dom.window.document;
  global.HTMLElement = dom.window.HTMLElement;
  global.Text = dom.window.Text;
  global.customElements = dom.window.customElements;

  const { html, render } = await import("../../vendor/lit-html.js");
  const { repeat } = await import("../../vendor/directives/repeat.js");

  const cardsEl = document.getElementById("cards");

  function renderList(items) {
    render(
      html`${repeat(items, (i) => i.symbol, (i) => html`<div class="card" data-symbol="${i.symbol}">${i.probability}</div>`)}`,
      cardsEl,
    );
  }

  renderList([{ symbol: "XAUUSD", probability: 0.5 }, { symbol: "US30", probability: 0.6 }]);
  const firstNode = cardsEl.querySelector('[data-symbol="XAUUSD"]');
  assert.ok(firstNode, "expected a rendered card for XAUUSD");

  // Mark the node with UI-only state a real interaction would set (e.g.
  // a flipped class) that must NOT be lost by the next render just
  // because XAUUSD's own data changed.
  firstNode.classList.add("flipped");

  renderList([{ symbol: "XAUUSD", probability: 0.9 }, { symbol: "US30", probability: 0.6 }]);
  const secondNode = cardsEl.querySelector('[data-symbol="XAUUSD"]');

  assert.equal(secondNode, firstNode, "the DOM node for the same key (symbol) must be the SAME node object, not recreated");
  assert.ok(secondNode.classList.contains("flipped"), "state set directly on the DOM node must survive a re-render keyed by the same identity");
  assert.equal(secondNode.textContent.trim(), "0.9", "the changed value must still be patched into the surviving node");
});

test("repeat() removes a card whose key (symbol) is no longer present, without touching siblings", async () => {
  const dom = new JSDOM("<!doctype html><html><body><div id='cards'></div></body></html>");
  global.window = dom.window;
  global.document = dom.window.document;
  global.HTMLElement = dom.window.HTMLElement;
  global.Text = dom.window.Text;
  global.customElements = dom.window.customElements;

  const { html, render } = await import("../../vendor/lit-html.js");
  const { repeat } = await import("../../vendor/directives/repeat.js");
  const cardsEl = document.getElementById("cards");

  function renderList(items) {
    render(html`${repeat(items, (i) => i.symbol, (i) => html`<div data-symbol="${i.symbol}"></div>`)}`, cardsEl);
  }

  renderList([{ symbol: "XAUUSD" }, { symbol: "US30" }]);
  const us30Node = cardsEl.querySelector('[data-symbol="US30"]');

  renderList([{ symbol: "US30" }]); // XAUUSD removed (e.g. untracked)

  assert.equal(cardsEl.querySelector('[data-symbol="XAUUSD"]'), null);
  assert.equal(cardsEl.querySelector('[data-symbol="US30"]'), us30Node, "the surviving card must not be rebuilt just because a sibling was removed");
});
```

If `import("../../vendor/lit-html.js")` fails under jsdom because the vendored build assumes `ShadowRoot`/`customElements` globals not set up above, add whichever additional jsdom globals the actual error message names (e.g. `global.ShadowRoot = dom.window.ShadowRoot;`) — do not change the vendored library itself to work around a missing global.

- [ ] **Step 3: Run the tests**

```bash
npm test
```
Expected: all pass, including both new `dashboard-poll.test.js` cases proving state survives keyed re-rendering.

- [ ] **Step 4: Cut over app.js — remove the old teardown and both restoration hacks**

In `webapp/static/app.js`:
1. Add to the top-of-file imports: `import { refreshDashboard } from "./js/dashboard/dashboard-poll.js";`
2. Delete the entire old `refreshDashboard()` function (currently defined around line 875) — including its `expandedHistoryIds`/`flippedSymbols` capture-before-teardown logic and the `cardsEl.innerHTML = ""` line and the two `.forEach(...)` restoration blocks after it. All of that logic is now handled by `dashboard-poll.js`'s `renderDashboardNow()` + `cardState`.
3. **Do NOT delete `renderCard()`, `finalizeCardFlip()`, `wireCardFlip()`, or `articleProgressionEntryHtml()` in this task**, even though they are now unused — per the spec's own migration plan (`docs/superpowers/specs/2026-09-11-frontend-rendering-refactor-design.md`'s Migration plan, step 4): "removing it here would be an unrelated deletion bundled into the same commit as the rendering swap." They stay in place, dead, until Task 9's dedicated cleanup pass deletes them alongside every other now-orphaned helper in one focused commit.
4. `removeSymbol(ticker)` — currently a standalone function calling the old `refreshDashboard()` after a delete — is superseded by `card-flip.js`'s `onRemoveClick`. Leave the old standalone `removeSymbol` function in place for the same reason as point 3 above, even if nothing calls it after this task — Task 9 deletes it alongside the others.

- [ ] **Step 5: Live-verify — the actual point of this task**

Using the Browser pane: reload the dashboard, confirm every card renders identically (screenshot, compare against Task 5's screenshot). Then, the real test:
1. Flip a card (click the symbol name) to see its back face.
2. Expand its "History ▾" panel.
3. Wait for a real 60-second poll to fire (or, faster: manually call `refreshDashboard()` from the browser console via `javascript_tool` if `refreshDashboard` is reachable, or just wait the 60s).
4. Confirm the card is STILL flipped and the History panel is STILL expanded after the poll — this is the property the whole refactor exists to deliver. Screenshot before and after the poll to compare.
5. Check `read_console_messages` for any new errors.

- [ ] **Step 6: Commit**

```bash
git add webapp/static/js/dashboard/dashboard-poll.js webapp/static/js/dashboard/dashboard-poll.test.js webapp/static/js/staleness.js webapp/static/app.js
git commit -m "refactor: cut Dashboard cards over to keyed lit-html rendering, remove teardown + restoration hacks"
```

---

### Task 7: Calendar tab — grid-view-model.js, grid.js, date-panel.js, calendar-poll.js

**Files:**
- Create: `webapp/static/js/calendar/grid-view-model.js`
- Create: `webapp/static/js/calendar/grid-view-model.test.js`
- Create: `webapp/static/js/calendar/grid.js`
- Create: `webapp/static/js/calendar/date-panel.js`
- Create: `webapp/static/js/calendar/calendar-poll.js`
- Modify: `webapp/static/app.js`

**Interfaces:**
- Consumes: `format.js` (Task 3), `api.js` (Task 5), `html`/`render`/`repeat` (Task 1).
- Produces: `refreshCalendar()` — same exact name `app.js`'s polling loop already calls.

A note on scope, for accuracy: unlike the Dashboard cards, the Calendar grid's cells carry no interactive state of their own today (no flip/expand per cell) — its full `innerHTML` rebuild each poll doesn't currently lose anything, because the date panel is a separate DOM element outside the grid and `selectedCalendarDateStr`/`calendarPanelClosed` already live in plain JS variables, not the DOM. This task still applies the same keyed-rendering treatment for architectural consistency with the Dashboard (per the approved design), and because it removes an unnecessary full-DOM-rebuild every 60 seconds — but there is no existing "restoration hack" bug being fixed here the way there was for cards.

- [ ] **Step 1: Write grid-view-model.js**

```javascript
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
```

- [ ] **Step 2: Write grid-view-model.test.js**

```javascript
// webapp/static/js/calendar/grid-view-model.test.js
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
```

- [ ] **Step 3: Write grid.js**

```javascript
// webapp/static/js/calendar/grid.js
import { html } from "../../vendor/lit-html.js";
import { repeat } from "../../vendor/directives/repeat.js";
import { escapeHtml } from "../format.js";

function cellTemplate(cell, onCellClick) {
  if (!cell) return html`<div class="cal-cell"></div>`;
  const classes = ["cal-cell"];
  if (cell.isToday) classes.push("today");
  if (cell.isNearestUpcoming) classes.push("nearest-upcoming");
  if (cell.hasEstimatedOnly) classes.push("has-estimated-only");
  return html`<div class="${classes.join(" ")}" data-date="${cell.dateStr}" @click=${() => onCellClick(cell.dateStr)}>
    ${cell.day}<br>
    ${cell.dots.map((d) => html`<span class="cal-dot ${d.impactClass}" title="${escapeHtml(d.title)}"></span>`)}
    ${cell.estimatedDots.map((d) => html`<span class="cal-dot cal-dot-estimated" title="${escapeHtml(d.title)}"></span>`)}
  </div>`;
}

export function calendarGridTemplate(gridViewModel, onCellClick) {
  const blanks = Array.from({ length: gridViewModel.leadingBlanks }, () => null);
  const allCells = blanks.concat(gridViewModel.cells);
  return html`${repeat(
    allCells,
    (cell, i) => cell?.dateStr ?? `blank-${i}`,
    (cell) => cellTemplate(cell, onCellClick),
  )}`;
}
```

- [ ] **Step 4: Write date-panel.js**

```javascript
// webapp/static/js/calendar/date-panel.js
//
// The click-to-inspect date panel. State (selectedCalendarDateStr,
// calendarPanelClosed) is owned by calendar-poll.js and passed in —
// this module is a pure template + one fetch-triggering function.

import { html, render } from "../../vendor/lit-html.js";
import { escapeHtml, directionLabel, directionPct, confidenceColorClass } from "../format.js";
import { fetchCalendarDate } from "../api.js";

function callLineTemplate(symbol, call) {
  if (!call) return html`<div class="date-panel-call">${escapeHtml(symbol)}: <span style="color:#888">no call recorded</span></div>`;
  const essenceLine = call.direction != null && call.direction !== "pending"
    ? html`<b>${directionLabel(call.direction)} ${directionPct(call.probability, call.direction)}%</b>`
    : html`<span style="color:#888">no essence score yet</span>`;
  const articleLine = call.article_prediction
    ? html`<div style="font-size:12px;color:#666">📰 ${directionLabel(call.article_prediction.direction)} ${directionPct(call.article_prediction.probability, call.article_prediction.direction)}% (${call.article_prediction.article_count} articles)</div>`
    : html``;
  const printLine = call.print_prediction
    ? (() => {
        const pct = Math.round(call.print_prediction.confidence * 100);
        return html`<div style="font-size:12px">📊 ${escapeHtml(call.print_prediction.direction)} <span class="${confidenceColorClass(pct)}">(${pct}% conf.)</span></div>`;
      })()
    : html``;
  return html`<div class="date-panel-call">${escapeHtml(symbol)}: ${essenceLine}${articleLine}${printLine}</div>`;
}

function eventTemplate(e) {
  if (e.estimated) {
    return html`<div class="date-panel-event">
      <b>${escapeHtml(e.title)}</b> <span class="estimated-badge" title="FRED month-ahead estimate — not yet confirmed by Forex Factory's own feed">ESTIMATED</span><br>
      <span style="font-size:12px;color:#888">Exact time not yet confirmed — Forex Factory hasn't reached this occurrence's week yet.</span>
    </div>`;
  }
  return html`<div class="date-panel-event">
    <b>${escapeHtml(e.title)}</b> (${escapeHtml(e.impact ?? "")})<br>
    <span style="font-size:12px;color:#888">forecast ${escapeHtml(e.forecast ?? "—")}, previous ${escapeHtml(e.previous ?? "—")}, actual ${escapeHtml(e.actual ?? "—")}</span>
    ${Object.entries(e.calls || {}).map(([symbol, call]) => callLineTemplate(symbol, call))}
  </div>`;
}

export async function showDatePanel(dateStr, state) {
  state.selectedCalendarDateStr = dateStr;
  state.calendarPanelClosed = false;
  const panel = document.getElementById("calendar-date-panel");
  const title = document.getElementById("calendar-date-panel-title");
  const body = document.getElementById("calendar-date-panel-body");
  title.textContent = new Date(`${dateStr}T00:00:00`).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
  panel.style.display = "";

  const data = await fetchCalendarDate(dateStr);
  if (!data.events || data.events.length === 0) {
    render(html`<div style="color:#888">No tracked events on this date.</div>`, body);
    return;
  }
  render(html`${data.events.map(eventTemplate)}`, body);
}
```

- [ ] **Step 5: Write calendar-poll.js**

```javascript
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
```

- [ ] **Step 6: Run the tests**

```bash
npm test
```
Expected: all pass, including the new `grid-view-model.test.js` file.

- [ ] **Step 7: Cut over app.js**

1. Add to `app.js`'s imports: `import { refreshCalendar } from "./js/calendar/calendar-poll.js";`
2. Delete ONLY the old `refreshCalendar()` function's body from `app.js` (currently around line 947) — this one is unavoidable: an ES module cannot both `import { refreshCalendar }` and declare `function refreshCalendar() {}` in the same scope (a real `SyntaxError: Identifier 'refreshCalendar' has already been declared`), unlike Task 6's `renderCard()`/etc., which have no import-name collision and can stay. **Do NOT delete `showDatePanel()`, the `selectedCalendarDateStr`/`calendarPanelClosed` module-level state, or the old `calendar-date-panel-close` click listener in this task** — none of these three collide with anything imported here, and per the spec's Migration plan (step 5, "repeat steps 3-4's shape"), dead code with no forced collision stays in place until Task 9's dedicated cleanup pass.

- [ ] **Step 8: Live-verify**

Switch to the Calendar tab in the Browser pane, confirm the grid renders identically (screenshot comparison), click a different cell than the default, confirm the date panel updates, click the panel's close button, wait for a poll, confirm the panel stays closed (not re-opened by the next poll) — this exact behavior already worked before this task via `calendarPanelClosed`; confirming it still works here is the regression check, not a new behavior. Check `read_console_messages` for errors.

- [ ] **Step 9: Commit**

```bash
git add webapp/static/js/calendar webapp/static/app.js
git commit -m "refactor: cut Calendar tab over to keyed lit-html rendering"
```

---

### Task 8: Move the History tab's functions (mechanical, no logic change)

**Files:**
- Create: `webapp/static/js/history/table.js`
- Modify: `webapp/static/app.js`

**Interfaces:**
- Consumes: `format.js` (Task 3), `api.js` (Task 5).
- Produces: `loadHistoryIfNeeded()` — `app.js`'s `tab-history` click listener calls this exact name, unchanged.

Per the spec's Non-goals: the History tab's rendering logic is out of scope for this refactor (it fetches once per page load, filters/sorts client-side, and isn't part of the 60-second poll — it has no teardown problem to fix). This task is a **pure file-location move, zero logic change** — every function keeps its exact current body.

- [ ] **Step 1: Move the History functions verbatim**

Open the current `webapp/static/app.js` and locate these functions (as of the state after Task 7's commit — line numbers will have shifted from the original file, so locate by name, not by the line numbers cited earlier in this plan): `loadHistoryIfNeeded`, `_populateHistoryFilterOptions`, `_historyOutcomeFilterValue`, `_filterAndSortHistoryRows`, `_applyHistoryFilterAndSort`, `_renderHistorySortIndicators`, `renderHistoryStats`, `loadHistoryStats`, `renderHistoryTable`, plus the module-level state they share: `let historyLoaded = false;`, `let allHistoryRows = [];`, `const historySort = { column: "event_time_utc", ascending: false };`.

Cut all of the above, verbatim, into a new file `webapp/static/js/history/table.js`. At the top of that new file, add:
```javascript
import { escapeHtml, directionLabel, directionClass, directionPct, confidenceColorClass } from "../format.js";
import { fetchHistory, fetchHistoryStats } from "../api.js";
```
Replace any direct `fetch("/api/history")` / `fetch(<the history-stats URL>)` call inside the moved `loadHistoryIfNeeded`/`loadHistoryStats` functions with `fetchHistory()`/`fetchHistoryStats()` respectively — this is the one intentional, mechanical adjustment (using the already-built `api.js` wrappers instead of inline `fetch()`), not a logic change (identical URL, identical response handling).

Add `export` to `loadHistoryIfNeeded` (the only function `app.js` needs to call into this module) — every other moved function stays unexported (module-private), matching their current effectively-private usage (nothing outside the History tab's own code calls `_populateHistoryFilterOptions` etc. today).

- [ ] **Step 2: Update app.js**

Add the import: `import { loadHistoryIfNeeded } from "./js/history/table.js";` Remove the old inline definitions of all functions moved in Step 1 from `app.js`.

- [ ] **Step 3: Live-verify**

Switch to the History tab in the Browser pane (first visit triggers `loadHistoryIfNeeded()`), confirm the table renders with the same rows, confirm the aggregate stats panel (`#history-stats`) renders, use a filter dropdown and a sort-by-clicking-a-header action, confirm both still work identically to before. Check `read_console_messages` for errors.

- [ ] **Step 4: Commit**

```bash
git add webapp/static/js/history/table.js webapp/static/app.js
git commit -m "refactor: move History tab functions to js/history/table.js (mechanical, no logic change)"
```

---

### Task 9: Final cleanup + full verification pass

**Files:**
- Modify: `webapp/static/app.js`

**Interfaces:**
- Consumes: nothing new.
- Produces: nothing new — this task only deletes dead code and verifies.

- [ ] **Step 1: Delete dead code**

Per Task 6 Step 4 point 3 and Task 7 Step 7 point 2, the following were deliberately left in `app.js`, dead, until this task: `renderCard()` (and every nested closure inside it — `articlePredictionHtml`, `tier1PredictionHtml`, `printPredictionHtml`, `kalshiReadHtml`, `trendSignalHtml`, `breakdownPanelHtml`, `otherEventsHtml`, `otherTrackedEventsHtml`, and any others still nested there), `finalizeCardFlip()`, `wireCardFlip()`, `removeSymbol()`, `showDatePanel()`, the `selectedCalendarDateStr`/`calendarPanelClosed` module-level state, and the old `calendar-date-panel-close` click listener.

Confirm each is genuinely unused now (via `grep -n "removeSymbol(\|showDatePanel(\|selectedCalendarDateStr\|calendarPanelClosed" webapp/static/app.js` to check for any lingering call site outside the dead function definitions themselves — there should be none, since every real caller was already migrated to the new modules in Tasks 5-7). Delete all of the above from `app.js`. If any grep-turned-up reference surprises you (a real, still-needed call site this plan didn't anticipate), stop and treat it as a real gap in Tasks 5-7 rather than guessing — leave that one function in place and note which task's boundary missed it.

- [ ] **Step 2: Confirm app.js's final shape matches the spec**

Run `wc -l webapp/static/app.js` — expect a file in the low hundreds of lines (DOM refs, the polling loop, one-time static listeners: tab switching, the add-symbol form handler), not the original 1416. Read through the remaining content once and confirm every remaining top-level statement is one of: an `import`, a `const ... = document.getElementById(...)` DOM reference, `showView()`, the `tab-*` click listeners, the `addForm` submit listener, `async function refreshAll()`, and the final `refreshAll(); setInterval(refreshAll, POLL_INTERVAL_MS);` bootstrap. Anything else found here is a task-boundary miss from Tasks 3-8 — move it to the appropriate module now rather than leaving it stranded.

- [ ] **Step 3: Run the complete automated suite**

```bash
npm test
cd .. && python -m pytest -q  # from news_engine/, confirm the unrelated Python suite is untouched
```
Expected: all `node --test` cases pass; Python suite shows the same pass count as before this refactor began (this refactor touches zero Python files, so the count must be identical).

- [ ] **Step 4: Full live verification pass across all three tabs**

Using the Browser pane:
1. **Dashboard:** screenshot, flip a card, expand its History panel, expand its "Why this call" breakdown panel, wait for a real poll, confirm all three states survive. Add a new symbol via the form, confirm a new card appears. Remove a symbol, confirm its card disappears and no sibling card is disturbed.
2. **Calendar:** screenshot, click a non-default cell, confirm the date panel updates, close the panel, wait for a poll, confirm it stays closed, click "Add" for a new tracked symbol from a date-panel call line if that's an available interaction (otherwise skip), reopen a cell.
3. **History:** switch tabs, confirm the table and aggregate stats render, apply a filter, sort by a column, expand a resolved row's drill-down.
4. `read_console_messages` (no errors across the whole pass) and `read_network_requests` (confirm `/api/predictions`, `/api/calendar`, `/api/calendar/monthahead`, `/api/history` all return 200, and that the poll cadence is still 60 seconds — no new request storm introduced by the refactor).

- [ ] **Step 5: Commit**

```bash
git add webapp/static/app.js
git commit -m "chore: final cleanup — delete dead code from app.js post-refactor"
```
