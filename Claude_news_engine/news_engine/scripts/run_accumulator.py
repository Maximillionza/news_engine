"""
Long-running entry point for the article-based backtest accumulator.

scoring/backtest_accumulator.py's own __main__ block only runs ONE cycle
and exits — nothing previously called start_accumulator() continuously,
so the adaptive-interval background loop it builds was dead code in
practice. This script is what actually keeps it running.

Run this as its own process (not through webapp/ — the dashboard is
essence-only by design; this accumulator is article-based and a
separate concern, same separation as everywhere else in this project):

    python scripts/run_accumulator.py

Stop with Ctrl-C.
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.backtest_accumulator import start_accumulator
import webapp.store as store


def main():
    # Reads the dashboard's OWN live tracked-symbols list (2026-09-13) —
    # previously read config.settings.INSTRUMENTS.keys() instead, a
    # separate, hand-maintained 2-entry dict (XAUUSD, US30) that silently
    # never grew when a new symbol was added via the dashboard's "Add"
    # form. A symbol added there now gets real article-based scoring too,
    # the next time this process is (re)started — start_accumulator()'s
    # background loop still reuses a fixed list for its own lifetime, so
    # adding/removing a symbol on the live dashboard while this process
    # is already running still needs a restart to take effect, same as
    # every instrument-related change already required before this fix.
    conn = store.get_connection()
    tracked = store.list_tracked_symbols(conn)
    conn.close()
    if not tracked:
        print("No tracked symbols found in the dashboard's tracked_symbols table — nothing to accumulate. "
              "Add a symbol via the dashboard's \"Add\" form first, then restart this process.")
        return
    print(f"Starting the article-based backtest accumulator for: {tracked}")
    print("Poll interval adapts to how close the nearest tracked event is "
          "(webapp/scheduler.py's compute_adaptive_interval_seconds tiers, reused here).")
    print("Press Ctrl-C to stop.\n")

    start_accumulator(tracked)

    # start_accumulator's loop runs in a daemon thread — a daemon thread
    # dies the instant its process would otherwise exit, so this process
    # has to stay alive on the main thread for the accumulator to run at
    # all. Sleeping in a loop here is that "stay alive" — the real work
    # all happens in the background thread already started above.
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\nStopping.")


if __name__ == "__main__":
    # See webapp/app.py's identical reconfigure() call for why: this
    # process's background thread logs non-ASCII characters (e.g. the ⚠
    # in ProbabilityResult.summary), which crashed a live cycle on
    # Windows' default cp1252 console codepage (confirmed 2026-08-19 —
    # "'charmap' codec can't encode character '⚠'"). Forcing real
    # UTF-8 here removes that crash at its source.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    main()
