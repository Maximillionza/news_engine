# Frontend Rendering Refactor — Design Spec

**Date:** 2026-09-11
**Status:** Approved (brainstorming session, same day)

## Problem

`webapp/static/app.js` (1416 lines) rebuilds the Dashboard tab's cards and the
Calendar tab's grid from scratch on every 60-second poll
(`cardsEl.innerHTML = ""` / `calendarGridEl.innerHTML = cells`, followed by a
full re-append). Because the DOM is destroyed and recreated wholesale, any
UI-only state that lived on those DOM nodes — a flipped card, an expanded
History panel, the Calendar's selected-date panel — is destroyed too, and gets
patched back with capture-before-teardown / restore-after hacks
(`expandedHistoryIds`, `flippedSymbols` in `refreshDashboard()`;
`selectedCalendarDateStr`/`calendarPanelClosed` sticky variables for the
Calendar panel). These hacks are themselves evidence the underlying rendering
strategy is wrong, not a stable design.

Separately, `renderCard()` is ~520 lines with roughly 20 nested closures
handling every sub-signal (article prediction, Tier 1, Tier 1 conflict, Tier 1
confidence downgrade, print call, Kalshi read, trend signal, other-events,
other-tracked-events). This has made every new dashboard signal this project
has shipped (Batches 4, 9, 10, and the essence/article labeling fix) an
addition to one already-large function, with no enforced boundary between
"decide what to show" and "render it."

This refactor was explicitly recommended twice before Batch 6 (Tier 2/3
exogenous context) and deferred twice, specifically because no JS test
coverage exists in this codebase to verify a rewrite against. This spec
resolves that by making test coverage part of the design, not an
afterthought.

## Goals

1. Replace full-DOM-teardown rendering (Dashboard cards, Calendar grid) with
   keyed rendering that only touches the DOM nodes whose underlying data
   actually changed, eliminating the restoration hacks as a structural
   consequence, not a patch.
2. Break `renderCard()` (and the Calendar grid's equivalent) into named,
   independently readable/testable units with clear responsibilities.
3. Introduce real automated test coverage — the actual point, given this was
   deferred twice for lacking it.

## Non-goals

- Rewriting `webapp/scoring_service.py`, `predictions_service.py`, or any
  backend/API surface. This is a frontend-only rendering refactor; every
  field the API returns today is consumed identically.
- Touching the History tab's rendering. It fetches once per page load
  (`historyLoaded` guard) and re-renders only on an explicit user filter/sort
  action, not on the 60-second poll — it doesn't have the teardown problem
  this refactor targets. Left as-is.
- Any new dashboard feature, signal, or visual change. Pure refactor —
  output HTML must be behaviorally identical to today's, verified live.
- A build step / bundler. Browsers load ES modules natively; no bundling is
  introduced for the shipped frontend.

## Architecture

### Library choice: lit-html, vendored

A single-file UMD/ESM build of `lit-html`, downloaded once and served from
`webapp/static/vendor/lit-html.js` — no CDN dependency at runtime, no build
step. `lit-html` was chosen over hand-rolling keyed diffing (more code to
maintain, this codebase's existing zero-JS-dependency norm notwithstanding)
and over heavier options (`petite-vue`'s directive-based HTML, `preact`+`htm`'s
full virtual-DOM component model) because it does exactly one thing this
project needs — tagged-template HTML rendering plus a `repeat()` directive for
efficient keyed list diffing — with the smallest conceptual jump from the
current imperative, function-per-template-fragment style.

### Module structure

Browsers load ES modules directly (`<script type="module">` in
`webapp/static/index.html`, replacing the current plain `<script src=...>`) —
no bundler needed at this project's scale.

```
webapp/static/
  app.js                       — entrypoint: DOM refs, polling loop, one-time
                                  static listeners (remove-symbol, add-symbol
                                  form, calendar panel close button)
  js/
    api.js                     — fetch wrappers: fetchPredictions(),
                                  fetchCalendar(), fetchCalendarDate(dateStr),
                                  fetchHistory(), fetchArticleHistory(symbol,
                                  eventTitle). No DOM, no rendering.
    format.js                  — pure functions, zero DOM: escapeHtml,
                                  directionLabel, directionClass,
                                  directionPct, confidenceColorClass,
                                  formatEventDateTime, toIsoDateLocal,
                                  gaugeSvg, bullBearScaleSvg,
                                  buildDiffStripHtml, diffPieSvg,
                                  dayStripHtml, tier1DirectionLabel.
                                  Mechanical move out of app.js, zero
                                  behavior change.
    dashboard/
      card-view-model.js       — pure functions: given one prediction event
                                  dict (+ prior/current UI state), return a
                                  plain object of everything the template
                                  needs already decided (direction, pct,
                                  dirClass, whether to show each badge, the
                                  downgrade/conflict text, etc.). This is
                                  where the decision logic that used to be
                                  tangled inside renderCard()'s closures now
                                  lives — fully unit-testable, no DOM.
      card.js                  — cardTemplate(viewModel) -> lit-html
                                  TemplateResult, plus one small named
                                  template function per sub-section
                                  (articlePredictionTemplate,
                                  tier1PredictionTemplate,
                                  tier1SentimentConflictTemplate,
                                  tier1ConfidenceDowngradeTemplate,
                                  printPredictionTemplate, kalshiReadTemplate,
                                  trendSignalTemplate, otherEventsTemplate,
                                  otherTrackedEventsTemplate) — thin,
                                  low-logic, mostly interpolating
                                  already-decided values from the view model.
      card-flip.js              — onFlipClick(symbol, cardState),
                                  onHistoryToggle(symbol, cardState):
                                  mutate cardState (lazy-fetching article
                                  history into it on first flip), then
                                  trigger a re-render.
      dashboard-poll.js         — refreshDashboard(): fetch via api.js,
                                  handle poll-error/staleness notices
                                  (logic unchanged from today), call the one
                                  render function.
    calendar/
      grid-view-model.js        — same shape as card-view-model.js, for one
                                  calendar cell.
      grid.js                   — cell template + keyed repeat() list.
      date-panel.js              — showDatePanel() and its template,
                                  converted from hand-built HTML strings to
                                  a lit-html template driven by
                                  (selectedCalendarDateStr,
                                  calendarPanelClosed) state.
      calendar-poll.js          — refreshCalendar(): fetch, error/staleness
                                  handling (unchanged), render.
  vendor/
    lit-html.js                — vendored library, single file.
```

The History tab's existing functions (`loadHistoryIfNeeded`,
`_populateHistoryFilterOptions`, `_historyOutcomeFilterValue`,
`_filterAndSortHistoryRows`, `_applyHistoryFilterAndSort`,
`_renderHistorySortIndicators`, `renderHistoryStats`, `loadHistoryStats`,
`renderHistoryTable`, `articleProgressionEntryHtml`) move unchanged into
`webapp/static/js/history/table.js` for consistency with the new file
layout, but their internals are untouched — out of scope per the Non-goals
section above.

## Data flow & state model

**Core principle: one render function per tab, called from two triggers
(the poll timer and any user interaction), fed by two state sources (the
last-fetched server data, and a UI-state map).** There is no separate
"poll rendering path" and "interaction rendering path" with different logic
— both call the same render function.

```js
// dashboard/dashboard-poll.js
const cardState = new Map();  // symbol -> { flipped, historyExpanded, articleHistory }
let latestPredictionsData = null;

function renderDashboardNow() {
  render(
    html`${repeat(
      latestPredictionsData?.predictions ?? [],
      p => p.symbol,
      p => cardTemplate(buildCardViewModel(p, cardState.get(p.symbol) ?? {}))
    )}`,
    cardsEl
  );
}

async function refreshDashboard() {
  // ... fetch, error/staleness handling, unchanged ...
  latestPredictionsData = data;
  renderDashboardNow();
}
```

`repeat()` diffs by `p.symbol`. A card whose symbol persists across polls
keeps its DOM subtree — lit-html patches only the interpolated values that
changed (a new probability%, a new article count), never rebuilding the
card wholesale. A symbol no longer tracked has its DOM removed; a newly
added symbol gets fresh DOM. UI state (flip, expanded history, lazy-loaded
article progression) lives in `cardState`, not in DOM inspection — an
interaction handler mutates `cardState` and calls `renderDashboardNow()`
again; the template reads state to decide which face/panel shows. State
was never lost across a poll because it was never stored in the DOM to
begin with — this replaces the restoration hacks structurally, not by
patching around teardown.

The Calendar grid and its date panel follow the identical shape, keyed by
ISO date string, with `selectedCalendarDateStr`/`calendarPanelClosed`
folded into the same explicit state pattern (they are already JS state
today, not a DOM hack — this is a consistency move, not a bug fix).

## Testing strategy

Three tiers, matched to what's actually achievable without over-engineering:

1. **Pure view-model functions (`card-view-model.js`, `grid-view-model.js`,
   `format.js`) — full unit test coverage, plain `node --test`, zero DOM.**
   This is where the actual decision logic lives (which direction class
   applies, is this pending/resolved, does this event get a Tier1 badge,
   what's the downgrade text) — the same logic that today is untestable
   because it's tangled inside `renderCard()`'s string-template closures.
   This tier gets the real coverage.
2. **Template smoke tests (`card.js`, `grid.js`) — plain `node --test`, no
   DOM.** `lit-html`'s `html` tagged template constructs a `TemplateResult`
   object without touching the DOM (DOM is only touched by `render()`).
   Tests assert `cardTemplate(viewModel).values` contains the expected
   computed strings/values — catches "wrong field passed to the template"
   wiring mistakes without needing jsdom.
3. **DOM/diffing tests (`dashboard-poll.js`, `calendar-poll.js`) — `node
   --test` + `jsdom`.** Verifies the property this whole refactor exists to
   guarantee: that `repeat()`'s keyed diffing genuinely preserves a card's
   DOM node (and therefore anything `cardState`-driven rendered onto it)
   across two successive `render()` calls with the same key but different
   data — i.e. state really does survive a simulated poll.

**Test infrastructure:** `package.json` at the `news_engine/` project root
(this repo's first) — `"type": "module"`, `devDependencies: { jsdom }`
only. No Jest/Mocha/bundler; Node 18+'s built-in `node --test` and
`node:assert` are sufficient. Tests colocated as `*.test.js` next to the
module they test (e.g. `webapp/static/js/dashboard/card-view-model.test.js`),
run via `node --test webapp/static/js`.

**What stays manual:** actual visual rendering, and real click/flip/expand
interaction in a real browser — verified live in the Browser pane per file
change, same discipline this project has used for every JS change this
session. The surface that requires manual verification shrinks
substantially: it now only needs to confirm painting and interaction feel
correct, not that the underlying decision logic is right (that's covered by
tier 1).

## Migration plan

This is a live tool traded off of daily — no step may leave it in a broken
intermediate state.

1. Vendor `lit-html.js`; flip `index.html` to `<script type="module">`;
   change nothing else. Confirms module loading works before any logic
   moves. Live-verify: dashboard and calendar still render identically.
2. Extract `format.js`'s pure functions verbatim (mechanical, zero behavior
   change). Add their unit tests.
3. Build `card-view-model.js` + `card.js` alongside the OLD `renderCard()`
   — not wired in yet. Unit-test the view-model functions and the template
   smoke tests.
4. Swap `dashboard-poll.js` to the new keyed `repeat()` render; remove
   `refreshDashboard()`'s old `innerHTML=""` teardown and both restoration
   hacks (`expandedHistoryIds`, `flippedSymbols`) in the same step — they
   become dead code the instant keyed rendering lands, and leaving them in
   would be actively confusing, not a safety net. The old `renderCard()`
   function itself is left in place, unused, until step 6's cleanup —
   removing it here would be an unrelated deletion bundled into the same
   commit as the rendering swap. Add the jsdom state-survives-a-poll test.
   Live-verify: flip a card, expand a History panel, wait for a real poll
   cycle, confirm neither resets.
5. Repeat steps 3-4's shape for the Calendar grid + date panel
   (`grid-view-model.js`, `grid.js`, `date-panel.js`, `calendar-poll.js`),
   removing the `selectedCalendarDateStr`/`calendarPanelClosed` imperative
   HTML-string rendering in `showDatePanel()` once the lit-html version is
   wired in.
6. Move the History tab's unchanged functions into `js/history/table.js`.
   Delete now-dead code from the old `app.js`. Confirm final file structure
   matches this spec.

Each step is independently verifiable (unit tests + a live browser check)
before the next begins.

## Error handling

Unchanged. `refreshDashboard()`/`refreshCalendar()`'s existing fetch
try/catch, poll-error notices (`predictionsPollErrorEl`/
`calendarPollErrorEl`), and stale-data handling (`data.error` →
`predictionsStaleNoticeEl`/`calendarStaleNoticeEl`) carry over into the new
modules with identical behavior — this refactor targets rendering
structure, not the fetch/error layer, which already went through its own
hardening pass (Batch 5).

## Global constraints

- Output HTML/behavior must be identical to today's for every existing
  signal (article prediction, Tier 1, Tier 1 conflict, Tier 1 confidence
  downgrade, print call, Kalshi read, trend signal, other-events,
  other-tracked-events, essence/article labeling) — this is a refactor, not
  a feature change. Any visual difference found during migration is a bug
  in the refactor, not a deliberate change, unless explicitly called out
  and approved.
- No CDN dependency introduced at runtime — `lit-html` is vendored as a
  local static file.
- No build step / bundler for the shipped frontend.
- `package.json`/`jsdom` is test-only tooling — never shipped to
  `webapp/static/` as a runtime dependency.
- The History tab's rendering logic is out of scope (see Non-goals) — only
  its file location moves.
