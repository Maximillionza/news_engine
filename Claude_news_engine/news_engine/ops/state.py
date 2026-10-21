# ops/state.py
"""
Small operational-state DB (ops/ops_state.db) for the B4 health work.

Holds when each scheduled job last ran / last succeeded, the once-per-UTC-day
health-notice ledger and the instant tracking began (so a weekly job that has
not fired since deploy is amber, not red, on day one). Stdlib only: it is
imported by the job wrapper, the scheduler loops and the health check, and
none of those may fail because of it.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "ops_state.db"

JOB_NAMES: tuple[str, ...] = (
    "shock_poll",
    "shock_reality_check",
    "outcome_confirm",
    "reaction_incremental",
    "reaction_baselines",
    "tier1_capture_daily",
    "tier1_capture_weekly",
    "article_accumulator",
    "calendar_refresh",
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS job_runs (
    job              TEXT PRIMARY KEY,
    last_run_utc     TEXT NOT NULL,
    last_exit_code   INTEGER NOT NULL,
    last_success_utc TEXT
);
CREATE TABLE IF NOT EXISTS health_notices (
    utc_date     TEXT PRIMARY KEY,
    sent_at_utc  TEXT NOT NULL,
    detail       TEXT
);
CREATE TABLE IF NOT EXISTS ops_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class JobRun:
    job: str
    last_run_utc: dt.datetime
    last_exit_code: int
    last_success_utc: Optional[dt.datetime]


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def get_connection(db_path: Optional[Path | str] = None, now: Optional[dt.datetime] = None) -> sqlite3.Connection:
    # DB_PATH is resolved here (not as a default argument) so tests can patch it.
    path = db_path if db_path is not None else DB_PATH
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    stamp = (now or _utc_now()).isoformat()
    conn.execute("INSERT OR IGNORE INTO ops_meta (key, value) VALUES ('tracking_since_utc', ?)", (stamp,))
    conn.commit()
    return conn


def record_job_run(conn: sqlite3.Connection, job: str, finished_utc: dt.datetime, exit_code: int) -> None:
    """Upsert the job's latest run; last_success_utc only moves on exit 0."""
    if job not in JOB_NAMES:
        raise ValueError(f"unknown job {job!r}")
    stamp = finished_utc.isoformat()
    success = stamp if exit_code == 0 else None
    conn.execute(
        """INSERT INTO job_runs (job, last_run_utc, last_exit_code, last_success_utc)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(job) DO UPDATE SET
               last_run_utc = excluded.last_run_utc,
               last_exit_code = excluded.last_exit_code,
               last_success_utc = COALESCE(excluded.last_success_utc, job_runs.last_success_utc)""",
        (job, stamp, exit_code, success),
    )
    conn.commit()


def _parse(value: Optional[str]) -> Optional[dt.datetime]:
    return dt.datetime.fromisoformat(value) if value else None


def get_job_runs(conn: sqlite3.Connection) -> dict[str, JobRun]:
    rows = conn.execute("SELECT job, last_run_utc, last_exit_code, last_success_utc FROM job_runs").fetchall()
    return {
        r["job"]: JobRun(r["job"], _parse(r["last_run_utc"]), r["last_exit_code"], _parse(r["last_success_utc"]))
        for r in rows
    }


def get_tracking_since(conn: sqlite3.Connection) -> dt.datetime:
    row = conn.execute("SELECT value FROM ops_meta WHERE key = 'tracking_since_utc'").fetchone()
    return dt.datetime.fromisoformat(row["value"])


def touch_heartbeat(job: str, now: Optional[dt.datetime] = None, db_path: Optional[Path] = None) -> None:
    """Record a successful tick for a loop-style job. Never raises."""
    try:
        conn = get_connection(db_path)
        try:
            record_job_run(conn, job, now or _utc_now(), 0)
        finally:
            conn.close()
    except Exception as exc:  # fail-open: a heartbeat must never stop its loop
        print(f"[ops.state] WARNING: heartbeat for {job} not recorded: {exc}")


def health_notice_sent(conn: sqlite3.Connection, utc_date: dt.date) -> bool:
    row = conn.execute("SELECT 1 FROM health_notices WHERE utc_date = ?", (utc_date.isoformat(),)).fetchone()
    return row is not None


def claim_health_notice(conn: sqlite3.Connection, utc_date: dt.date, claimed_at_utc: dt.datetime, detail: str) -> bool:
    """Atomically claim the day's notice: True only for the one caller whose INSERT created the row."""
    cur = conn.execute(
        "INSERT OR IGNORE INTO health_notices (utc_date, sent_at_utc, detail) VALUES (?, ?, ?)",
        (utc_date.isoformat(), claimed_at_utc.isoformat(), detail),
    )
    conn.commit()
    return cur.rowcount == 1


def release_health_notice(conn: sqlite3.Connection, utc_date: dt.date) -> None:
    """Delete the day's claim (the send failed, so the next trigger retries)."""
    conn.execute("DELETE FROM health_notices WHERE utc_date = ?", (utc_date.isoformat(),))
    conn.commit()


def record_health_notice(conn: sqlite3.Connection, utc_date: dt.date, sent_at_utc: dt.datetime, detail: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO health_notices (utc_date, sent_at_utc, detail) VALUES (?, ?, ?)",
        (utc_date.isoformat(), sent_at_utc.isoformat(), detail),
    )
    conn.commit()
