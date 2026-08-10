"""
Single entry point that starts the dashboard (webapp/app.py, which starts
its own internal essence-only scheduler thread) and the article-based
backtest accumulator (scripts/run_accumulator.py) together, as separate
subprocesses, with combined tagged output in one terminal. Ctrl+C stops
both cleanly.

Deliberately does NOT include scripts/confirm_backtest_outcomes.py
(interactive, needs a real stdin) or scripts/run_live_check.py (a one-off
diagnostic, not a continuous service) — those stay separate manual
commands, run directly when needed. No daemonization, no auto-restart on
crash — matches this project's existing personal-tool scale; if either
process exits on its own, this stops the other and exits too.

Usage:
    python scripts/run_all.py
"""
import subprocess
import sys
import os
import threading
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SERVICES = [
    ("dashboard", [sys.executable, "-m", "webapp.app"]),
    ("accumulator", [sys.executable, "scripts/run_accumulator.py"]),
]

POLL_INTERVAL_SECONDS = 1.0
SHUTDOWN_TIMEOUT_SECONDS = 10


def _stream_output(name, pipe):
    for line in iter(pipe.readline, ""):
        print(f"[{name}] {line.rstrip()}")
    pipe.close()


def start_service(name, cmd, cwd=None):
    proc = subprocess.Popen(
        cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    threading.Thread(target=_stream_output, args=(name, proc.stdout), daemon=True).start()
    print(f"[run_all] started {name} (pid {proc.pid})")
    return proc


def supervise(processes, poll_interval_seconds=POLL_INTERVAL_SECONDS, sleep_fn=time.sleep):
    """
    Polls every process's exit status until either one exits on its own
    (crash) or a KeyboardInterrupt arrives (Ctrl+C), then terminates every
    process that's still running and waits for clean shutdown, force-
    killing any that don't stop within SHUTDOWN_TIMEOUT_SECONDS.

    `processes` is a list of (name, Popen-like object) — Popen-like needs
    .poll(), .terminate(), .wait(timeout=...), .kill(). Split out from
    main() so tests can inject fake process objects instead of spawning
    real subprocesses.
    """
    try:
        while True:
            for name, proc in processes:
                exit_code = proc.poll()
                if exit_code is not None:
                    print(f"[run_all] {name} exited unexpectedly (code {exit_code}) — stopping everything")
                    return
            sleep_fn(poll_interval_seconds)
    except KeyboardInterrupt:
        print("\n[run_all] stopping...")
    finally:
        for name, proc in processes:
            if proc.poll() is None:
                proc.terminate()
        for name, proc in processes:
            try:
                proc.wait(timeout=SHUTDOWN_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("[run_all] stopped.")


def main():
    processes = [(name, start_service(name, cmd, cwd=REPO_ROOT)) for name, cmd in SERVICES]
    print("[run_all] both services running — Ctrl+C to stop both\n")
    supervise(processes)


if __name__ == "__main__":
    main()
