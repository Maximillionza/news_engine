# B8 re-score report

- Generated: 2026-10-28 00:16 SAST (2026-10-27 22:16 UTC)
- Database: `C:/Users/Masoodt/Documents/Claude/Projects/.worktrees/news-engine-live/Claude_news_engine/news_engine/webapp/dashboard.db` (opened read-only, `mode=ro`)
- Constants: minimum prior surprises 6, history cap 24, standardized sensitivity 0.5
- Old = percent method; new = z = (actual - forecast) / sigma of strictly prior surprises, tanh(0.5 z), percent method below 6 priors.

## Summary

- Scored rows: 102 (z method 21, fallback 81)
- XAUUSD: 0 direction changes; 5 probability shifts >= 0.10
- US30: 0 direction changes; 6 probability shifts >= 0.10

## Direction changes

No direction changes.

## Largest probability shifts (top 20)

| Title | Release | Forecast | Actual | z | Max shift | XAUUSD prob old -> new | US30 prob old -> new |
|---|---|---|---|---|---|---|---|
| CPI y/y | 2026-10-14 14:30 SAST (2026-10-14T12:30Z; stored 2026-10-14T12:30:00+00:00) | 3.6% | 3.7% | 0.885 | 0.301 | 0.378 -> 0.076 | 0.414 -> 0.149 |
| CPI y/y | 2026-07-14 14:30 SAST (2026-07-14T12:30Z; stored 2026-07-14T12:30:00+00:00) | 3.8% | 3.5% | -3.000 | 0.252 | 0.801 -> 0.996 | 0.726 -> 0.978 |
| Core CPI y/y | 2026-10-14 14:30 SAST (2026-10-14T12:30Z; stored 2026-10-14T12:30:00+00:00) | 2.5% | 2.6% | 0.882 | 0.251 | 0.328 -> 0.077 | 0.377 -> 0.149 |
| Non-Farm Employment Change | 2026-07-02 14:30 SAST (2026-07-02T12:30Z; stored 2026-07-02T12:30:00+00:00) | 110K | 57K | -0.546 | 0.223 | 0.995 -> 0.832 | 0.977 -> 0.754 |
| PPI m/m | 2026-08-13 14:30 SAST (2026-08-13T12:30Z; stored 2026-08-13T12:30:00+00:00) | 0.2% | 0.0% | -0.664 | 0.191 | 0.997 -> 0.872 | 0.985 -> 0.793 |
| Core CPI m/m | 2026-10-14 14:30 SAST (2026-10-14T12:30Z; stored 2026-10-14T12:30:00+00:00) | 0.2% | 0.3% | 0.968 | 0.110 | 0.004 -> 0.063 | 0.022 -> 0.131 |
| Non-Farm Employment Change | 2026-09-04 14:30 SAST (2026-09-04T12:30Z; stored 2026-09-04T12:30:00+00:00) | 55K | 162K | 1.098 | 0.094 | 0.002 -> 0.048 | 0.015 -> 0.109 |
| Non-Farm Employment Change | 2026-08-07 14:30 SAST (2026-08-07T12:30Z; stored 2026-08-07T12:30:00+00:00) | 83K | -23K | -1.128 | 0.090 | 0.998 -> 0.955 | 0.985 -> 0.895 |
| Retail Sales m/m | 2026-09-16 14:30 SAST (2026-09-16T12:30Z; stored 2026-09-16T12:30:00+00:00) | 0.8% | 1.2% | 1.118 | 0.084 | 0.004 -> 0.046 | 0.022 -> 0.106 |
| Retail Sales m/m | 2026-10-15 14:30 SAST (2026-10-15T12:30Z; stored 2026-10-15T12:30:00+00:00) | 0.3% | 0.8% | 1.395 | 0.059 | 0.002 -> 0.026 | 0.015 -> 0.074 |
| CPI m/m | 2026-07-14 14:30 SAST (2026-07-14T12:30Z; stored 2026-07-14T12:30:00+00:00) | -0.2% | -0.4% | -2.000 | 0.024 | 0.997 -> 0.990 | 0.985 -> 0.961 |
| PPI m/m | 2026-10-15 14:30 SAST (2026-10-15T12:30Z; stored 2026-10-15T12:30:00+00:00) | 0.6% | 1.3% | 2.071 | 0.022 | 0.002 -> 0.009 | 0.015 -> 0.037 |
| Retail Sales m/m | 2026-08-14 14:30 SAST (2026-08-14T12:30Z; stored 2026-08-14T12:30:00+00:00) | 0.1% | -0.6% | -3.760 | 0.003 | 0.998 -> 0.997 | 0.985 -> 0.982 |

## Sigma by title (latest scored release)

| Title | Latest release | n prior | Sigma | Method |
|---|---|---|---|---|
| ADP Non-Farm Employment Change | 2026-09-02 14:15 SAST (2026-09-02T12:15Z; stored 2026-09-02T12:15:00+00:00) | 3 | - | fallback |
| Average Hourly Earnings m/m | 2026-09-04 14:30 SAST (2026-09-04T12:30Z; stored 2026-09-04T12:30:00+00:00) | 4 | - | fallback |
| CPI m/m | 2026-10-14 14:30 SAST (2026-10-14T12:30Z; stored 2026-10-14T12:30:00+00:00) | 9 | 0.1000 | z |
| CPI y/y | 2026-10-14 14:30 SAST (2026-10-14T12:30Z; stored 2026-10-14T12:30:00+00:00) | 9 | 0.1130 | z |
| Core CPI m/m | 2026-10-14 14:30 SAST (2026-10-14T12:30Z; stored 2026-10-14T12:30:00+00:00) | 6 | 0.1033 | z |
| Core CPI y/y | 2026-10-14 14:30 SAST (2026-10-14T12:30Z; stored 2026-10-14T12:30:00+00:00) | 7 | 0.1134 | z |
| Core PCE Price Index m/m | 2026-09-30 14:30 SAST (2026-09-30T12:30Z; stored 2026-09-30T12:30:00+00:00) | 1 | - | fallback |
| Core PPI m/m | 2026-10-15 14:30 SAST (2026-10-15T12:30Z; stored 2026-10-15T12:30:00+00:00) | 5 | - | fallback |
| ISM Manufacturing PMI | 2026-09-01 16:00 SAST (2026-09-01T14:00Z; stored 2026-09-01T14:00:00+00:00) | 2 | - | fallback |
| ISM Services PMI | 2026-09-03 16:00 SAST (2026-09-03T14:00Z; stored 2026-09-03T14:00:00+00:00) | 0 | - | fallback |
| Import Prices m/m | 2026-10-16 14:30 SAST (2026-10-16T12:30Z; stored 2026-10-16T12:30:00+00:00) | 3 | - | fallback |
| Non-Farm Employment Change | 2026-09-04 14:30 SAST (2026-09-04T12:30Z; stored 2026-09-04T12:30:00+00:00) | 8 | 97488.0945 | z |
| PPI m/m | 2026-10-15 14:30 SAST (2026-10-15T12:30Z; stored 2026-10-15T12:30:00+00:00) | 8 | 0.3381 | z |
| Prelim GDP q/q | 2026-08-26 14:30 SAST (2026-08-26T12:30Z; stored 2026-08-26T12:30:00+00:00) | 0 | - | fallback |
| Prelim UoM Consumer Sentiment | 2026-08-14 16:00 SAST (2026-08-14T14:00Z; stored 2026-08-14T14:00:00+00:00) | 0 | - | fallback |
| Retail Sales m/m | 2026-10-15 14:30 SAST (2026-10-15T12:30Z; stored 2026-10-15T12:30:00+00:00) | 8 | 0.3583 | z |
| Unemployment Claims | 2026-09-03 14:30 SAST (2026-09-03T12:30Z; stored 2026-09-03T12:30:00+00:00) | 5 | - | fallback |
| Unemployment Rate | 2026-09-04 14:30 SAST (2026-09-04T12:30Z; stored 2026-09-04T12:30:00+00:00) | 6 | 0.1000 | z |

## Note

Accumulator (article-based) calls are affected only through precursor contributions and are not re-run here; that needs the article bundles.
