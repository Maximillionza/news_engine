# B6 contamination report (live numbers, read-only)

Generated 2026-10-22 03:22 SAST by `scripts/b6_contamination_report.py` against the live `scoring/backtest_log.db`, opened with `mode=ro` (nothing written; the live checkout was not modified). Window: every live prediction that stores article evidence, 2026-08-17 onward (774 rows).

## In plain English

The recorded FOMC and CPI calls were being voted on by articles that should never have been there. Of the 110 FOMC-family calls that stored evidence, 18 had a foreign central bank (ECB, RBI, Philippine or Chinese central bank and similar) among their three heaviest articles, and 88 had at least one article that the new rules would drop (mostly "no Fed term", see the caveat below). Of the 136 CPI-family calls, 50 carried a foreign-central-bank headline and 128 had at least one article the new rules would drop (192 off-subject stories, for example an AstraZeneca drug trial or a Gambia protest).

The more telling number is the calls whose whole top-3 evidence goes: 44 FOMC-family calls and 58 CPI-family calls. After the fix those calls rest on whatever real evidence remains, so many will become thin-sample calls (low article count, lower confidence) instead of confident calls built on irrelevant headlines. Looking only at the latest call per event and instrument (the one actually in force): 12 of 16 FOMC and 16 of 16 CPI were touched, and 6 FOMC and 8 CPI would have lost all top evidence.

Outside the two families the damage is small, as expected (PPI 20, jobs 14, GDP 5, other 5 stored articles with a foreign-CB title); those get only the foreign-CB rule.

## Family table

| Family | Rows | Rows touched | Rows losing all evidence | Contributions | Unique | Removed (unique) | Removed with a real vote | Same-URL pairs | Removed by reason |
|---|---|---|---|---|---|---|---|---|---|
| cpi | 136 | 128 | 58 | 376 | 144 | 115 | 192 | 0 | foreign_cb 68, off_subject 192 |
| fomc | 110 | 88 | 44 | 292 | 127 | 90 | 105 | 0 | foreign_cb 22, no_fed_coterm 161 |
| ppi | 34 | 20 | 4 | 74 | 26 | 2 | 20 | 0 | foreign_cb 20 |
| jobs | 357 | 14 | 0 | 877 | 299 | 9 | 14 | 0 | foreign_cb 14 |
| gdp | 48 | 5 | 0 | 144 | 58 | 1 | 5 | 0 | foreign_cb 5 |
| other | 64 | 5 | 0 | 180 | 77 | 1 | 5 | 0 | foreign_cb 5 |
| ism | 3 | 0 | 0 | 9 | 6 | 0 | 0 | 0 | none |
| retail_sales | 22 | 0 | 0 | 40 | 18 | 0 | 0 | 0 | none |
| **total** | 774 | 260 | 106 | 1992 | 755 | 218 | 341 | 0 | foreign_cb 134, no_fed_coterm 161, off_subject 192 |

"Removed with a real vote" counts stored entries with `abs(usd_sentiment) >= 0.05`. Foreign-CB only (the unambiguous part): FOMC 18 rows over 5 event occurrences (2 rows lose all evidence to foreign CBs alone); CPI 50 rows over 4 occurrences. Every FOMC and CPI event occurrence in the window (8 each) had at least one affected row once `no_fed_coterm` and `off_subject` are included.

## Examples

- foreign_cb (FOMC, jobs, GDP, other): "Interest rates must rise further on inflation risks, ECB's Schnabel tells Bloomberg - Reuters"; "China's slower loan growth is the new normal, central bank governor says - reuters.com"; "Markets bet on RBI rate hike as inflation pressure builds - Reuters"; "'Godzilla El Nino' is wreaking havoc with Philippine central bank's inflation forecasts" (also in CPI and PPI); "Dollar languishes as inflation awaited; Euro edges up on Lagarde warning" (CPI).
- off_subject (CPI): "AstraZeneca's COPD drug scores two late-stage trial wins ..."; "Trump told Putin he wants swift end to Ukraine war ..."; "Air traffic control issue disrupts departing flights at major UK airports"; "Gambia protesters burn tyres to denounce power cuts"; "Chevron to double oil rigs in Venezuela ...".
- no_fed_coterm (FOMC): "Wall Street indexes slip as oil prices rise, retail results awaited"; "Apple to change app data consent rules, German regulator says"; "Nvidia to provide up to $105 billion guarantee for OpenAI's Ohio data center"; "Dick's Sporting Goods stock falls 20% ..."; "Canada announces retaliatory tariffs on $20 billion worth of US goods ...".

## Caveats

- **Top 3 only.** `predictions.top_contributions_json` keeps the three heaviest articles, so every count undercounts. The full evidence table (`prediction_article_contributions`) exists only from the B6 deploy on.
- **Title only.** The summary is not stored. The live rule reads title plus summary for the Fed co-term, so a story whose summary names the Fed would survive live but is counted as removed here: `no_fed_coterm` (161) is an upper bound. `foreign_cb` and `off_subject` read the title, so they are close to exact (the live summary check can only add foreign-CB hits).
- **Precursor and Kalshi contributions are not stored**, so this says nothing about the PPI-to-CPI precursor weights or the Kalshi read.
- Same-URL pairs are 0 because the top 3 rarely repeats a URL; B6 dedup matters more over the full article list.
- This is a re-run of today's rules on old stored titles, not a re-score: it says which evidence would go, not what the new probability would have been.

## Cross-check against the audit

The audit (`docs/fundamental-analysis-audit-2026-10-16.md` section 2.1) quoted 45 rows / 17 occurrences with foreign-CB titles, and 92 of 137 FOMC-family unique articles with no Fed term. I could not reproduce either figure exactly:

| Measure | Audit | This report |
|---|---|---|
| Rows with a foreign-CB title, all families | 45 | 36 (B6 matcher); 39 (audit's name list ECB/BoE/BoJ/Lagarde/Ueda/Bailey/RBA/SNB as whole words); 42 (same list as plain substrings) |
| Occurrences with a foreign-CB title | 17 | 22 (B6 matcher, adds RBI/RBNZ/Philippine/China central bank); 13 (audit's list, whole words); 14 (substrings) |
| FOMC-family unique articles | 137 | 127 (by event, time and URL) / 103 (by title) |
| ... of which no Fed term in the title | 92 | 90 (by event, time and URL) / 79 (by title) |

The no-Fed-term figure is close (90 vs 92 of a slightly smaller base). The foreign-CB gap goes both ways: the B6 matcher finds more distinct occurrences because it knows more names (RBI, RBNZ, "Philippine central bank"), and fewer rows because it deliberately ignores bare "Bailey" (a non-central-banker). The audit's exact query and snapshot are not recorded, so I cannot say why its row count is higher; the likely causes are a different row scope or matching on fields other than the title. The direction agrees (a minority of calls carry foreign-CB titles, a majority of FOMC articles carry no Fed term), and this report is the reproducible baseline from here.

## Post-deploy acceptance check

After the B6 restart, the table `prediction_article_contributions` records every included article. Run:

```text
python scripts\b6_contamination_report.py --db scoring\backtest_log.db --verify-since <restart time, UTC ISO, e.g. 2026-10-23T08:00:00+00:00>
```

It prints a single integer: included articles since that instant whose title names a foreign central bank. It must print **0**, immediately and again after a week (exit code 0 when 0, 1 otherwise, 2 if the database or the table is missing: a pre-B6 database fails loudly instead of reading as a pass). Run today against the live DB it exits 2 because the table does not exist yet.
