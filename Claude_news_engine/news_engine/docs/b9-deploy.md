# B9 deploy runbook - honest Stats scoring (ST1 + ST2)

Branch `b9-stats-honest`, applied by the controller. Times are SAST. Every command runs from the live app dir:

```
cd C:\Users\Masoodt\Documents\Claude\Projects\.worktrees\news-engine-live\Claude_news_engine\news_engine
```

## 1. What changes

- No DB changes and no migrations. No Windows or Claude scheduled task changes.
- **Scoring-display change:** Stats grades News by a pre-registered side (`|lean| >= 0.2`, else "no call"; News never says "in line"), and the scoreboard adds directional-only accuracy and an "always in line" baseline. Nothing stored changes: no prediction or `predicted_direction` is written.
- `/api/stats/events` rows gain `news_call`. `/api/stats/scoreboard` gains `methods.*.directional`, `methods.news.no_call` and `in_line_baseline`.
- Merge `b9-stats-honest` into `news-engine/batch-predictions-queries` in the live worktree (the controller does this; no push).

## 2. Stop the single engine copy

Stop the single engine copy exactly as `docs/b11-deploy.md` section 2.

## 3. Merge, then start exactly one copy

Merge as in section 1, then start exactly one copy exactly as `docs/b11-deploy.md` section 3.

## 4. Verify

- `GET http://localhost:5001/api/stats/events?event=CPI%20m/m` returns 200 and every row has a `news_call` key. Count the `news_call` values: no News row reads "in line". On 2026-10-28 data expect 2 `no_call` and 0 `higher`/`lower`.
- `GET /api/stats/scoreboard` has top-level `in_line_baseline` and `methods.*.directional`.
- Hard-refresh the Stats tab (Ctrl+F5): the scoreboard shows "Directional only", the News no-call line and the "Always in line (baseline)" row.
- **Record the restart-complete time (UTC and SAST) as the B9 scoring-display change time** in the roadmap status line and the feature inventory row. The 2027-01-15 review uses post-change data only.

## 5. Rollback

`git revert` the merge, then restart as in sections 2 and 3. There is no data to restore.
