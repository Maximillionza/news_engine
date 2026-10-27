"""
B8 (2026-10-27) re-score report: which recorded USD essence calls would change
direction if the standardized surprise (scoring/surprise_scale.py) had been in
force, using only data each release could have seen (sigma from strictly prior
rows).

For every USD event_history row whose title has an EVENT_SURPRISE_DIRECTION and
whose forecast and actual both parse, the row is scored twice per symbol with
the dashboard's own scorer (webapp/scoring_service.score_event_for_symbol):
  old = surprise_sigma None  (today's percent method)
  new = with_surprise_sigma(conn, event)  (z-based when >= 6 priors, else the
        same percent method, so short-history rows cannot change)

Read-only and offline: the database is opened through a SQLite
`file:...?mode=ro` URI, so a bug here cannot write to the live dashboard.db.
Accumulator (article-based) calls are affected only through precursor
contributions and are NOT re-run here -- they need the article bundles.

Usage (from the app dir):
    python scripts/b8_rescore_report.py --out docs/superpowers/specs/2026-10-27-b8-rescore-report.md
    python scripts/b8_rescore_report.py --db <path>/dashboard.db --out report.md
"""
from __future__ import annotations

import argparse
import datetime as dt
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import (
    EVENT_SURPRISE_DIRECTION,
    MIN_PRIOR_SURPRISES_FOR_SIGMA,
    STANDARDIZED_SURPRISE_SENSITIVITY,
    SURPRISE_SIGMA_MAX_HISTORY,
)
from data_layer.calendar_feed import EconomicEvent, _parse_numeric
from scoring.surprise_scale import prior_surprises, with_surprise_sigma
from webapp.scoring_service import score_event_for_symbol
from webapp.symbols import classify_symbol

SAST = dt.timezone(dt.timedelta(hours=2))
DEFAULT_DB = Path(__file__).resolve().parent.parent / "webapp" / "dashboard.db"
SHIFT_THRESHOLD = 0.10   # probability shift (0-1) counted as material in the summary
TOP_SHIFTS = 20


@dataclass(frozen=True)
class RescoreRow:
    title: str
    event_time_utc: str          # as stored
    forecast: str
    actual: str
    n_prior: int                 # usable prior surprises (capped at SURPRISE_SIGMA_MAX_HISTORY)
    sigma: Optional[float]
    z: Optional[float]
    method: str                  # "z" | "fallback"
    old_score: float             # USD surprise score (not the symbol score), percent method
    new_score: float             # USD surprise score, standardized when sigma exists
    old_dirs: dict[str, str]
    new_dirs: dict[str, str]
    old_prob: dict[str, float]
    new_prob: dict[str, float]
    changed: bool


def open_readonly(path: Path) -> sqlite3.Connection:
    """Read-only connection: any write raises sqlite3.OperationalError."""
    if not Path(path).exists():
        raise FileNotFoundError(f"database not found: {path}")
    conn = sqlite3.connect(f"file:{Path(path).resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _parse_time(text: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)


def rescore_rows(conn: sqlite3.Connection, symbols: tuple[str, ...] = ("XAUUSD", "US30")) -> list[RescoreRow]:
    """Every scoreable USD row, ascending by release time, scored old vs new."""
    classes = [classify_symbol(s) for s in symbols]
    titles = sorted(EVENT_SURPRISE_DIRECTION)
    marks = ",".join("?" for _ in titles)
    rows = conn.execute(
        "SELECT event_title, event_time_utc, forecast, actual, impact FROM event_history "
        f"WHERE country = 'USD' AND forecast IS NOT NULL AND actual IS NOT NULL AND event_title IN ({marks}) "
        "ORDER BY julianday(event_time_utc), event_title",
        titles,
    ).fetchall()
    out: list[RescoreRow] = []
    for r in rows:
        if _parse_numeric(r["forecast"]) is None or _parse_numeric(r["actual"]) is None:
            continue
        when = _parse_time(r["event_time_utc"])
        event = EconomicEvent(r["event_title"], "USD", r["impact"] or "Low", when,
                              forecast=r["forecast"], actual=r["actual"])
        scaled = with_surprise_sigma(conn, event)
        old_usd = event.usd_surprise_score()
        new_usd = scaled.usd_surprise_score()
        if old_usd is None or new_usd is None:
            continue
        sigma = scaled.surprise_sigma
        z = (_parse_numeric(r["actual"]) - _parse_numeric(r["forecast"])) / sigma if sigma else None
        old_dirs, new_dirs, old_prob, new_prob = {}, {}, {}, {}
        for sc in classes:
            old = score_event_for_symbol(event, sc)
            new = score_event_for_symbol(scaled, sc)
            old_dirs[sc.symbol], new_dirs[sc.symbol] = old.direction.value, new.direction.value
            old_prob[sc.symbol], new_prob[sc.symbol] = old.probability, new.probability
        out.append(RescoreRow(
            title=r["event_title"], event_time_utc=r["event_time_utc"],
            forecast=r["forecast"], actual=r["actual"],
            n_prior=len(prior_surprises(conn, r["event_title"], when)),
            sigma=sigma, z=z, method="z" if sigma else "fallback",
            old_score=old_usd, new_score=new_usd,
            old_dirs=old_dirs, new_dirs=new_dirs, old_prob=old_prob, new_prob=new_prob,
            changed=any(old_dirs[s] != new_dirs[s] for s in old_dirs),
        ))
    return out


def _sast_with_utc(stored: str) -> str:
    when = _parse_time(stored)
    return f"{when.astimezone(SAST):%Y-%m-%d %H:%M} SAST ({when.astimezone(dt.timezone.utc):%Y-%m-%dT%H:%MZ}; stored {stored})"


def _max_shift(row: RescoreRow) -> float:
    return max(abs(row.new_prob[s] - row.old_prob[s]) for s in row.old_prob)


def _fmt(value: Optional[float], digits: int = 3) -> str:
    return "-" if value is None else f"{value:.{digits}f}"


def render_report(rows: list[RescoreRow], generated_at: dt.datetime, db_label: str) -> str:
    """Markdown report (LF newlines; main() converts to CRLF when writing)."""
    symbols = list(rows[0].old_dirs) if rows else ["XAUUSD", "US30"]
    z_rows = [r for r in rows if r.method == "z"]
    lines: list[str] = [
        "# B8 re-score report",
        "",
        f"- Generated: {generated_at.astimezone(SAST):%Y-%m-%d %H:%M} SAST ({generated_at.astimezone(dt.timezone.utc):%Y-%m-%d %H:%M} UTC)",
        f"- Database: `{db_label}` (opened read-only, `mode=ro`)",
        f"- Constants: minimum prior surprises {MIN_PRIOR_SURPRISES_FOR_SIGMA}, history cap {SURPRISE_SIGMA_MAX_HISTORY}, "
        f"standardized sensitivity {STANDARDIZED_SURPRISE_SENSITIVITY}",
        "- Old = percent method; new = z = (actual - forecast) / sigma of strictly prior surprises, "
        "tanh(0.5 z), percent method below 6 priors.",
        "",
        "## Summary",
        "",
        f"- Scored rows: {len(rows)} (z method {len(z_rows)}, fallback {len(rows) - len(z_rows)})",
    ]
    for s in symbols:
        n_dir = sum(1 for r in rows if r.old_dirs[s] != r.new_dirs[s])
        n_shift = sum(1 for r in rows if abs(r.new_prob[s] - r.old_prob[s]) >= SHIFT_THRESHOLD)
        lines.append(f"- {s}: {n_dir} direction changes; {n_shift} probability shifts >= {SHIFT_THRESHOLD:.2f}")
    lines += ["", "## Direction changes", ""]
    changed = [r for r in rows if r.changed]
    if not changed:
        lines.append("No direction changes.")
    else:
        lines += [
            "| Title | Release | Forecast | Actual | n prior | Sigma | z | " + " | ".join(f"{s} old -> new (prob)" for s in symbols) + " |",
            "|---|---|---|---|---|---|---|" + "---|" * len(symbols),
        ]
        for r in changed:
            cells = [
                f"{r.old_dirs[s]} -> {r.new_dirs[s]} ({r.old_prob[s]:.3f} -> {r.new_prob[s]:.3f})" for s in symbols
            ]
            lines.append(
                f"| {r.title} | {_sast_with_utc(r.event_time_utc)} | {r.forecast} | {r.actual} | {r.n_prior} | "
                f"{_fmt(r.sigma, 4)} | {_fmt(r.z, 3)} | " + " | ".join(cells) + " |"
            )
    lines += ["", f"## Largest probability shifts (top {TOP_SHIFTS})", ""]
    top = sorted(rows, key=_max_shift, reverse=True)[:TOP_SHIFTS]
    if not top or _max_shift(top[0]) == 0:
        lines.append("No probability shifts.")
    else:
        lines += [
            "| Title | Release | Forecast | Actual | z | Max shift | " + " | ".join(f"{s} prob old -> new" for s in symbols) + " |",
            "|---|---|---|---|---|---|" + "---|" * len(symbols),
        ]
        for r in top:
            if _max_shift(r) == 0:
                break
            cells = [f"{r.old_prob[s]:.3f} -> {r.new_prob[s]:.3f}" for s in symbols]
            lines.append(
                f"| {r.title} | {_sast_with_utc(r.event_time_utc)} | {r.forecast} | {r.actual} | {_fmt(r.z, 3)} | "
                f"{_max_shift(r):.3f} | " + " | ".join(cells) + " |"
            )
    lines += ["", "## Sigma by title (latest scored release)", ""]
    latest: dict[str, RescoreRow] = {}
    for r in rows:        # ascending, so the last write per title is the latest release
        latest[r.title] = r
    if not latest:
        lines.append("No scored rows.")
    else:
        lines += ["| Title | Latest release | n prior | Sigma | Method |", "|---|---|---|---|---|"]
        for title in sorted(latest):
            r = latest[title]
            lines.append(f"| {title} | {_sast_with_utc(r.event_time_utc)} | {r.n_prior} | {_fmt(r.sigma, 4)} | {r.method} |")
    lines += [
        "",
        "## Note",
        "",
        "Accumulator (article-based) calls are affected only through precursor contributions and are not re-run "
        "here; that needs the article bundles.",
        "",
    ]
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="B8 read-only re-score report")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="dashboard.db path (opened read-only)")
    parser.add_argument("--out", required=True, help="markdown report path (written with CRLF)")
    args = parser.parse_args(argv)
    try:
        conn = open_readonly(Path(args.db))
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    try:
        rows = rescore_rows(conn)
    finally:
        conn.close()
    text = render_report(rows, dt.datetime.now(dt.timezone.utc), args.db)
    Path(args.out).write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    n_changed = sum(1 for r in rows if r.changed)
    print(f"scored {len(rows)} rows, {n_changed} direction changes -> {args.out}")
    return 0


if __name__ == "__main__":
    # Example: python scripts/b8_rescore_report.py --out %TEMP%\b8_rescore.md
    sys.exit(main())
