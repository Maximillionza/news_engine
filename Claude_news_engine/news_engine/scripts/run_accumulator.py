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

from config.settings import INSTRUMENTS
from scoring.backtest_accumulator import start_accumulator


def main():
    tracked = list(INSTRUMENTS.keys())
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
    main()
