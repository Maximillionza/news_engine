"""
One-off migration: renames event_title 'ADP Nonfarm Employment Change' ->
'ADP Non-Farm Employment Change' across every table that stores it, in both
this project's SQLite databases.

Why: config/settings.py's event title for the ADP private-payrolls report
was "ADP Nonfarm Employment Change" (no hyphen) -- a guessed spelling that
never matched Forex Factory's real live feed. Confirmed live 2026-09-02:
the live feed actually sends "ADP Non-Farm Employment Change" (hyphenated).
Every title-keyed lookup in this codebase (EVENT_SURPRISE_DIRECTION,
EVENT_REGISTRY, EVENT_INFLUENCE_LINKS, ACCUMULATOR_MEDIUM_ALLOWLIST,
KALSHI_SERIES_BY_EVENT_TITLE, FRED_RELEASE_ID_BY_EVENT_TITLE) was blind to
the live title, so ADP's actual was never filled by any fallback and its
precursor links to NFP/Unemployment Rate/Average Hourly Earnings m/m never
resolved. config/settings.py and data_layer/historical_events.py were
corrected to the real hyphenated title; this migration re-points historical
rows stored under the old title so they aren't silently orphaned (invisible
to every future lookup) -- same pattern as
scripts/migrate_gdp_title_rename.py's 'Advance GDP q/q' -> 'Prelim GDP q/q'
fix last month.

Safe to run more than once (each UPDATE is a no-op the second time, since
no row will still have the old title after the first run).

Usage:
    python scripts/migrate_adp_title_rename.py
"""
import sys
import os
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OLD_TITLE = "ADP Nonfarm Employment Change"
NEW_TITLE = "ADP Non-Farm Employment Change"

# (table, unique_columns_besides_event_title) — unique_columns is None for
# tables with no UNIQUE constraint involving event_title (a plain UPDATE
# can't collide); a tuple names the OTHER columns in a UNIQUE constraint
# that includes event_title, so a collision is handled per-row.
DASHBOARD_TABLES = [
    ("event_history", None),
    ("macro_calendar", None),
]
BACKTEST_TABLES = [
    ("predictions", None),
    ("outcomes", ("instrument", "event_time_utc")),
    ("dismissals", ("instrument", "event_time_utc")),
    ("print_predictions", None),
    ("kalshi_reads", None),
]


def _migrate_table(conn: sqlite3.Connection, table: str, unique_cols) -> tuple[int, int]:
    """Returns (migrated_count, skipped_count) for this table."""
    if unique_cols is None:
        cursor = conn.execute(
            f"UPDATE {table} SET event_title = ? WHERE event_title = ?",
            (NEW_TITLE, OLD_TITLE),
        )
        conn.commit()
        return cursor.rowcount, 0

    # Has a UNIQUE constraint including event_title -- migrate row by row
    # so one collision (a row already exists under NEW_TITLE for the same
    # unique key) doesn't abort every other row.
    # `AS rid` — SQLite reports a plain `rowid` select back under the
    # table's own INTEGER PRIMARY KEY column name (e.g. "id") when one
    # exists, not literally "rowid", so sqlite3.Row["rowid"] would raise
    # IndexError. An explicit alias sidesteps that entirely.
    rows = conn.execute(f"SELECT rowid AS rid FROM {table} WHERE event_title = ?", (OLD_TITLE,)).fetchall()
    migrated, skipped = 0, 0
    for row in rows:
        rowid = row["rid"]
        try:
            conn.execute(f"UPDATE {table} SET event_title = ? WHERE rowid = ?", (NEW_TITLE, rowid))
            conn.commit()
            migrated += 1
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            print(f"  WARNING: could not migrate {table} rowid={rowid}: {exc}")
            skipped += 1
    return migrated, skipped


def run(conn: sqlite3.Connection, tables: list[tuple[str, object]]) -> None:
    for table, unique_cols in tables:
        migrated, skipped = _migrate_table(conn, table, unique_cols)
        print(f"  {table}: {migrated} row(s) migrated" + (f", {skipped} skipped (collision)" if skipped else ""))


if __name__ == "__main__":
    import webapp.store as dash_store
    import scoring.backtest_store as backtest_store

    print(f"Migrating {OLD_TITLE!r} -> {NEW_TITLE!r}")

    print("Dashboard DB:")
    dash_conn = dash_store.get_connection()
    run(dash_conn, DASHBOARD_TABLES)
    dash_conn.close()

    print("Backtest DB:")
    bt_conn = backtest_store.get_connection()
    run(bt_conn, BACKTEST_TABLES)
    bt_conn.close()

    print("Done.")
