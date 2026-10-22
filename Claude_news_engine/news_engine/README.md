# News Engine

Scores each scheduled USD release (CPI, NFP, FOMC and so on) from news sentiment and a Causation-Matrix numeric read (Tier 1), alerts on market-moving shock headlines, and shows the result per tracked symbol on a local dashboard. Tracked symbols are managed from the dashboard itself.

## Run

1. `pip install -r requirements.txt`, plus the extras you need: `requirements-webapp.txt`, `requirements-alerting.txt`, `requirements-contextual.txt`, `requirements-dukascopy.txt`.
2. Copy `.env.example` to `.env` and fill in the keys (`config/settings.py` loads it; RSS-only sources work with no keys).
3. `scripts\run_engine.bat` starts the dashboard (`webapp/app.py`, http://localhost:5001) and the accumulator (`scripts/run_accumulator.py`). Each runs under `_restart_loop.bat` with a single-instance lock. The `NewsEngine_AutoStart` Windows task runs it at logon.

## Tests

```
python -m pytest -q -p no:warnings
npm test
```

## Scheduled jobs

The poller, outcome confirmation, health checks and the research tasks run on schedules outside the dashboard process. The full list is in the "Scheduled jobs" section of `docs/feature-inventory-2026-09-11.md`.

## Databases

| DB | What it holds |
|---|---|
| `webapp/dashboard.db` | Calendar snapshot, event history, macro calendar, tracked symbols |
| `scoring/backtest_log.db` | Predictions, outcomes, Tier 1 rows/late checks/nowcasts, reaction baselines; legacy empty `exogenous_shocks` and frozen `tier1_comparisons` |
| `alerting/shock_alerts.db` | Shock alerts, near-misses, poll cursor, source health, seen URLs |
| `ops/ops_state.db` | Job runs, health notices |

## Dashboard tabs

Dashboard, Calendar, History, Shock Alerts, Stats. Stats has four sub-tabs: Combined, Tier 1, News sentiment, Market reaction.

## Docs

- `docs/roadmap-2026-10-20.md`: the agreed improvement roadmap and batch order.
- `docs/feature-inventory-2026-09-11.md`: what is built, scheduled jobs, deployment history.
- `docs/b*-deploy.md`: per-batch deploy runbooks.
- `docs/archive/`: retired handover and the original README.
