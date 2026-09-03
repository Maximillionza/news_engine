"""
One-off migration: backfills event_history.country = 'USD' for every
existing row whose source guarantees it's a genuine US release by
construction — 'seeded' (data_layer/historical_events.py's hand-researched
facts, all explicitly USD), 'live_web_fallback' (scripts/fill_missing_actuals.py's
FACTS, same discipline), and 'fred' (data_layer/fred_actuals.py's fallback,
whose ~10-title coverage table is US-only by design).

Why not 'live' rows too: those came from Forex Factory's live feed, which
DOES carry a real country tag per event — but this project's event_history
table had no country COLUMN to store it in until now (see
webapp/store.py's _migrate_add_country_column()), so a live row's true
country was never persisted and can't be safely reconstructed after the
fact. Confirmed live (2026-09-03) that some 'live' rows under generic,
internationally-shared titles ("CPI m/m", "Retail Sales m/m",
"Unemployment Rate") are genuinely foreign (Australia/UK/Japan/Eurozone),
not USD — assuming 'live' == USD here would silently re-introduce exactly
the contamination this fix exists to close. Those rows stay country=NULL
(genuinely unknown) until self-healed by a future resolving upsert_event_
history() call (which now always populates country from the real
EconomicEvent.country) or superseded by fresh live data.

Safe to re-run: only ever sets country when it is currently NULL, and only
for the three guaranteed-USD sources.

Usage:
    python scripts/migrate_country_backfill.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GUARANTEED_USD_SOURCES = ("seeded", "live_web_fallback", "fred")


def run(conn) -> int:
    placeholders = ",".join("?" for _ in GUARANTEED_USD_SOURCES)
    cursor = conn.execute(
        f"UPDATE event_history SET country = 'USD' WHERE country IS NULL AND source IN ({placeholders})",
        GUARANTEED_USD_SOURCES,
    )
    conn.commit()
    return cursor.rowcount


if __name__ == "__main__":
    import webapp.store as store

    conn = store.get_connection()
    migrated = run(conn)
    conn.close()
    print(f"[migrate_country_backfill] {migrated} row(s) backfilled to country='USD' "
          f"(source in {GUARANTEED_USD_SOURCES!r})")
