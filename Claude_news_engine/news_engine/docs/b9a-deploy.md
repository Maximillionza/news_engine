# B9a deploy runbook - Stats display fixes

Branch `b9a-stats-display`, applied by the controller. Times are SAST. Every command runs from the live app dir:

```
cd C:\Users\Masoodt\Documents\Claude\Projects\.worktrees\news-engine-live\Claude_news_engine\news_engine
```

## 1. What changes

- No DB changes and no migrations. No Windows or Claude scheduled task changes.
- Display-only: `/api/stats/events` rows gain `agreement` and `tier1_tier`; the Stats tab renders them, shows grey for pending calls, and an honest note when a method has no calls. No scoring, verdict, accuracy or 70/30 change.
- Merge `b9a-stats-display` into `news-engine/batch-predictions-queries` in the live worktree (the controller does this; no push).

## 2. Stop the single engine copy

Stop the single engine copy exactly as `docs/b11-deploy.md` section 2.

## 3. Merge, then start exactly one copy

Merge as in section 1, then start exactly one copy exactly as `docs/b11-deploy.md` section 3.

## 4. Verify

- `GET http://localhost:5001/api/stats/events` returns 200 and each row has `agreement` and `tier1_tier` keys (CPI rows from reconstructed snapshots show `tier1_tier` "formula").
- Hard-refresh the Stats tab (Ctrl+F5): a CPI Tier 1 row shows "formula"; the pre-12-Aug notice reads the new wording; the News sub-tab chart for a title with no news calls shows "No News sentiment calls for this selection".

## 5. Rollback

`git revert` the merge, then restart as in sections 2 and 3. There is no data to restore.
