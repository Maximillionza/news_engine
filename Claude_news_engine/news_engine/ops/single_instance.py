"""
Single-instance guard for the long-running engine processes
(webapp/app.py and scripts/run_accumulator.py) - B4 O8.

Found 2026-10-20: two full engine copies ran at once (the AutoStart task
at logon plus the desktop "News Engine.bat"), each with its own Flask
scheduler hitting Forex Factory. A second launch now exits with code 3
(ALREADY_RUNNING_EXIT_CODE); scripts/_restart_loop.bat treats that code
as "stop", so a refused copy does not relaunch every 5 seconds.
"""
from __future__ import annotations

import os
import socket
from pathlib import Path
from typing import Optional

try:
    import msvcrt  # Windows
except ImportError:  # pragma: no cover - POSIX
    msvcrt = None
    import fcntl

ALREADY_RUNNING_EXIT_CODE = 3
LOCK_DIR = Path(__file__).parent  # files: ops/<name>.lock, ops/<name>.pid


class InstanceLock:
    """Holds the open lock file; the lock lives as long as this object (or the process)."""

    def __init__(self, handle) -> None:
        self._handle = handle

    def release(self) -> None:
        handle, self._handle = self._handle, None
        if handle is None:
            return
        try:
            handle.seek(0)
            if msvcrt is not None:
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        finally:
            handle.close()


def try_acquire(name: str, lock_dir: Path = LOCK_DIR) -> Optional[InstanceLock]:
    """
    Take a non-blocking exclusive OS lock on byte 0 of <name>.lock. None if
    another process (or another handle in this one) already holds it.

    The OS releases the lock when the holding process dies, so a crashed
    instance never leaves a stale lock behind (no PID-liveness guessing,
    no PID-reuse risk). The .pid file is informational only.
    """
    lock_dir = Path(lock_dir)
    handle = open(lock_dir / f"{name}.lock", "a+")
    try:
        handle.seek(0)
        if msvcrt is not None:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    try:
        (lock_dir / f"{name}.pid").write_text(str(os.getpid()))
    except OSError:
        pass  # informational only
    return InstanceLock(handle)


def running_pid(name: str, lock_dir: Path = LOCK_DIR) -> Optional[int]:
    try:
        return int((Path(lock_dir) / f"{name}.pid").read_text().strip())
    except Exception:  # noqa: BLE001 - informational; any failure means "unknown"
        return None


def port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """True if something already accepts connections on host:port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def claim_or_exit(name: str, *, port: Optional[int] = None, lock_dir: Path = LOCK_DIR) -> InstanceLock:
    """Return the held lock, or exit with code 3 if another copy is running (lock busy, or the port is already answering)."""
    lock = try_acquire(name, lock_dir)
    if lock is not None and port is not None and port_in_use(port):
        lock.release()  # a copy started before locks existed (or by hand) owns the port
        lock = None
    if lock is None:
        pid = running_pid(name, lock_dir)
        print(f"[{name}] another instance is already running (PID {pid or 'unknown'}) - "
              f"exiting without starting (exit {ALREADY_RUNNING_EXIT_CODE})")
        raise SystemExit(ALREADY_RUNNING_EXIT_CODE)
    return lock
