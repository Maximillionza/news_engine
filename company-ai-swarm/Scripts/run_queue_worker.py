"""Runs the objective queue worker as its own OS process, separate from the API gateway.

Source: Documentation/plans/SDK_MIGRATION_PLAN.md Section 4.2 item 3 ("New background
worker (separate from FastAPI process)"). Imports main.py's already-constructed session
factory and queue handler (so it reuses the same engine/dev-db config, identity/COO
bootstrap, and provider selection main.py already sets up at import time) and hands them to
queue_worker.run_forever() - the actual "poll every ~100ms" loop.

Usage:
    .venv/Scripts/python.exe Scripts/run_queue_worker.py
Stop with Ctrl+C (SIGINT) - main() catches KeyboardInterrupt and sets the stop event so
run_forever() exits its loop cleanly instead of dying mid-cycle.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "services"))
sys.path.insert(0, str(ROOT / "sdk"))
sys.path.insert(0, str(ROOT / "apps" / "api_gateway"))

import main as gateway_main  # noqa: E402
from queue_worker import DEFAULT_POLL_INTERVAL_SECONDS, run_forever  # noqa: E402


def main() -> None:
    stop_event = threading.Event()
    print(
        f"Queue worker starting (poll interval {DEFAULT_POLL_INTERVAL_SECONDS}s). Ctrl+C to stop.",
        flush=True,
    )
    try:
        run_forever(
            gateway_main._SessionFactory,
            handler=gateway_main._queue_handler,
            stop_event=stop_event,
        )
    except KeyboardInterrupt:
        stop_event.set()
        print("Queue worker stopping.", flush=True)


if __name__ == "__main__":
    main()
