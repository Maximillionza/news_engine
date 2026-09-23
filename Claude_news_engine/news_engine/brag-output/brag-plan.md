# Brag Plan: News Fundamental Engine

## What is this app?
A live dashboard that reads news/economic-calendar data and predicts which way gold (XAUUSD) and US30 will move ahead of major USD releases — and then, in its own History tab, honestly tracks how often it's wrong.

## The angle
Play it completely straight, like an institutional trading-desk product demo — the confident BUY/SELL meters, the calendar heatmap, the shock-alert feed — right up until the History tab, which the video holds on just long enough for the viewer to read "20/43 correct (47%)" and a wall of red "Wrong" outcomes. No joke is told. No wink to camera. The dashboard's own honesty is the punchline. Bonus beat: the Shock Alerts tab surfaces a raw LLM API error ("credit balance is too low") sitting in production right next to a "High" severity oil-shock alert — the system reporting its own failure with the same straight face it reports geopolitical risk.

## Hook (first 2-3 seconds)
Hard cut to the dashboard's BUY/SELL confidence meter on XAUUSD mid-animation, ticking to "BUY 53%" with the little bear/bull triangle sliding. Text slams in over it: "LIVE MARKET INTELLIGENCE." Confident, trading-terminal energy.

## Key moments (the middle)
- The two symbol cards (US30, XAUUSD) with their BUY/BEAR/BULL gradient meters and "Reversal: was SELL 55% → now BUY 54%" badge — sell it as sophisticated signal-tracking.
- The Calendar heatmap filling in with red/orange/grey impact dots across the month grid — "every high-impact print, mapped."
- Hard cut to History tab. Header stat "Overall (last 200 events): 20/43 correct (47%), 12 no-call" — hold long enough to actually read it, then the table rows below stamp in with red "Wrong" one after another.
- Quick beat on Shock Alerts: the "High — energy" oil alert card sits directly above a card whose body is a raw `{"type":"error"... credit balance is too low}` string, both styled identically, both timestamped, both looking equally official.

## Outro / punchline
Text card, dead simple: "News Fundamental Engine — Right about half the time. We show our work." Logo/wordmark hold, no music swell, just a flat cut to black.

## User flow worth showing
Dashboard tab (symbol cards + confidence meters) → Calendar tab (heatmap of upcoming events) → History tab (the scorecard exposing the 47% hit rate) → Shock Alerts tab (the error message hiding in plain sight). This is the real flow: check today's calls, check the calendar, check the track record, check the news feed — and the app never flinches at any of it.

## Tone
- Preset: deadpan
- Creative direction: institutional trading-terminal demo that never breaks character, even while quoting its own 47% accuracy and a live API error
- Interpretation: long, confident holds on real UI; zero comedic music stingers or joke sound effects; the humor comes entirely from pacing and what's left on screen long enough to read. Calm typography, minimal cuts, generous silence.

## Format: landscape — 1920x1080
## Duration: 20s

## Visual identity (from the project)
- Background: #fafafa
- Accent (bullish): #2e7d32 / bullish-light #a5d6a7
- Accent (bearish): #c62828
- Neutral: #888
- Border: #ddd
- Text: #222
- Display/body font: system-ui, sans-serif (clean terminal-utility feel — no display font flourish, matches the deadpan tone)
- Strongest visual element: the BUY/SELL gradient confidence meter with its bear/bull triangle marker, and the History table's red "Wrong" column

## Share copy (draft)
Built a news engine that predicts gold moves ahead of Fed prints. It's right 47% of the time and shows the receipts.

## Audio direction
- Role: sparse professional accents, deliberately restrained
- Music: low, dry, minimal-tension bed (something like a single sustained synth pad, near-static) — never builds to a swell
- Music treatment: starts at low volume under the hook, stays flat throughout, hard-stops (no fade) on the cut to the outro card — the abruptness reinforces the deadpan
- Music cue guidance: to be detected at composition time (no bundled preset chosen yet); one soft accent cue at the hard cut into the History tab, one at the outro card; no beat-grid reveals needed since sequential elements (table rows, calendar dots) hold long enough to read rather than snapping to a beat
- Audio-reactive treatment: none
- SFX posture: sparse; one dry UI-tick sound on the confidence meter's needle settling, one flat "stamp" sound per History row landing, no whoosh/swoosh transitions
- Audio-coupled moments: confidence meter needle settling into place (tick), History table rows stamping in one by one (flat stamp, not a triumphant ding)
- Restraint rule: no comedic timing sounds (no record scratch, no rimshot, no music sting on the 47% reveal) — the number must land in silence

## Storyboard

### Scene 1 — Hook: the meter — 3s
XAUUSD confidence meter fills the frame, needle animates to settle at "BUY 53%" on the bear/bull gradient bar. Text slams in: "LIVE MARKET INTELLIGENCE."
Sequential/interaction: yes — needle ticks and settles once, text slams in after settle.
Audio intent: confident, clinical open.
Audio-coupled idea: dry tick sound as the needle settles, synced to its stop.
Music: low dry pad, just starting.
Transition mood: hard cut → Scene 2.

### Scene 2 — Dashboard reveal — 4s
Both symbol cards (US30 + XAUUSD) shown side by side, "Reversal: was SELL 55% → now BUY 54%" badge visible on one card. Small label: "Two markets. Every major print."
Sequential/interaction: yes — the two cards arrive one after the other (US30 first, then XAUUSD).
Audio intent: procedural, matter-of-fact.
Audio-coupled idea: flat card-arrival tick per card.
Music: steady low bed, no build.
Transition mood: clean crossfade → Scene 3.

### Scene 3 — Calendar heatmap — 3s
Calendar grid fills in, red/orange/grey impact dots populating date cells left to right, top to bottom. Label: "Every high-impact release, mapped."
Sequential/interaction: yes — dots populate in a steady sweep, not a flourish.
Audio intent: quiet, procedural.
Audio-coupled idea: none — no ticking per dot, keep this scene the calmest beat.
Music: unchanged low bed.
Transition mood: hard cut → Scene 4.

### Scene 4 — The scorecard — 6s
Hard cut to History tab. Header stat "Overall (last 200 events): 20/43 correct (47%), 12 no-call" appears and holds — full 2s of nothing else happening so it can be read. Then table rows stamp in one by one below it, each landing on a red "Wrong."
Sequential/interaction: yes — header holds alone first; then 4-5 table rows stamp in one by one, each with its red "Wrong" outcome.
Audio intent: the tension beat — music does NOT change, which is the point. Total restraint.
Audio-coupled idea: one flat stamp sound per row landing, no music sting on the 47% itself.
Music: unchanged low bed, still flat.
Transition mood: dramatic (via stillness, not motion) → Scene 5.

### Scene 5 — The error hiding in plain sight — 2s
Shock Alerts tab: the "High — energy" oil-shock card sits directly above the raw JSON error card ("credit balance is too low... falling back to rule tier"), both in identical styling.
Sequential/interaction: none — a single static hold, let the eye find the error itself.
Audio intent: deadpan silence.
Audio-coupled idea: none.
Music: unchanged low bed.
Transition mood: hard cut → Scene 6.

### Scene 6 — Outro / punchline — 2s
Flat text card: "News Fundamental Engine — Right about half the time. We show our work." Music hard-stops with the cut in (no fade).
Sequential/interaction: none.
Audio intent: flat, final.
Audio-coupled idea: none.
Music: cuts to silence exactly on this scene's entrance.
Transition mood: hard cut → end (black).

**Music mood for this video:** deadpan
**Audio summary:** A single low, static synth bed runs almost unchanged under the entire video and cuts to silence — cold, not building — at the punchline; the only rhythmic texture comes from a handful of dry UI ticks/stamps synced to on-screen elements settling into place, never from comedic stings.
