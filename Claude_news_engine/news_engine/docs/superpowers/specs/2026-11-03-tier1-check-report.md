# Tier 1 Capture and Timing Check (2026-11-03, ~09:30 SAST)

## 1) Bottom line

The Windows-scheduled tiers (formula and market-implied via Kalshi) are reliably on time. Both tasks ran at 07:00 SAST every day in the window, exit 0, with no missed runs [Certain]. Pre-release coverage since 10-21 is 5 of 5 releases, but only 3 of 5 came from the producer the registry names; Fed Funds Rate and FOMC Statement were hand-researched FedWatch rows [Certain]. No displayed row was logged after its release [Certain]. The judgment tier is effectively dark: the Claude task `tier1-cpi-ppi-autoresearch` has produced no usable run since 10-27, an 11-02 session has been stuck about 25 h, and ISM Services PMI (11-04 17:00 SAST) has no call [Certain]. Upcoming 8 days: 1 of 6 covered titles has a row [Certain]. Tier 1 is NOT reliably on time overall; the judgment tier is the failure.

## 2) Problems found

| ID | Severity | What | Evidence | Fix |
|---|---|---|---|---|
| 1 | HIGH | Judgment-tier producer stalled | Runs 10-28 to 11-01 report "succeeded" but did nothing (`request_directory` refused, `cd` resets to shared checkout, `plan` never runs). 11-02 08:13 run still "running", last activity 08:13:52. 11-03 run never started (cause [Likely]: overlap block). Only manual session wrote late checks (10-27). | Kill stuck session. Make the live worktree the task's working directory or pre-grant it; stop runtime `request_directory`. Re-run attended. |
| 2 | HIGH | ISM Services PMI 11-04 17:00 has no row | `tier1_predictions` has none; inside plan window since 10-27. Tomorrow 08:12 run is the last chance. | Fix #1, then run once manually today (cheap: Guessing/neutral expected). |
| 3 | HIGH | Stuck 11-02 session (about 25 h) | Run `local_4586f497`, 74 messages. Needs owner approval; not touched. | Owner stops the session. |
| 4 | MEDIUM | NFP row used stale forecast | Row 35/36 uses 63K "in line"; `event_history` now 65K, which gives "cooler" (tol 1.0, `stats_rules.py:30`). Next refresh 11-05 07:00 (about 8.5 h pre-release). | Forecast-change detection in the Wednesday run, or 72 h daily window Thu/Fri. |
| 5 | MEDIUM | 11-10 CPI family may be missed | `_due_releases` (`capture_nowcast_from_cleveland.py:191-199`) reads only `event_history`; CPI rows exist only in unconfirmed `macro_calendar` (snapshot ends 11-06). Estimated 12:30 UTC probably an hour early after US DST end. Phantom "Prelim GDP q/q" 10-29 in calendar. | Fall back to `macro_calendar` with a time guard, or add an "unconfirmed release in window" notice. |
| 6 | MEDIUM | ISM Manufacturing call is edge-case | 54.3559 vs 54.5 (gap 0.14, tol 0.1) gives "cooler", logged bullish for both XAUUSD and US30. Actual still empty in `event_history` 18 h+ after release. | Resolve the "in line" band ruling. Review US30 direction mapping alongside the sentiment-direction stopgap. |
| 7 | MEDIUM | Health check would not catch the dark tier | `ops/health.py:301-313, 216-247`: red only if a release had no pre-release row; amber only if due within 24 h with no call; late checks never graded. Showed green for 7 dark days. Amber from 11-03 17:00, red after 11-04 17:00. | Amber at about 30 h without a run (task heartbeat); amber when a call-of-record lacks a late check inside 24 h. |
| 8 | MEDIUM | No comparisons since September (needs human check) | `tier1_comparisons`: 10 rows, latest for a 09-16 event. None for 10-28 FFR/FOMC, 10-29 GDP/PCE, 11-02 ISM. Not confirmed whether Stats tab is live-computed. | Check `stats_service.py`. |
| 9 | MEDIUM | FOMC Statement call quality | Rows 21-22: "Likely" confidence on a no-call (SKILL.md line 36 says Guessing); source is a blog, does not start with "CME FedWatch" (line 19). | Tighten prompt on confidence and source format. |
| 10 | LOW | Scheduler robustness | `DisallowStartIfOnBatteries` / `StopIfGoingOnBatteries` True in `register_tier1_tasks.ps1`; no wake; daily and weekly start same minute Mondays, writing one DB (order looks racy). Wake-after-sleep acceptance has no evidence. | Battery flags False; stagger weekly. |
| 11 | LOW | Tier label mismatch | FedWatch-cited FOMC Statement row classified `market_implied` though registry says `judgment`. Kalshi `KXFED` first real read will be the December meeting. | Fix `tier1_row_tier`. |
| 12 | LOW | Coverage gaps if the task stays down | Prelim GDP 11-25, Core Retail Sales, Retail Sales, FOMC Minutes (mid/late Nov). Plan reads only `event_history`. "GDP q/q" entry probably unused. | Resolved by #1 plus macro_calendar fallback. |
| 13 | LOW | Late checks sparse | Only FOMC/FFR got late checks (10-27 manual). GDP and PCE got none on 10-28. 7-day outage on 10-22/23: first judgment rows only 10-26 16:50. | Same as #1 and #7. |

## 3) Upcoming releases (next 8 days)

| Release | Time (SAST) | Tier | Status |
|---|---|---|---|
| ISM Services PMI | 11-04 17:00 | judgment | NO ROW (problems 1, 2) |
| Non-Farm Employment Change | 11-06 15:30 | Kalshi | Row exists (11-02 07:00), stale forecast, refresh pending 11-05 07:00 (problem 4) |
| CPI m/m, Core CPI m/m, CPI y/y, Core CPI y/y | about 11-10 | formula/Kalshi | No rows; not in `event_history` (problem 5) |
| PPI m/m | about 11-13 (outside 8 days) | -- | Mon 11-09 weekly run reaches it only if `event_history` carries it |

## 4) What was not checked

- Whether `stats_service.py` computes comparisons live (problem 8).
- Content accuracy of calls against actual outcomes (ISM Manufacturing actual is empty).
- Behaviour after a PC sleep or on battery; never exercised.
- CPI, PPI and Retail Sales (10-14/15), which predate the window and B3.
- Dashboard display rendering; checked row selection logic and DB only.
- The 11-02 stuck session (not touched; needs owner).
