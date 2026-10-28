"""
B5 event study - chain check (E2) and Tier 1 dipstick (E3) helpers (pure; no network, no DB).

Plan: docs/superpowers/plans/2026-10-21-b5-event-study.md (Task 3). Consumed by scripts/archive/event_study_once.py;
unit-tested in tests/test_event_study_checks.py.

  * E2 asks two questions of the 5-minute DXY move after a release: does it follow the release's implied USD
    direction (event_usd_agreement), and do gold / US30 follow the engine's sign for it
    (usd_instrument_agreement; ENGINE_SIGN is -1 for both: gold is inverse to USD, US30 risk_sentiment
    flips like inverse in market_lean). Moves below the basis-point threshold are noise and are left out.
  * E3 compares an early Cleveland Fed nowcast value (lag days before the release) with the final one
    (last stamp strictly before the release instant) against the actual, using the Stats tolerance rule.
"""
from __future__ import annotations

import csv
import datetime as dt
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

# Make `python scripts/...` work from the app dir (repo root on sys.path).
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from config.settings import LOCAL_TZ  # noqa: E402
from webapp import stats_rules  # noqa: E402

UTC = dt.timezone.utc

DXY_THRESHOLDS_BPS: tuple[float, ...] = (0.0, 2.0, 5.0)   # |DXY 5-min move| cut-offs in basis points
HEADLINE_DXY_BPS = 2.0                                     # the threshold the report leads with
ENGINE_SIGN: dict[str, int] = {"XAUUSD": -1, "US30": -1}   # instrument sign per DXY sign the engine assumes

LAGS_DAYS: tuple[int, ...] = (5, 15, 20, 25)               # days before release for the "early" nowcast
HEADLINE_LAG_DAYS = 25                                     # "mid reference month"
TIE_EPS = 1e-12                                            # distances closer than this count as a tie

DIPSTICK_KEYS: tuple[str, ...] = (
    "title", "release_utc", "release_sast", "lag_days", "early", "final", "actual", "forecast",
    "early_equals_final", "closer", "early_side", "final_side", "actual_side", "side_changed",
    "early_hit", "final_hit",
)


def bps(move: Optional[float], p0: Optional[float]) -> Optional[float]:
    """Move as basis points of the starting price; None when either is missing or p0 is not positive."""
    if move is None or p0 is None or p0 <= 0:
        return None
    return move / p0 * 10_000.0


def _sign(value: float) -> int:
    return (value > 0) - (value < 0)


def _share(count: int, n: int) -> Optional[float]:
    return count / n if n else None


def event_usd_agreement(rows: list[tuple[int, Optional[float], Optional[float]]],
                        threshold_bps: float) -> dict[str, Any]:
    """rows = (implied USD dir, dxy_net_5, dxy_p0). Counts only dir +1/-1 with |bps| above the threshold."""
    n = n_match = 0
    for implied, net_5, p0 in rows:
        if implied not in (1, -1):
            continue
        move = bps(net_5, p0)
        if move is None or abs(move) <= threshold_bps:
            continue
        n += 1
        if _sign(move) == implied:
            n_match += 1
    return {"threshold_bps": threshold_bps, "n": n, "n_match": n_match, "share": _share(n_match, n)}


def usd_instrument_agreement(rows: list[tuple[Optional[float], Optional[float], Optional[float]]],
                             engine_sign: int, threshold_bps: float) -> dict[str, Any]:
    """rows = (dxy_net_5, dxy_p0, inst_net_5). Agree when sign(inst) == engine_sign x sign(dxy)."""
    n = n_agree = 0
    for dxy_net, dxy_p0, inst_net in rows:
        move = bps(dxy_net, dxy_p0)
        if move is None or abs(move) <= threshold_bps or not inst_net:   # None and 0.0 both excluded
            continue
        n += 1
        if _sign(inst_net) == engine_sign * _sign(move):
            n_agree += 1
    return {"threshold_bps": threshold_bps, "n": n, "n_agree": n_agree, "share": _share(n_agree, n)}


def ols(xs: list[float], ys: list[float]) -> Optional[dict[str, float]]:
    """Least-squares line y = intercept + slope x with Pearson r. None when n < 3 or x has no variance."""
    n = len(xs)
    if n < 3 or n != len(ys):
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    if sxx == 0:
        return None
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    syy = sum((y - mean_y) ** 2 for y in ys)
    slope = sxy / sxx
    r = sxy / math.sqrt(sxx * syy) if syy > 0 else 0.0
    return {"slope": slope, "intercept": mean_y - slope * mean_x, "r": r, "n": n}


@dataclass(frozen=True)
class NowcastPoint:
    as_of_utc: dt.datetime
    value: float


def _parse_utc(text: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def load_nowcast_csv(path: Path) -> dict[tuple[str, dt.datetime], list[NowcastPoint]]:
    """cleveland_nowcast_to_csv.CSV_COLUMNS file -> {(event_title, release_utc): points sorted by as_of}."""
    out: dict[tuple[str, dt.datetime], list[NowcastPoint]] = {}
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for rec in csv.DictReader(handle):
            key = (rec["event_title"], _parse_utc(rec["release_utc"]))
            out.setdefault(key, []).append(NowcastPoint(_parse_utc(rec["as_of_utc"]), float(rec["value"])))
    for points in out.values():
        points.sort(key=lambda p: p.as_of_utc)
    return out


def value_as_of(points: list[NowcastPoint], cutoff: dt.datetime) -> Optional[float]:
    """Value of the latest point stamped at or before the cutoff."""
    chosen = [p for p in points if p.as_of_utc <= cutoff]
    return max(chosen, key=lambda p: p.as_of_utc).value if chosen else None


def final_value(points: list[NowcastPoint], release: dt.datetime) -> Optional[float]:
    """Value of the latest point stamped strictly before the release instant."""
    chosen = [p for p in points if p.as_of_utc < release]
    return max(chosen, key=lambda p: p.as_of_utc).value if chosen else None


def dipstick_row(title: str, release: dt.datetime, points: list[NowcastPoint], forecast_text: Optional[str],
                 actual_text: Optional[str], lag_days: int) -> dict[str, Any]:
    """One release: early (lag_days before) vs final nowcast against the actual, by the Stats tolerance rule."""
    release = release.astimezone(UTC)
    early = value_as_of(points, release - dt.timedelta(days=lag_days))
    final = final_value(points, release)
    forecast = stats_rules.parse_number(forecast_text)
    actual = stats_rules.parse_number(actual_text)
    tol = stats_rules.tolerance(forecast_text)

    def side_of(value: Optional[float]) -> Optional[int]:
        if value is None or forecast is None or tol is None:
            return None
        return stats_rules.side(value, forecast, tol)

    early_side, final_side, actual_side = side_of(early), side_of(final), side_of(actual)
    closer: Optional[str] = None
    if early is not None and final is not None and actual is not None:
        d_early, d_final = abs(early - actual), abs(final - actual)
        closer = "tie" if abs(d_early - d_final) <= TIE_EPS else ("final" if d_final < d_early else "early")

    def hit(value_side: Optional[int]) -> Optional[bool]:
        return None if value_side is None or actual_side is None else value_side == actual_side

    return {
        "title": title,
        "release_utc": release.isoformat(),
        "release_sast": release.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M SAST"),
        "lag_days": lag_days,
        "early": early,
        "final": final,
        "actual": actual,
        "forecast": forecast,
        "early_equals_final": None if early is None or final is None else abs(early - final) <= TIE_EPS,
        "closer": closer,
        "early_side": early_side,
        "final_side": final_side,
        "actual_side": actual_side,
        "side_changed": None if early_side is None or final_side is None else early_side != final_side,
        "early_hit": hit(early_side),
        "final_hit": hit(final_side),
    }


def summarize_dipstick(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Counts over rows with early, final and actual all present (n)."""
    full = [r for r in rows if r["early"] is not None and r["final"] is not None and r["actual"] is not None]
    return {
        "n": len(full),
        "final_closer": sum(r["closer"] == "final" for r in full),
        "early_closer": sum(r["closer"] == "early" for r in full),
        "ties": sum(r["closer"] == "tie" for r in full),
        "early_equals_final": sum(bool(r["early_equals_final"]) for r in full),
        "side_changed": sum(bool(r["side_changed"]) for r in full),
        "early_hits": sum(bool(r["early_hit"]) for r in full),
        "final_hits": sum(bool(r["final_hit"]) for r in full),
    }
