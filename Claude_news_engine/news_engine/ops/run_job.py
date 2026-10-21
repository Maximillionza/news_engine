# ops/run_job.py
"""
Wrapper every scheduled launcher (.bat / .vbs) runs its python job through:

    python -m ops.run_job --job NAME --log PATH -- <python args>

It rotates the log (1 MB, one backup), prefixes every output line with a SAST
timestamp, drains the child's output so a chatty job can never block on a full
pipe, and records the exit code in ops_state.db for the health check.
Everything here is fail-open: a locked log or an unwritable state DB is
reported once on stderr and the job still runs and returns its own exit code.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional, TextIO

from config.settings import LOCAL_TZ
from ops import state

LOG_MAX_BYTES = 1_000_000
LOG_BACKUPS = 1


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def timestamp_prefix(now_utc: dt.datetime) -> str:
    return now_utc.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S SAST")


def _warn(message: str) -> None:
    print(f"[run_job] WARNING: {message}", file=sys.stderr)


def rotate_if_needed(log_path: Path, max_bytes: int = LOG_MAX_BYTES, backups: int = LOG_BACKUPS) -> bool:
    """Shift log -> log.1 (-> log.2 ...) once the log reaches max_bytes."""
    try:
        if not log_path.exists() or log_path.stat().st_size < max_bytes:
            return False
        # Oldest first, so nothing is overwritten before it has moved up.
        for i in range(backups, 1, -1):
            older = log_path.with_name(f"{log_path.name}.{i - 1}")
            if older.exists():
                os.replace(older, log_path.with_name(f"{log_path.name}.{i}"))
        os.replace(log_path, log_path.with_name(f"{log_path.name}.1"))
        return True
    except OSError as exc:
        # Another process holding the file is normal (overlapping runs).
        _warn(f"could not rotate {log_path}: {exc}")
        return False


def _open_log(log_path: Path) -> Optional[TextIO]:
    try:
        return open(log_path, "a", encoding="utf-8")
    except OSError as exc:
        _warn(f"could not open {log_path}: {exc}")
        return None


def run_logged(
    job: str,
    log_path: Path,
    child_args: list[str],
    *,
    max_bytes: int = LOG_MAX_BYTES,
    backups: int = LOG_BACKUPS,
    clock: Callable[[], dt.datetime] = _utc_now,
    ops_db: Optional[Path] = None,
) -> int:
    log_path = Path(log_path)
    rotate_if_needed(log_path, max_bytes, backups)
    log: Optional[TextIO] = _open_log(log_path)

    def emit(text: str) -> None:
        nonlocal log
        if log is None:
            return
        try:
            log.write(f"{timestamp_prefix(clock())} {text}\n")
            log.flush()
        except OSError as exc:
            _warn(f"log write failed, continuing without a log: {exc}")
            log = None

    emit(f"[run_job] {job} starting: python {' '.join(child_args)}")
    try:
        proc = subprocess.Popen(
            [sys.executable, "-u", *child_args],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
    except OSError as exc:
        emit(f"[run_job] {job} could not start: {exc}")
        code = 1
    else:
        # Reading to EOF drains the pipe, so the child can never block on it.
        assert proc.stdout is not None
        for line in proc.stdout:
            emit(line.rstrip())
        code = proc.wait()
    emit(f"[run_job] {job} finished (exit {code})")

    try:
        conn = state.get_connection(ops_db)
        try:
            state.record_job_run(conn, job, clock(), code)
        finally:
            conn.close()
    except Exception as exc:  # fail-open: bookkeeping must not change the job's result
        _warn(f"run of {job} not recorded: {exc}")
    if log is not None:
        try:
            log.close()
        except OSError:
            pass
    return code


def main(argv: Optional[list[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        prog="python -m ops.run_job",
        usage="python -m ops.run_job --job NAME --log PATH -- <python args>",
    )
    parser.add_argument("--job", required=True, choices=state.JOB_NAMES)
    parser.add_argument("--log", required=True)
    if "--" not in args:
        parser.error("missing '--' before the python arguments")
    sep = args.index("--")
    child_args = args[sep + 1:]
    if not child_args:
        parser.error("nothing to run after '--'")
    opts = parser.parse_args(args[:sep])
    return run_logged(opts.job, Path(opts.log), child_args)


if __name__ == "__main__":
    sys.exit(main())
