# Archived one-off scripts

Not imported by production code; kept runnable from the app dir as `python scripts/archive/<name>.py`.

- `market_reaction_phase0.py` — Phase 0 feasibility check for the market-reaction design (2026-10-16); archived because the real job is `scripts/compute_release_reactions.py` and its helpers moved to `data_layer/minute_bars.py` in B10.
- `audit_fa_probes.py` — hand-written headline probes behind the fundamental-analysis audit (2026-10-16); archived as a finished audit, kept so the findings can be re-run.
- `audit_shock_impact.py` — one-off check of whether sent shock alerts coincide with unusual XAUUSD/US30 moves; archived because B10 grading (`alerting/lean_grading.py`) replaces it.
- `migrate_adp_title_rename.py` — one-off rename of the ADP event title across both DBs; archived because the migration has been applied.
- `migrate_country_backfill.py` — one-off backfill of `event_history.country = 'USD'` for seeded/fallback/FRED rows; archived because the migration has been applied.
- `migrate_gdp_title_rename.py` — one-off rename of 'Advance GDP q/q' to 'Prelim GDP q/q' across both DBs; archived because the migration has been applied.
- `stats_phase0_news_input.py` — Stats Phase 0 (B-series): how often each news signal takes a side; archived because the finding fed the Stats tab design.
- `compare_fred_lookahead.py` — read-only comparison of FRED's release lookahead against the persisted calendar snapshot; archived as a finished verification tool.
- `event_study_once.py` — B5 event study runner (2026-10-21), read-only and not scheduled; archived because the study is complete.
- `event_study_groups.py` — B5 event study clusters, implied directions and group tables; archived with its runner.
- `event_study_metrics.py` — B5 event study per-window price measures from OHLC bars; archived with its runner.
- `event_study_checks.py` — B5 event study DXY chain check and Tier 1 dipstick helpers; archived with its runner.
