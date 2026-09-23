# Hyperframes Composition Brief: News Fundamental Engine

## Objective
Create a short launch-style brag video for the News Fundamental Engine — a live news/economic-calendar dashboard that predicts XAUUSD/US30 direction ahead of major USD releases.

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080
- Duration: 20 seconds

## Source Material
- Project root: `C:\Users\Masoodt\Documents\Claude\Projects\Claude_news_engine\news_engine`
- Primary files read: `webapp/static/index.html`, `webapp/static/style.css`, `README.md`, live dashboard at `http://localhost:5001` (Dashboard, Calendar, History, Shock Alerts tabs)
- Product name: News Fundamental Engine ("Symbol Impact Dashboard" is the app's own page title)
- Tagline / strongest claim: the History tab's own header stat — "Overall (last 200 events): 20/43 correct (47%), 12 no-call"
- Key UI or visual moment to recreate: the XAUUSD/US30 confidence meter (bear/bull gradient bar with a needle and a "Reversal: was SELL 55% → now BUY 54%" badge), and the History table with red "Wrong" outcome cells
- Copy that must appear verbatim:
  - "Overall (last 200 events): 20/43 correct (47%), 12 no-call"
  - "BUY 53%" / "BUY 54%" style confidence readouts
  - "Reversal: was SELL 55% → now BUY 54%"
  - "Wrong" (History outcome column, styled red)
  - "High — energy" alert header and the raw error string: `{"type":"error"... Your credit balance is too low...}`

## Creative Direction
- Tone preset: deadpan
- Creative direction: institutional trading-terminal demo that never breaks character, even while quoting its own 47% accuracy and a live API error sitting in production
- Interpretation: long, confident holds on real UI; no comedic stingers, no joke SFX; humor comes entirely from pacing and what's left on screen long enough to read; calm system-ui typography; minimal, clean cuts; generous stillness especially around the 47% reveal
- Angle: sell it straight as a professional signal-tracking product — right up until the History tab, held long enough for the viewer to read "20/43 correct (47%)" over a wall of red "Wrong" rows. No joke is told; the dashboard's own honesty is the punchline. Bonus beat: Shock Alerts shows a real LLM API failure message sitting next to a "High" severity alert card, styled with equal seriousness.
- Hook: hard cut into the XAUUSD confidence meter mid-animation, needle settling on "BUY 53%", text slams in: "LIVE MARKET INTELLIGENCE"
- Outro / punchline: flat text card — "News Fundamental Engine — Right about half the time. We show our work." Music hard-stops on this cut, no fade.
- Avoid:
  - Generic SaaS language ("streamline your workflow" etc.)
  - Abstract filler visuals — everything on screen must be real dashboard UI
  - Comedic sound effects (record scratch, rimshot, music sting) on the 47% reveal — it must land in silence
  - Redesigning the dashboard's actual look — reuse its real colors/layout, don't reinvent it

## Visual Identity
- Background: #fafafa
- Text: #222
- Accent (bullish): #2e7d32, bullish-light #a5d6a7
- Accent (bearish): #c62828
- Neutral: #888 / border #ddd
- Display font: system-ui, sans-serif (no display flourish — keep the flat, utilitarian terminal feel)
- Body font: system-ui, sans-serif
- Visual references from the project: the confidence meter gradient bar + needle marker; the calendar grid with colored impact dots; the History table's red/green outcome column; the Shock Alerts card list styling (left border color-coded by severity)

## Storyboard
Use the storyboard in `brag-output/brag-plan.md` as the creative contract.

Scene summary:
1. Hook: the meter — 3s — XAUUSD confidence meter fills frame, needle settles on "BUY 53%", "LIVE MARKET INTELLIGENCE" slams in
2. Dashboard reveal — 4s — US30 and XAUUSD cards arrive one after the other, "Reversal: was SELL 55% → now BUY 54%" badge visible
3. Calendar heatmap — 3s — calendar grid populates with impact dots left-to-right, top-to-bottom
4. The scorecard — 6s — hard cut to History; header stat holds alone 2s, then 4-5 table rows stamp in one by one landing on red "Wrong"
5. The error hiding in plain sight — 2s — Shock Alerts: "High — energy" oil alert card directly above the raw API error card, identical styling, single static hold
6. Outro / punchline — 2s — flat text card, music hard-stops, cut to black

## Audio
- Audio role: sparse professional accents, deliberately restrained
- Audio arc: a single low, near-static synth bed runs almost unchanged under the whole video and cuts to silence (no fade) exactly on the outro card
- Music: choose a low-tension, minimal/ambient bed from Hyperframes' available library — nothing that builds or swells
- Music treatment: starts low under scene 1, flat throughout, hard-stop (no fade-out) on the cut into scene 6
- Music cue guidance: no bundled preset selected; detect cues at composition time if useful, but this video intentionally avoids beat-locking the big reveal — the 47% stat should land in silence, not on a music hit. If a strong cue naturally falls near the scene 4 hard-cut or the scene 6 outro cut, alignment there is fine; do not force one elsewhere.
- Audio-reactive treatment: none
- Audio-coupled moments:
  - Scene 1 — needle settling into "BUY 53%" — dry tick sound synced to the stop
  - Scene 2 — each symbol card arriving — flat, quiet card-arrival tick, not a triumphant chime
  - Scene 4 — each History row stamping in — flat "stamp" sound per row, no ascending/rewarding tone; the header stat itself (the 47%) gets no sound at all
- SFX selection guidance: choose dry, low, non-triumphant UI sounds (ticks, flat stamps) — avoid anything that sounds celebratory or comedic; err toward silence over adding a cue when unsure
- SFX analysis guidance: use `skills/brag/assets/sfx/sfx-analysis.md` if present; prefer low high-frequency-risk sounds since several cues repeat (card arrivals, row stamps)
- Exact SFX choice: Hyperframes should choose filenames, timestamps, density, and volume based on the implemented animation
- Audio files: copy the chosen music and any Hyperframes-selected SFX into `brag-output/composition/assets/`

## Hyperframes Instructions
Load the composition-building Hyperframes domain skills — `hyperframes-core` (composition contract + `data-*` timing), `hyperframes-animation` (motion), `hyperframes-creative` (design spec, beats, audio-reactive), `hyperframes-keyframes` (seek-safe keyframes), and `hyperframes-cli` (lint/check/render). /brag is its own workflow: do not enter the `hyperframes` entry-point intent interview and do not route into its generic promo / launch-video workflow. Prefer native Hyperframes conventions over anything in `/brag`.

Requirements:
- Show at least one real UI, copy, or visual element from the source project (the confidence meter and the History table are non-negotiable; both must appear).
- Keep all text readable in the final render — the "20/43 correct (47%)" line especially needs a full, uninterrupted hold.
- Keep the video within 15-25 seconds (target 20s).
- Include the planned music/SFX layer — audio was not disabled by the user, but keep it sparse per the deadpan tone.
- Treat `/brag` audio notes as guidance, not a fixed cue sheet. Choose SFX after the visual animation exists.
- Treat music cue metadata as optional timing hints. Do not force the 47% reveal onto a music hit — it should land in stillness/silence per the creative direction.
- Use SFX to support motion: dry ticks for the meter needle, flat stamps for table rows arriving, restraint everywhere else.
- Honor the planned hard-stop (no fade) on the music at the outro cut.
- Use local assets for audio and any required runtime/media dependencies when possible.
- Run `hyperframes check` before render — it is brag's single gate.
