"""
B5 event study - the once-off, READ-ONLY runner (a study of release reactions; not a scheduled job).

Plan: docs/superpowers/plans/2026-10-21-b5-event-study.md (Task 4). The calculations live in the pure modules
event_study_metrics.py (window measures), event_study_groups.py (clusters, directions, group tables) and
event_study_checks.py (DXY chain, Cleveland dipstick); this file is the only one that touches a database,
the network or the disk.

What it does: reads every USD release minute since --since from the live dashboard.db, fetches Dukascopy
1-second BID bars for [t-2 min, t+31 min] (1-minute bars when the seconds are unusable) for XAUUSD, US30 and
DXY, measures each window, and writes releases.csv, members.csv, conflicts.csv, dipstick.csv, summary.json
and summary.md. It answers the co-release questions (spike then pull back? harder when they agree?), the
event -> USD -> instrument chain and the Cleveland nowcast dipstick.

Read-only guarantee:
  * dashboard.db and backtest_log.db are opened ONLY through open_readonly (sqlite URI mode=ro); nothing is
    ever written to them, no schema is created, a missing file is an error and never created.
  * Every file written (bar cache, CSV, JSON, Markdown) goes under --out-dir; an out-dir inside the repo is
    refused before anything is opened. No Telegram, no scheduler, no push. The nowcast CSV is only read;
    when missing, the study reports the commands to regenerate it and downloads nothing.
  * Dukascopy is the only network use: a pause (--pause, default 1.5 s) follows every request; fetched
    windows older than CACHE_MIN_AGE are cached on disk, so a re-run costs no requests; a failed fetch is
    never cached.

Usage (from the app dir):
    python scripts/event_study_once.py [--dry-run] [--offline] [--limit N] [--since 2026-01-01]
        [--dash-db PATH] [--bt-db PATH] [--nowcast-csv PATH] [--out-dir PATH] [--pause SECONDS]
--dry-run fetches nothing and prints only the sample block (compare with the known sample before a full run).
Expected run time: 3 requests (XAUUSD, US30, DXY) per release minute at the pause, plus 1-minute fallbacks;
roughly 30-45 minutes cold for about 200 release minutes, seconds when warm.
Exit code: 0 ok, 2 refused out-dir or missing database.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Optional

import pandas as pd

# Make `python scripts/...` work from the app dir (repo root on sys.path).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scoring import backtest_store  # noqa: E402
from scripts import event_study_checks as checks  # noqa: E402
from scripts import event_study_groups as groups  # noqa: E402
from scripts import event_study_metrics as metrics  # noqa: E402
from scripts.event_study_checks import LAGS_DAYS  # noqa: E402,F401  (re-exported for callers/tests)
from scripts.event_study_groups import Cluster, Member, RELEASE_ROW_KEYS  # noqa: E402
from scripts.event_study_metrics import Bar  # noqa: E402
from scripts.market_reaction_phase0 import _parse_utc  # noqa: E402
from webapp.reaction_rules import DUPLICATE_WITHIN, REACTION_BASELINE_QUANTILE  # noqa: E402

UTC = dt.timezone.utc

LIVE_ROOT = Path(r"C:\Users\Masoodt\Documents\Claude\Projects\.worktrees\news-engine-live"
                 r"\Claude_news_engine\news_engine")
LIVE_DASH_DB = LIVE_ROOT / "webapp" / "dashboard.db"
LIVE_BT_DB = LIVE_ROOT / "scoring" / "backtest_log.db"
DEFAULT_OUT_DIR = Path(r"C:\Users\Masoodt\AppData\Local\Temp\news_engine_event_study")
# Cleveland Fed daily nowcast history (CC BY 4.0), committed so E3 is reproducible after any scratchpad is cleaned.
DEFAULT_NOWCAST_CSV = Path(__file__).resolve().parents[1] / "docs" / "data" / "cleveland_nowcasts_2026.csv"
SYMBOLS = ("XAUUSD", "US30")
SERIES = SYMBOLS + ("DXY",)
START = dt.datetime(2026, 1, 1, tzinfo=UTC)
BEFORE = dt.timedelta(minutes=2)            # bars fetched from t - BEFORE ...
AFTER = dt.timedelta(minutes=31)            # ... to t + AFTER (30-min horizon + 1 min slack)
SETTLE = dt.timedelta(minutes=10)           # a minute is studied once t + AFTER + SETTLE <= now
CACHE_MIN_AGE = dt.timedelta(hours=1)       # only windows that ended this long ago are cached
DEFAULT_PAUSE_S = 1.5                       # seconds between Dukascopy requests
REPO_ROOT = Path(__file__).resolve().parents[3]
CPI_TITLES = ("CPI m/m", "Core CPI m/m")    # the Tier 1 dipstick releases
CACHE_COLUMNS = ["ts", "open", "high", "low", "close"]

# (instrument, interval tag "sec1" / "min1", lo, hi) -> OHLC frame with a tz-aware UTC index
FetchFn = Callable[[str, str, dt.datetime, dt.datetime], pd.DataFrame]

MEMBER_COLUMNS = ["t_utc", "t_sast", "title", "impact", "forecast", "actual", "surprise_side",
                  "surprise_steps", "usd_dir", "xauusd_dir", "us30_dir", "cluster_class"]


# =============================================================================================
# Read-only access and path guards
# =============================================================================================

def open_readonly(path: Path) -> sqlite3.Connection:
    """The ONLY way the study opens a live database: sqlite URI mode=ro. A missing file raises
    FileNotFoundError first, so sqlite can never create an empty database in its place."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"database not found: {path}")
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def assert_outside_repo(out_dir: Path) -> None:
    """ValueError when out_dir is the repo root or inside it (outputs and the bar cache stay out of git)."""
    resolved = Path(out_dir).resolve()
    if resolved == REPO_ROOT or REPO_ROOT in resolved.parents:
        raise ValueError(f"--out-dir {resolved} is inside the repo {REPO_ROOT}; pick a folder outside it")


def _db_path(conn: sqlite3.Connection) -> str:
    """File path of the main database of an open connection ('' for in-memory)."""
    try:
        return conn.execute("PRAGMA database_list").fetchone()[2] or ""
    except sqlite3.Error:
        return ""


# =============================================================================================
# Database reads
# =============================================================================================

def read_members(dash_conn: sqlite3.Connection, since: dt.datetime, until: dt.datetime) -> list[Member]:
    """USD event_history rows collapsed (same title within DUPLICATE_WITHIN) over ALL rows first, then
    filtered to [since, until], so a duplicate run straddling `since` is judged once."""
    rows = dash_conn.execute(
        "SELECT event_title, event_time_utc, forecast, actual, impact FROM event_history "
        "WHERE country = 'USD'").fetchall()
    members = [Member(r[0], _parse_utc(r[1]), r[2], r[3], r[4]) for r in rows]
    return [m for m in groups.collapse_members(members) if since <= m.when_utc <= until]


def read_baselines(bt_conn: sqlite3.Connection, symbol: str) -> dict[int, float]:
    """{utc_hour: typical |5-min move|} at REACTION_BASELINE_QUANTILE; {} when the table is missing."""
    try:
        return backtest_store.get_latest_reaction_baselines(bt_conn, symbol, REACTION_BASELINE_QUANTILE)
    except sqlite3.OperationalError:
        return {}


def baseline_for(baselines: dict[int, float], t: dt.datetime) -> Optional[float]:
    """The baseline of t's UTC hour (never the SAST hour)."""
    return baselines.get(t.astimezone(UTC).hour)


# =============================================================================================
# Dukascopy (the only network code) and the on-disk bar cache
# =============================================================================================

def dukascopy_instrument(series: str) -> str:
    """Dukascopy instrument id for XAUUSD / US30 / DXY."""
    if series == "DXY":
        from dukascopy_python.instruments import INSTRUMENT_IDX_AMERICA_DOLLAR_IDX_USD
        return INSTRUMENT_IDX_AMERICA_DOLLAR_IDX_USD
    from data_layer.dukascopy_feed import _resolve_dukascopy_instrument
    instrument = _resolve_dukascopy_instrument(series)
    if instrument is None:
        raise ValueError(f"no Dukascopy instrument for {series!r}")
    return instrument


def dukascopy_fetch(instrument: str, interval: str, lo: dt.datetime, hi: dt.datetime) -> pd.DataFrame:
    """BID OHLC bars for [lo, hi]; `interval` is the tag "sec1" (1 second) or "min1" (1 minute)."""
    import dukascopy_python as dk
    tags = {"sec1": dk.INTERVAL_SEC_1, "min1": dk.INTERVAL_MIN_1}
    return dk.fetch(instrument, tags[interval], dk.OFFER_SIDE_BID, lo, hi)


class BarCache:
    """Per (series, interval, release minute) bar windows, cached as CSV under root/bars.

    A hit reads the file and neither fetches nor sleeps. A miss fetches [t - BEFORE, t + AFTER], sleeps
    `pause_s` after every network call, and writes the file only when the window ended CACHE_MIN_AGE ago
    (a still-forming window is never cached). A header-only file means "fetched, no bars". A failed fetch
    returns None, counts an error and writes nothing. `offline` never touches the network (None on a miss).
    """

    def __init__(self, root: Path, fetch: FetchFn, now: dt.datetime, pause_s: float = DEFAULT_PAUSE_S,
                 sleep: Callable[[float], None] = time.sleep, offline: bool = False) -> None:
        self.root = Path(root)
        self.fetch = fetch
        self.now = now
        self.pause_s = pause_s
        self.sleep = sleep
        self.offline = offline
        self.network_requests = 0
        self.cache_hits = 0
        self.errors = 0

    def _path(self, series: str, interval_tag: str, t: dt.datetime) -> Path:
        return self.root / "bars" / f"{series}_{t.astimezone(UTC):%Y%m%dT%H%MZ}_{interval_tag}.csv"

    def get(self, series: str, interval_tag: str, t: dt.datetime) -> Optional[list[Bar]]:
        path = self._path(series, interval_tag, t)
        if path.exists():
            self.cache_hits += 1
            return self._read(path)
        if self.offline:
            return None
        self.network_requests += 1
        try:
            frame = self.fetch(dukascopy_instrument(series), interval_tag, t - BEFORE, t + AFTER)
            bars = metrics.bars_from_frame(frame)
        except Exception as exc:  # noqa: BLE001 - one bad window must not stop the study; it is retried next run
            self.errors += 1
            print(f"  fetch failed {series} {interval_tag} {t:%Y-%m-%d %H:%MZ}: {exc}", file=sys.stderr)
            return None
        finally:
            self.sleep(self.pause_s)                           # do not hammer the service
        if t + AFTER <= self.now - CACHE_MIN_AGE:
            self._write(path, bars)
        return bars

    @staticmethod
    def _read(path: Path) -> list[Bar]:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            next(reader, None)
            return [Bar(dt.datetime.fromisoformat(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]))
                    for r in reader if r]

    @staticmethod
    def _write(path: Path, bars: list[Bar]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(CACHE_COLUMNS)
            for b in bars:
                writer.writerow([b.ts.isoformat(), b.open, b.high, b.low, b.close])


def measure_series(cache: BarCache, series: str, t: dt.datetime) -> dict[str, Any]:
    """Window measures for one series and release minute: 1-second bars first; 1-minute bars are
    fetched only when choose_bars would reject the seconds (or they could not be fetched)."""
    sec_bars = cache.get(series, "sec1", t) or []
    min_bars: list[Bar] = []
    if metrics.choose_bars(sec_bars, [], t)[0] != "sec1":
        min_bars = cache.get(series, "min1", t) or []
    source, resolution, bars = metrics.choose_bars(sec_bars, min_bars, t)
    return metrics.measure_window(bars, t, source, resolution)


# =============================================================================================
# Study
# =============================================================================================

def _cluster_usd_dir(c: Cluster) -> Optional[int]:
    """The common USD direction of a single_directional / agree cluster, else None."""
    if groups.cluster_class(c) not in groups.DIRECTIONAL_CLASSES:
        return None
    dirs = {groups.usd_direction(m) for m in c.members} - {0, None}
    return dirs.pop() if len(dirs) == 1 else None


def _sample_block(clusters: list[Cluster], pending: int) -> dict[str, Any]:
    classes = Counter(groups.cluster_class(c) for c in clusters)
    counts = {cls: 0 for cls in groups.CLASS_ORDER}
    counts.update(classes)
    counts["agree_all_same"] = sum(1 for c in clusters if groups.all_same(c))
    multi = [c for c in clusters if len(c.members) > 1]
    computable = Counter(groups.cluster_class(c) for c in multi if groups.cluster_class(c) != "partial")
    return {
        "minutes": len(clusters),
        "minutes_multi": len(multi),
        "pending_minutes": pending,
        "classes": counts,
        "fully_computable_multi": {k: computable.get(k, 0) for k in ("agree", "conflict", "all_in_line")},
        "high_minutes": sum(1 for c in clusters if groups.cluster_impact(c) == "High"),
    }


def _fmt(value: Any) -> Any:
    return "" if value is None else value


def _write_csv(path: Path, header: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for row in rows:
            writer.writerow([_fmt(row.get(key)) for key in header])


def _flatten_conflict(detail: dict[str, Any]) -> dict[str, Any]:
    flat = dict(detail)
    flat["members"] = " | ".join(
        f"{m['title']} [{m['impact']}, dir={_fmt(m['instrument_dir'])}, steps={_fmt(m['surprise_steps'])}]"
        for m in detail["members"])
    for key, value in detail.items():
        if isinstance(value, list) and key != "members":
            flat[key] = " | ".join(value)
    return flat


def _member_rows(c: Cluster) -> list[dict[str, Any]]:
    out = []
    for m in c.members:
        out.append({
            "t_utc": m.when_utc.astimezone(UTC).isoformat(), "t_sast": groups._sast(m.when_utc),
            "title": m.title, "impact": groups.effective_impact(m), "forecast": m.forecast,
            "actual": m.actual, "surprise_side": groups.surprise_side(m),
            "surprise_steps": groups.surprise_steps(m), "usd_dir": groups.usd_direction(m),
            "xauusd_dir": groups.instrument_direction(m, "XAUUSD"),
            "us30_dir": groups.instrument_direction(m, "US30"), "cluster_class": groups.cluster_class(c),
        })
    return out


def _coverage(measured: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for series, items in measured.items():
        out[series] = {
            "n": len(items),
            "ok": sum(1 for m in items if m["status"] == "ok"),
            "no_data": sum(1 for m in items if m["status"] != "ok"),
            "sec1": sum(1 for m in items if m["bar_source"] == "sec1"),
            "min1": sum(1 for m in items if m["bar_source"] == "min1"),
            "none": sum(1 for m in items if m["bar_source"] == "none"),
        }
    return out


def _chain_block(rows_by_symbol: dict[str, list[dict[str, Any]]],
                 clusters: list[Cluster]) -> dict[str, Any]:
    """E2: event -> USD (vs DXY 5-min) and USD -> instrument (sign agreement and slope)."""
    by_minute = {r["t_utc"]: r for r in rows_by_symbol[SYMBOLS[0]]}
    event_rows = []
    for c in clusters:
        row = by_minute.get(c.minute.astimezone(UTC).isoformat())
        usd = _cluster_usd_dir(c)
        if row is not None and usd is not None and groups.usable(row, 5):
            event_rows.append((usd, row["dxy_net_5"], row["dxy_p0"]))
    out: dict[str, Any] = {
        "engine_sign": dict(checks.ENGINE_SIGN),
        "headline_bps": checks.HEADLINE_DXY_BPS,
        "event_usd": {f"{th:g}": checks.event_usd_agreement(event_rows, th) for th in checks.DXY_THRESHOLDS_BPS},
        "usd_instrument": {}, "ols": {},
    }
    for symbol in SYMBOLS:
        usable_rows = [r for r in rows_by_symbol[symbol] if groups.usable(r, 5)]
        triples = [(r["dxy_net_5"], r["dxy_p0"], r["net_5"]) for r in usable_rows]
        out["usd_instrument"][symbol] = {
            f"{th:g}": checks.usd_instrument_agreement(triples, checks.ENGINE_SIGN[symbol], th)
            for th in checks.DXY_THRESHOLDS_BPS}
        both = [r for r in usable_rows if r["dxy_net_5"] is not None and r["net_5"] is not None]
        pct = [r for r in both if (r["dxy_p0"] or 0) > 0 and (r["p0"] or 0) > 0]
        out["ols"][symbol] = {
            "abs": checks.ols([r["dxy_net_5"] for r in both], [r["net_5"] for r in both]),
            "pct": checks.ols([r["dxy_net_5"] / r["dxy_p0"] * 100 for r in pct],
                              [r["net_5"] / r["p0"] * 100 for r in pct]),
        }
    return out


def _regenerate_commands(out_dir: Path, dash_db: str, nowcast_csv: Path) -> str:
    return (
        f"1) fetch https://www.clevelandfed.org/-/media/files/webcharts/inflationnowcasting/nowcast_month.json "
        f"by hand into {out_dir / 'nowcast_month.json'}; "
        f"2) python scripts/cleveland_nowcast_to_csv.py {out_dir / 'nowcast_month.json'} {nowcast_csv} "
        f"--dash-db {dash_db or LIVE_DASH_DB}; "
        f"3) re-run this script with --nowcast-csv {nowcast_csv}")


def _snapshot_value(bt_conn: sqlite3.Connection, title: str, release: dt.datetime) -> Optional[float]:
    """Latest tier1_nowcast_snapshots value stamped strictly before the release (any kind)."""
    rows = bt_conn.execute(
        "SELECT event_time_utc, as_of_utc, nowcast_value FROM tier1_nowcast_snapshots WHERE event_title = ?",
        (title,)).fetchall()
    best: Optional[tuple[dt.datetime, float]] = None
    for r in rows:
        if _parse_utc(r[0]) != release:
            continue
        as_of = _parse_utc(r[1])
        if as_of < release and (best is None or as_of > best[0]):
            best = (as_of, r[2])
    return None if best is None else best[1]


def _dipstick_block(members: list[Member], bt_conn: sqlite3.Connection, nowcast_csv: Path, out_dir: Path,
                    dash_db: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """E3: every CPI m/m / Core CPI m/m release against the cached Cleveland nowcast history."""
    if not Path(nowcast_csv).exists():
        return {"status": "missing", "nowcast_csv": str(nowcast_csv),
                "regenerate": _regenerate_commands(out_dir, dash_db, Path(nowcast_csv))}, []
    points_by_key = checks.load_nowcast_csv(Path(nowcast_csv))
    rows: list[dict[str, Any]] = []
    releases: list[tuple[str, dt.datetime, list]] = []
    for m in members:
        if m.title not in CPI_TITLES:
            continue
        points = points_by_key.get((m.title, m.when_utc))
        if points is None:                                     # csv stamped by a collapsed duplicate row
            near = [k for k in points_by_key
                    if k[0] == m.title and abs(k[1] - m.when_utc) <= DUPLICATE_WITHIN]
            points = points_by_key[near[0]] if near else []
        releases.append((m.title, m.when_utc, points))
        for lag in checks.LAGS_DAYS:
            rows.append(checks.dipstick_row(m.title, m.when_utc, points, m.forecast, m.actual, lag))
    per_lag = {str(lag): checks.summarize_dipstick([r for r in rows if r["lag_days"] == lag])
               for lag in checks.LAGS_DAYS}
    t5 = [r for r in rows if r["lag_days"] == 5 and r["early"] is not None and r["final"] is not None]
    compared = equal = 0
    try:
        for title, release, points in releases:
            final = checks.final_value(points, release)
            snap = _snapshot_value(bt_conn, title, release)
            if final is not None and snap is not None:
                compared += 1
                equal += abs(final - snap) <= 1e-9
    except sqlite3.OperationalError:
        pass
    return {
        "status": "ok", "nowcast_csv": str(nowcast_csv), "headline_lag_days": checks.HEADLINE_LAG_DAYS,
        "n_releases": len(releases), "per_lag": per_lag,
        "t5_equals_final": {"n": len(t5), "equal": sum(1 for r in t5 if r["early_equals_final"])},
        "snapshot_check": {"n": compared, "equal": int(equal)},
    }, rows


def run_study(dash_conn: sqlite3.Connection, bt_conn: sqlite3.Connection, cache: BarCache, nowcast_csv: Path,
              out_dir: Path, since: dt.datetime, until: dt.datetime, limit: Optional[int] = None,
              dry_run: bool = False) -> dict[str, Any]:
    """Measure every studyable release minute, aggregate, write the outputs, return the summary.

    A minute is studied once t + AFTER + SETTLE <= cache.now (later ones are counted as pending). `limit`
    studies only the first N minutes. dry_run fetches and writes nothing and returns {"sample": ...}.
    """
    assert_outside_repo(out_dir)
    members = read_members(dash_conn, since, until)
    all_clusters = groups.build_clusters(members)
    all_minutes = [c.minute for c in all_clusters]
    studyable = [c for c in all_clusters if c.minute + AFTER + SETTLE <= cache.now]
    pending = len(all_clusters) - len(studyable)
    clusters = studyable[:limit] if limit is not None else studyable
    sample = _sample_block(clusters, pending)
    if dry_run:
        return {"sample": sample}

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    baselines = {symbol: read_baselines(bt_conn, symbol) for symbol in SYMBOLS}
    rows_by_symbol: dict[str, list[dict[str, Any]]] = {s: [] for s in SYMBOLS}
    measured: dict[str, list[dict[str, Any]]] = {s: [] for s in SERIES}
    conflicts: list[dict[str, Any]] = []
    member_rows: list[dict[str, Any]] = []
    for i, c in enumerate(clusters, 1):
        print(f"[{i}/{len(clusters)}] {groups._sast(c.minute)}: {' | '.join(m.title for m in c.members)}",
              file=sys.stderr)
        by_series = {series: measure_series(cache, series, c.minute) for series in SERIES}
        for series, result in by_series.items():
            measured[series].append(result)
        gap = groups.next_release_gap_min(c.minute, all_minutes)
        member_rows.extend(_member_rows(c))
        for symbol in SYMBOLS:
            row = groups.build_release_row(c, symbol, by_series[symbol], baseline_for(baselines[symbol], c.minute),
                                           gap, by_series["DXY"])
            rows_by_symbol[symbol].append(row)
            if row["cluster_class"] == "conflict":
                conflicts.append(groups.conflict_detail(c, row, symbol))

    all_rows = [r for s in SYMBOLS for r in rows_by_symbol[s]]
    all_rows.sort(key=lambda r: (r["t_utc"], SYMBOLS.index(r["symbol"])))
    dipstick, dip_rows = _dipstick_block(members, bt_conn, nowcast_csv, out_dir, _db_path(dash_conn))
    summary: dict[str, Any] = {
        "run_at_utc": cache.now.astimezone(UTC).isoformat(),
        "sources": {
            "dash_db": _db_path(dash_conn), "bt_db": _db_path(bt_conn),
            "bars": "Dukascopy BID, INTERVAL_SEC_1 (INTERVAL_MIN_1 fallback)",
            "since": since.isoformat(), "until": until.isoformat(),
            "baseline_quantile": REACTION_BASELINE_QUANTILE,
        },
        "sample": sample,
        "coverage": _coverage(measured),
        "magnitudes": {s: groups.magnitude_table(all_rows, s) for s in SYMBOLS},
        "pullbacks": {s: groups.pullback_table(all_rows, s) for s in SYMBOLS},
        "conflicts": conflicts,
        "peaks": {s: groups.peak_distribution(all_rows, s) for s in SYMBOLS},
        "chain": _chain_block(rows_by_symbol, clusters),
        "dipstick": dipstick,
        "fetch": {"network_requests": cache.network_requests, "cache_hits": cache.cache_hits,
                  "errors": cache.errors},
    }

    _write_csv(out_dir / "releases.csv", list(RELEASE_ROW_KEYS), all_rows)
    _write_csv(out_dir / "members.csv", MEMBER_COLUMNS, member_rows)
    _write_csv(out_dir / "conflicts.csv", list(groups.CONFLICT_DETAIL_KEYS),
               [_flatten_conflict(d) for d in conflicts])
    _write_csv(out_dir / "dipstick.csv", list(checks.DIPSTICK_KEYS), dip_rows)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    (out_dir / "summary.md").write_text(render_markdown(summary), encoding="utf-8")
    return summary


# =============================================================================================
# Markdown
# =============================================================================================

def _num(value: Any, digits: int = 2) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _spread(s: Optional[dict[str, Any]]) -> str:
    """'median (p25-p75)' of a summarize() dict, '-' when empty."""
    if not s or not s.get("n"):
        return "-"
    return f"{_num(s['median'])} ({_num(s['p25'])}-{_num(s['p75'])})"


def _table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(_num(c) for c in row) + " |" for row in rows]
    return lines + [""]


def render_markdown(summary: dict[str, Any]) -> str:
    """One table per summary block, every table with an n column; times in SAST."""
    out: list[str] = ["# B5 event study - summary", ""]
    if "run_at_utc" in summary:
        out += [f"Run at {summary['run_at_utc']} (UTC). Owner-facing times below are SAST.", ""]
    sample = summary.get("sample")
    if sample:
        out += ["## Sample", "",
                f"minutes {sample['minutes']}, with 2+ events {sample['minutes_multi']}, "
                f"High-impact {sample['high_minutes']}, not yet studyable {sample['pending_minutes']}.", ""]
        out += _table(["class", "n"], [[k, v] for k, v in sample["classes"].items()])
        out += _table(["fully computable multi-member", "n"],
                      [[k, v] for k, v in sample["fully_computable_multi"].items()])
    if "coverage" in summary:
        out += ["## Coverage", ""]
        out += _table(["series", "n", "ok", "no_data", "sec1", "min1", "none"],
                      [[s, c["n"], c["ok"], c["no_data"], c["sec1"], c["min1"], c["none"]]
                       for s, c in summary["coverage"].items()])
    for symbol, table in summary.get("magnitudes", {}).items():
        out += [f"## Magnitudes - {symbol} (baseline multiples, median (p25-p75))", ""]
        out += _table(
            ["class", "n", "n_30", "peak_1_x", "peak_5_x", "peak_30_x", "|net_5|_x", "|net_30|_x",
             "dir_net_30_x", "hit_30 (hits/n)"],
            [[cls, e["peak_1_x"]["n"], e["peak_30_x"]["n"], _spread(e["peak_1_x"]), _spread(e["peak_5_x"]),
              _spread(e["peak_30_x"]), _spread(e["abs_net_5_x"]), _spread(e["abs_net_30_x"]),
              _spread(e["dir_net_30_x"]), f"{e['implied_hit_30']['hits']}/{e['implied_hit_30']['n']}"]
             for cls, e in table.items()])
    for symbol, table in summary.get("pullbacks", {}).items():
        out += [f"## Spike then pull back - {symbol}", ""]
        out += _table(["class", "n", "n_5", "pullback_5", "n_30", "pullback_30"],
                      [[cls, e["n_first_dir"], e["n_5"], e["spike_pullback_5"], e["n_30"],
                        e["spike_pullback_30"]] for cls, e in table.items()])
    conflicts = summary.get("conflicts")
    if conflicts is not None:
        out += ["## Conflicting clusters (SAST)", ""]
        out += _table(
            ["t_sast", "symbol", "n", "members", "first_dir", "net_5", "net_30", "first followed",
             "net30 followed", "pullback_5", "pullback_30"],
            [[d["t_sast"], d["symbol"], len(d["members"]),
              "; ".join(f"{m['title']} ({m['impact']}, {_num(m['instrument_dir'])})" for m in d["members"]),
              d["first_min_dir"], d["net_5_sign"], d["net_30_sign"], " | ".join(d["first_followed"] or []) or "-",
              " | ".join(d["net30_followed"] or []) or "-", d["spike_pullback_5"], d["spike_pullback_30"]]
             for d in conflicts])
    for symbol, groups_ in summary.get("peaks", {}).items():
        unit = "$" if symbol == "XAUUSD" else "points"
        out += [f"## 1-minute peak - {symbol} ({unit})", ""]
        out += _table(["group", "n", "median", "p25", "p75", "p90", "max", "ttp_1 median s", "ttp_30 median s"],
                      [[g, e["peak_1"]["n"], e["peak_1"]["median"], e["peak_1"]["p25"], e["peak_1"]["p75"],
                        e["peak_1"]["p90"], e["peak_1"]["max"], e["ttp_1_s"]["median"], e["ttp_30_s"]["median"]]
                       for g, e in groups_.items()])
        if symbol == "XAUUSD":
            names = [name for name, _lo, _hi in groups.PEAK_BANDS]
            out += _table(["group", "n"] + names,
                          [[g, e["peak_1"]["n"]] + [e["bands"][name] for name in names]
                           for g, e in groups_.items()])
    chain = summary.get("chain")
    if chain:
        out += ["## E2 chain (DXY 5-minute move)", ""]
        out += _table(["event USD dir vs DXY: threshold bp", "n", "n_match", "share"],
                      [[th, e["n"], e["n_match"], e["share"]] for th, e in chain["event_usd"].items()])
        out += _table(["symbol", "threshold bp", "n", "n_agree", "share"],
                      [[s, th, e["n"], e["n_agree"], e["share"]]
                       for s, ths in chain["usd_instrument"].items() for th, e in ths.items()])
        out += _table(["symbol", "measure", "n", "slope", "intercept", "r"],
                      [[s, kind, fit["n"] if fit else 0, fit["slope"] if fit else None,
                        fit["intercept"] if fit else None, fit["r"] if fit else None]
                       for s, fits in chain["ols"].items() for kind, fit in fits.items()])
    dip = summary.get("dipstick")
    if dip:
        out += ["## E3 Cleveland nowcast dipstick", ""]
        if dip["status"] != "ok":
            out += [f"Nowcast history {dip['status']}: {dip['nowcast_csv']}. To regenerate: {dip['regenerate']}", ""]
        else:
            out += _table(["lag_days", "n", "final_closer", "early_closer", "ties", "early_equals_final",
                           "side_changed", "early_hits", "final_hits"],
                          [[lag, e["n"], e["final_closer"], e["early_closer"], e["ties"], e["early_equals_final"],
                            e["side_changed"], e["early_hits"], e["final_hits"]]
                           for lag, e in dip["per_lag"].items()])
            out += _table(["check", "n", "equal"],
                          [["T-5d equals final", dip["t5_equals_final"]["n"], dip["t5_equals_final"]["equal"]],
                           ["final equals stored snapshot", dip["snapshot_check"]["n"],
                            dip["snapshot_check"]["equal"]]])
    fetch = summary.get("fetch")
    if fetch:
        out += ["## Fetch", ""]
        out += _table(["counter", "n"], [[k, v] for k, v in fetch.items()])
    return "\n".join(out)


# =============================================================================================
# CLI
# =============================================================================================

def _parse_day(text: str) -> dt.datetime:
    return dt.datetime.fromisoformat(text).replace(tzinfo=UTC)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="B5 read-only event study (see the module docstring).")
    parser.add_argument("--dash-db", type=Path, default=LIVE_DASH_DB)
    parser.add_argument("--bt-db", type=Path, default=LIVE_BT_DB)
    parser.add_argument("--nowcast-csv", type=Path, default=DEFAULT_NOWCAST_CSV)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--since", default=START.strftime("%Y-%m-%d"), help="first release day (UTC)")
    parser.add_argument("--limit", type=int, default=None, help="study only the first N release minutes")
    parser.add_argument("--pause", type=float, default=DEFAULT_PAUSE_S, help="seconds between Dukascopy requests")
    parser.add_argument("--dry-run", action="store_true", help="fetch nothing; print the sample block only")
    parser.add_argument("--offline", action="store_true", help="use the bar cache only, never the network")
    args = parser.parse_args(argv)

    try:
        assert_outside_repo(args.out_dir)
    except ValueError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    try:
        dash_conn = open_readonly(args.dash_db)
        try:
            bt_conn = open_readonly(args.bt_db)
        except FileNotFoundError:
            dash_conn.close()
            raise
    except FileNotFoundError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    now = dt.datetime.now(UTC)
    try:
        cache = BarCache(args.out_dir, dukascopy_fetch, now, pause_s=args.pause, offline=args.offline)
        summary = run_study(dash_conn, bt_conn, cache, args.nowcast_csv, args.out_dir, _parse_day(args.since), now,
                            limit=args.limit, dry_run=args.dry_run)
    finally:
        dash_conn.close()
        bt_conn.close()
    print(render_markdown(summary))
    if not args.dry_run:
        print(f"\nOutputs written to {args.out_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
