# B9 deploy runbook - honest Stats scoring (ST1 + ST2)

Branch `b9-stats-honest`, applied by the controller. Times are SAST. Every command runs from the live app dir:

```
cd C:\Users\Masoodt\Documents\Claude\Projects\.worktrees\news-engine-live\Claude_news_engine\news_engine
```

## 1. What changes

- No DB changes and no migrations. No Windows or Claude scheduled task changes.
- **Scoring-display change:** Stats grades News by a pre-registered side (`|lean| >= 0.2`, else "no call"; News never says "in line"), and the scoreboard adds directional-only accuracy and an "always in line" baseline. Nothing stored changes: no prediction or `predicted_direction` is written.
- `/api/stats/events` rows gain `news_call`. `/api/stats/scoreboard` gains `methods.*.directional`, `methods.news.no_call` and `in_line_baseline`.
- **Side effect on the Market reaction tab (flagged for owner ruling):** the Market reaction tab engine column falls back to the Stats News verdict when Combined and Tier 1 have none, so it now shows the ST1 News verdict. On 2026-10-28 data (read-only replay of the live DBs) 18 release cells change: 17 former in-line News verdicts clear (6 'right', 11 'wrong': PPI m/m 2026-08-13, Core PPI m/m 2026-08-13 and 2026-09-10, Unemployment Claims x5, Average Hourly Earnings m/m x2, Non-Farm Employment Change x2, Unemployment Rate, and CPI y/y and Core CPI y/y for 2026-09-11 and 2026-10-14), and ISM Manufacturing PMI 2026-09-01 gains a News verdict (an unsized call, 'right'); the leaderboard engine k/n for those titles moves with them. No Market reaction code changes; `tests/test_reaction_service.py` pins the fallback.
- Merge `b9-stats-honest` into `news-engine/batch-predictions-queries` in the live worktree (the controller does this; no push).

## 2. Stop the single engine copy

Stop the single engine copy exactly as `docs/b11-deploy.md` section 2.

## 3. Merge, then start exactly one copy

Merge as in section 1, then start exactly one copy exactly as `docs/b11-deploy.md` section 3.

## 4. Verify

- `GET http://localhost:5001/api/stats/events?event=CPI%20m/m` returns 200 and every row has a `news_call` key. Count the `news_call` values: no News row reads "in line". On 2026-10-28 data expect 2 `no_call` and 0 `higher`/`lower`.
- `GET /api/stats/scoreboard` has top-level `in_line_baseline` and `methods.*.directional`.
- Hard-refresh the Stats tab (Ctrl+F5): the scoreboard shows "Directional only", the News no-call line and the "Always in line (baseline)" row.
- Market reaction tab (gold, all impacts): open CPI y/y and confirm the 2026-09-11 and 2026-10-14 releases show no engine call, then open ISM Manufacturing PMI and confirm 2026-09-01 shows a News engine call reading 'right'. Any other engine-column change beyond the 18 cells in section 1 is unexpected: stop and report it.
- **Record the restart-complete time (UTC and SAST) as the B9 scoring-display change time** in the roadmap status line and the feature inventory row. The 2027-01-15 review uses post-change data only.

## 5. Rollback

`git revert` the merge, then restart as in sections 2 and 3. There is no data to restore.
