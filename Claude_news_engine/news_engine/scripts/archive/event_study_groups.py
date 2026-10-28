"""
B5 event study - release members, same-minute clusters, implied directions and group summaries
(pure; no I/O, no network, no DB).

Plan: docs/superpowers/plans/2026-10-21-b5-event-study.md (Task 2). Uses the window measures of
scripts/archive/event_study_metrics.py; consumed by scripts/archive/event_study_once.py; unit-tested in
tests/test_event_study_groups.py.

Rules:
  * Members: USD event_history rows. Same-title rows within DUPLICATE_WITHIN of the earliest row of
    their run are one release listed twice and collapse to that earliest row
    (reaction_rules.collapse_same_title_duplicates, as compute_release_reactions does). When the kept
    row has no readable forecast/actual, the first row of the same run that has both supplies them,
    so a calendar re-stamp never loses a direction.
  * Implied directions: actual vs forecast by the Stats tolerance rule (one rounding step of the
    forecast's own precision) -> EVENT_SURPRISE_DIRECTION -> USD up (+1) / down (-1) / in line (0);
    stats_methods.market_lean -> instrument buy (+1) / sell (-1). An unreadable number or an unmapped
    title is None (unknown), never "in line".
  * Cluster classes (market_reaction_phase0.classify_cluster semantics on USD direction; in-line
    members do not vote): size 1 -> single_directional / single_in_line / single_unknown; size 2+ ->
    partial (any member unknown), all_in_line, conflict (+1 and -1 both present), agree. all_same marks
    an agree cluster where EVERY member moved the same way (the owner's literal "all hot / all cool").
  * Impact per minute: the highest member impact (High > Medium > Low > Unknown), row impact first,
    EVENT_REGISTRY when the row has none.
  * Contamination: a row enters horizon-k statistics only when the next release minute is at least k
    minutes after t (usable()); every table below applies it per horizon.
"""
from __future__ import annotations

import datetime as dt
import statistics
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Optional

# Make `python scripts/...` work from the app dir (repo root on sys.path).
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from config.settings import EVENT_REGISTRY, EVENT_SURPRISE_DIRECTION, LOCAL_TZ  # noqa: E402
from data_layer.minute_bars import quantile  # noqa: E402
from scripts.archive.event_study_metrics import METRIC_KEYS, baseline_multiple, owner_units  # noqa: E402
from webapp import stats_rules  # noqa: E402
from webapp.reaction_rules import DUPLICATE_WITHIN, collapse_same_title_duplicates  # noqa: E402
from webapp.stats_methods import market_lean  # noqa: E402

UTC = dt.timezone.utc

IMPACT_RANK: dict[str, int] = {"High": 3, "Medium": 2, "Low": 1, "Unknown": 0}
STEPS_DECIMALS = 9          # surprise steps rounded so 0.4 - 0.3 over 0.1 is exactly 1.0 (ties compare)

# Table order: the directional classes the questions are about first, then the controls / leftovers.
CLASS_ORDER: tuple[str, ...] = (
    "single_directional", "agree", "agree_all_same", "conflict",
    "single_in_line", "all_in_line", "partial", "single_unknown",
)
DIRECTIONAL_CLASSES = ("single_directional", "agree")
IMPACT_GROUPS: tuple[str, ...] = ("High", "others")

# XAUUSD 1-minute peak bands in $ (lower bound inclusive), against "$5-10 typical, $15-20 max".
PEAK_BANDS: tuple[tuple[str, float, float], ...] = (
    ("lt5", float("-inf"), 5.0),
    ("5_10", 5.0, 10.0),
    ("10_15", 10.0, 15.0),
    ("15_20", 15.0, 20.0),
    ("20_plus", 20.0, float("inf")),
)

RELEASE_ROW_KEYS: tuple[str, ...] = (
    "t_utc", "t_sast", "symbol", "n_members", "titles", "cluster_class", "all_same", "impact",
    "implied_dir", "baseline", "next_release_gap_min",
) + METRIC_KEYS + (
    "peak_1_x", "peak_5_x", "peak_30_x", "abs_net_5_x", "abs_net_30_x", "dir_net_30_x",
    "peak_1_owner", "peak_5_owner", "peak_30_owner", "owner_unit",
    "dxy_bar_source", "dxy_p0", "dxy_net_5", "dxy_net_30",
)

CONFLICT_DETAIL_KEYS: tuple[str, ...] = (
    "t_sast", "symbol", "members", "first_min_dir", "net_5_sign", "net_30_sign",
    "first_followed", "net30_followed", "largest_surprise_title", "first_followed_largest",
    "net30_followed_largest", "highest_impact_title", "net30_followed_highest_impact",
    "spike_pullback_5", "spike_pullback_30",
)

SUMMARY_KEYS: tuple[str, ...] = ("n", "mean", "p25", "median", "p75", "p90", "max")


# =============================================================================================
# Members and implied directions
# =============================================================================================

@dataclass(frozen=True)
class Member:
    """One USD release row (after the duplicate collapse); `when_utc` is aware UTC."""
    title: str
    when_utc: dt.datetime
    forecast: Optional[str]
    actual: Optional[str]
    impact: Optional[str]

    def __post_init__(self) -> None:
        # Same test as compute_release_reactions._aware_utc; no conversion, a naive value is a caller bug.
        if self.when_utc.tzinfo is None or self.when_utc.utcoffset() is None:
            raise ValueError(f"when_utc must be timezone-aware, got naive {self.when_utc!r}")


def _readable(m: Member) -> bool:
    return stats_rules.parse_number(m.forecast) is not None and stats_rules.parse_number(m.actual) is not None


def collapse_members(rows: list[Member]) -> list[Member]:
    """Same-title duplicates within DUPLICATE_WITHIN collapse to the earliest row of their run.

    The kept rows are exactly those of reaction_rules.collapse_same_title_duplicates. A kept row
    without a readable forecast AND actual takes both from the first row of its run that has them
    (impact stays the kept row's). Returned sorted by (time, title).
    """
    kept_keys = collapse_same_title_duplicates([(r.title, r.when_utc) for r in rows])
    by_title: dict[str, list[Member]] = {}
    for r in sorted(rows, key=lambda r: r.when_utc):        # stable: input order breaks time ties
        by_title.setdefault(r.title, []).append(r)
    out: list[Member] = []
    for title, anchor in kept_keys:
        run = [r for r in by_title[title] if anchor <= r.when_utc <= anchor + DUPLICATE_WITHIN]
        kept = next(r for r in run if r.when_utc == anchor)
        if not _readable(kept):
            donor = next((r for r in run if _readable(r)), None)
            if donor is not None:
                kept = replace(kept, forecast=donor.forecast, actual=donor.actual)
        out.append(kept)
    return out


def _numbers(m: Member) -> Optional[tuple[float, float, float]]:
    """(actual, forecast, tolerance) or None when any is unreadable."""
    actual = stats_rules.parse_number(m.actual)
    forecast = stats_rules.parse_number(m.forecast)
    tol = stats_rules.tolerance(m.forecast)
    if actual is None or forecast is None or tol is None:
        return None
    return actual, forecast, tol


def surprise_side(m: Member) -> Optional[int]:
    """+1 above forecast, -1 below, 0 in line (Stats tolerance rule); None when unreadable."""
    numbers = _numbers(m)
    if numbers is None:
        return None
    actual, forecast, tol = numbers
    return stats_rules.side(actual, forecast, tol)


def surprise_steps(m: Member) -> Optional[float]:
    """|actual - forecast| in rounding steps of the forecast (0.5 vs 0.3 -> 2.0); None when unreadable."""
    numbers = _numbers(m)
    if numbers is None:
        return None
    actual, forecast, tol = numbers
    return round(abs(actual - forecast) / tol, STEPS_DECIMALS)


def usd_direction(m: Member) -> Optional[int]:
    """+1 USD up, -1 USD down, 0 in line; None when the side is unknown or the title is unmapped."""
    side = surprise_side(m)
    mapping = EVENT_SURPRISE_DIRECTION.get(m.title)
    if side is None or mapping is None:
        return None
    if side == 0:
        return 0
    return 1 if (side > 0) == (mapping == "higher_bullish") else -1


def instrument_direction(m: Member, symbol: str) -> Optional[int]:
    """+1 buy / -1 sell / 0 in line for `symbol` (stats_methods.market_lean); None when unknown or mixed."""
    usd = usd_direction(m)
    if usd is None or usd == 0:
        return usd
    lean = market_lean(m.title, surprise_side(m), symbol)
    return {"buy": 1, "sell": -1}.get(lean)


def effective_impact(m: Member) -> str:
    """'High' / 'Medium' / 'Low' / 'Unknown': the row's impact (any case), else EVENT_REGISTRY."""
    for raw in (m.impact, (EVENT_REGISTRY.get(m.title) or {}).get("impact")):
        if raw:
            label = str(raw).strip().capitalize()
            if label in IMPACT_RANK and label != "Unknown":
                return label
    return "Unknown"


# =============================================================================================
# Same-minute clusters
# =============================================================================================

@dataclass(frozen=True)
class Cluster:
    """Every member released in one UTC minute (`minute` has seconds dropped)."""
    minute: dt.datetime
    members: tuple[Member, ...]


def build_clusters(members: list[Member]) -> list[Cluster]:
    """Members grouped by UTC minute (seconds dropped); clusters by minute, members by (time, title)."""
    groups: dict[dt.datetime, list[Member]] = {}
    for m in members:
        minute = m.when_utc.astimezone(UTC).replace(second=0, microsecond=0)
        groups.setdefault(minute, []).append(m)
    return [Cluster(minute, tuple(sorted(groups[minute], key=lambda m: (m.when_utc, m.title))))
            for minute in sorted(groups)]


def cluster_class(c: Cluster) -> str:
    """See the module docstring: single_* for one member, else partial / all_in_line / conflict / agree."""
    dirs = [usd_direction(m) for m in c.members]
    if len(dirs) == 1:
        d = dirs[0]
        if d is None:
            return "single_unknown"
        return "single_in_line" if d == 0 else "single_directional"
    if any(d is None for d in dirs):
        return "partial"
    voting = {d for d in dirs if d != 0}
    if not voting:
        return "all_in_line"
    return "conflict" if len(voting) > 1 else "agree"


def all_same(c: Cluster) -> bool:
    """An agree cluster in which every member is hot (or every member cool): no in-line member."""
    if cluster_class(c) != "agree":
        return False
    return len({usd_direction(m) for m in c.members}) == 1


def cluster_impact(c: Cluster) -> str:
    """The highest member impact (High > Medium > Low > Unknown)."""
    return max((effective_impact(m) for m in c.members), key=lambda label: IMPACT_RANK[label])


def cluster_instrument_direction(c: Cluster, symbol: str) -> Optional[int]:
    """The common non-zero instrument direction of a single_directional / agree cluster, else None."""
    if cluster_class(c) not in DIRECTIONAL_CLASSES:
        return None
    dirs = {instrument_direction(m, symbol) for m in c.members if usd_direction(m)}
    if len(dirs) != 1:
        return None
    d = dirs.pop()
    return d if d in (1, -1) else None


def next_release_gap_min(minute: dt.datetime, all_minutes: list[dt.datetime]) -> Optional[float]:
    """Minutes from `minute` to the next later release minute; None when there is none."""
    later = [m for m in all_minutes if m > minute]
    if not later:
        return None
    return (min(later) - minute).total_seconds() / 60.0


# =============================================================================================
# Release rows
# =============================================================================================

def _sast(when: dt.datetime) -> str:
    return f"{when.astimezone(LOCAL_TZ):%Y-%m-%d %H:%M} SAST"


def _abs(value: Optional[float]) -> Optional[float]:
    return None if value is None else abs(value)


def build_release_row(c: Cluster, symbol: str, metrics: dict[str, Any], baseline: Optional[float],
                      gap_min: Optional[float], dxy: dict[str, Any]) -> dict[str, Any]:
    """One CSV row per (release minute, symbol); keys exactly RELEASE_ROW_KEYS.

    `_x` columns are baseline multiples (value / the UTC-hour typical |5-min move|); dir_net_30_x is
    the 30-min net signed by the implied direction (positive = moved the implied way). `_owner`
    columns are the peaks in the owner's units (gold pips, US30 points). `dxy` is DXY's
    measure_window output for the same minute ({} when not measured).
    """
    implied = cluster_instrument_direction(c, symbol)
    row: dict[str, Any] = {
        "t_utc": c.minute.astimezone(UTC).isoformat(),
        "t_sast": _sast(c.minute),
        "symbol": symbol,
        "n_members": len(c.members),
        "titles": " | ".join(m.title for m in c.members),
        "cluster_class": cluster_class(c),
        "all_same": all_same(c),
        "impact": cluster_impact(c),
        "implied_dir": implied,
        "baseline": baseline,
        "next_release_gap_min": gap_min,
    }
    for key in METRIC_KEYS:
        row[key] = metrics.get(key)
    for k in (1, 5, 30):
        row[f"peak_{k}_x"] = baseline_multiple(metrics.get(f"peak_{k}"), baseline)
    for k in (5, 30):
        row[f"abs_net_{k}_x"] = baseline_multiple(_abs(metrics.get(f"net_{k}")), baseline)
    net_30 = metrics.get("net_30")
    row["dir_net_30_x"] = (baseline_multiple(implied * net_30, baseline)
                           if implied is not None and net_30 is not None else None)
    for k in (1, 5, 30):
        peak = metrics.get(f"peak_{k}")
        row[f"peak_{k}_owner"] = None if peak is None else owner_units(symbol, peak)[0]
    row["owner_unit"] = owner_units(symbol, 0.0)[1]
    row["dxy_bar_source"] = dxy.get("bar_source")
    row["dxy_p0"] = dxy.get("p0")
    row["dxy_net_5"] = dxy.get("net_5")
    row["dxy_net_30"] = dxy.get("net_30")
    return row


# =============================================================================================
# Group summaries
# =============================================================================================

def summarize(values: list[float]) -> dict[str, Optional[float]]:
    """n, mean, p25, median, p75, p90, max (linear-interpolated quantiles); all None but n when empty."""
    if not values:
        return {key: (0 if key == "n" else None) for key in SUMMARY_KEYS}
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "p25": quantile(values, 0.25),
        "median": quantile(values, 0.5),
        "p75": quantile(values, 0.75),
        "p90": quantile(values, 0.9),
        "max": max(values),
    }


def usable(row: dict[str, Any], k_min: int) -> bool:
    """Measured, and no other release minute inside [t, t + k_min) (contamination rule)."""
    gap = row.get("next_release_gap_min")
    return row.get("status") == "ok" and (gap is None or gap >= k_min)


def _class_rows(rows: list[dict[str, Any]], symbol: str, cls: str) -> list[dict[str, Any]]:
    """The symbol's rows of one table class; agree_all_same is the all_same subset of agree."""
    mine = [r for r in rows if r.get("symbol") == symbol]
    if cls == "agree_all_same":
        return [r for r in mine if r.get("cluster_class") == "agree" and r.get("all_same")]
    return [r for r in mine if r.get("cluster_class") == cls]


def _values(rows: list[dict[str, Any]], key: str, k_min: int) -> list[float]:
    return [r[key] for r in rows if usable(r, k_min) and r.get(key) is not None]


def _sign(x: float) -> int:
    return (x > 0) - (x < 0)


# measure -> horizon it belongs to (its contamination window)
_MAGNITUDE_MEASURES: tuple[tuple[str, int], ...] = (
    ("peak_1_x", 1), ("peak_5_x", 5), ("peak_30_x", 30),
    ("abs_net_5_x", 5), ("abs_net_30_x", 30), ("dir_net_30_x", 30),
)


def magnitude_table(rows: list[dict[str, Any]], symbol: str) -> dict[str, dict]:
    """Per class: summaries of the baseline-multiple measures plus the 30-min implied-direction hit rate.

    Each measure only over rows usable at its horizon. implied_hit_30: rows with an implied direction
    and a 30-min net; a hit is sign(net_30) == implied_dir (a zero net is a miss).
    """
    table: dict[str, dict] = {}
    for cls in CLASS_ORDER:
        mine = _class_rows(rows, symbol, cls)
        entry: dict[str, Any] = {key: summarize(_values(mine, key, k)) for key, k in _MAGNITUDE_MEASURES}
        judged = [r for r in mine if usable(r, 30) and r.get("implied_dir") in (1, -1)
                  and r.get("net_30") is not None]
        hits = sum(1 for r in judged if _sign(r["net_30"]) == r["implied_dir"])
        entry["implied_hit_30"] = {"n": len(judged), "hits": hits}
        table[cls] = entry
    return table


def pullback_table(rows: list[dict[str, Any]], symbol: str) -> dict[str, dict]:
    """Per class: rows with a first-minute direction, and per horizon k (5, 30) the rows judged
    (spike flag present, usable at k) and how many of them spiked then pulled back."""
    table: dict[str, dict] = {}
    for cls in CLASS_ORDER:
        mine = _class_rows(rows, symbol, cls)
        entry: dict[str, int] = {
            "n_first_dir": sum(1 for r in mine if usable(r, 1) and r.get("first_min_dir") in (1, -1)),
        }
        for k in (5, 30):
            judged = [r for r in mine if usable(r, k) and r.get(f"spike_pullback_{k}") is not None]
            entry[f"n_{k}"] = len(judged)
            entry[f"spike_pullback_{k}"] = sum(1 for r in judged if r[f"spike_pullback_{k}"])
        table[cls] = entry
    return table


def _unique_top(scored: list[tuple[str, float]]) -> Optional[str]:
    """The title with the strictly highest score; None when empty or the top is tied."""
    if not scored:
        return None
    best = max(score for _title, score in scored)
    top = [title for title, score in scored if score == best]
    return top[0] if len(top) == 1 else None


def _followed(members: list[dict[str, Any]], direction: Optional[int]) -> Optional[list[str]]:
    """Titles whose instrument direction matches `direction`; None when there is no direction to follow."""
    if direction not in (1, -1):
        return None
    return [m["title"] for m in members if m["instrument_dir"] == direction]


def _in(title: Optional[str], titles: Optional[list[str]]) -> Optional[bool]:
    return None if title is None or titles is None else title in titles


def conflict_detail(c: Cluster, row: dict[str, Any], symbol: str) -> dict[str, Any]:
    """Who the price followed in one conflicting cluster; keys exactly CONFLICT_DETAIL_KEYS.

    Only directional members (instrument direction +1/-1) are candidates. The net/pull-back fields
    at k are None when the row is not usable at k (another release inside [t, t + k)), so a
    contaminated net never credits a member. largest_surprise_title / highest_impact_title are None
    on a tie (no single "winner" for the mover rules to check).
    """
    members = [{"title": m.title, "impact": effective_impact(m),
                "instrument_dir": instrument_direction(m, symbol), "surprise_steps": surprise_steps(m)}
               for m in c.members]
    directional = [m for m in members if m["instrument_dir"] in (1, -1)]

    first_dir = row.get("first_min_dir") if usable(row, 1) else None
    net_sign: dict[int, Optional[int]] = {}
    for k in (5, 30):
        net = row.get(f"net_{k}")
        net_sign[k] = _sign(net) if usable(row, k) and net is not None else None

    first_followed = _followed(directional, first_dir)
    net30_followed = _followed(directional, net_sign[30])
    largest = _unique_top([(m["title"], m["surprise_steps"]) for m in directional
                           if m["surprise_steps"] is not None])
    highest = _unique_top([(m["title"], float(IMPACT_RANK[m["impact"]])) for m in directional])
    return {
        "t_sast": _sast(c.minute),
        "symbol": symbol,
        "members": members,
        "first_min_dir": first_dir,
        "net_5_sign": net_sign[5],
        "net_30_sign": net_sign[30],
        "first_followed": first_followed,
        "net30_followed": net30_followed,
        "largest_surprise_title": largest,
        "first_followed_largest": _in(largest, first_followed),
        "net30_followed_largest": _in(largest, net30_followed),
        "highest_impact_title": highest,
        "net30_followed_highest_impact": _in(highest, net30_followed),
        "spike_pullback_5": row.get("spike_pullback_5") if usable(row, 5) else None,
        "spike_pullback_30": row.get("spike_pullback_30") if usable(row, 30) else None,
    }


def peak_distribution(rows: list[dict[str, Any]], symbol: str) -> dict[str, dict]:
    """Per impact group (High / others): peak_1 and peak_5 ($ or points), ttp_1_s and ttp_30_s, each
    over rows usable at its horizon; XAUUSD also gets the $ band counts of peak_1 (PEAK_BANDS)."""
    out: dict[str, dict] = {}
    for group in IMPACT_GROUPS:
        mine = [r for r in rows if r.get("symbol") == symbol
                and (r.get("impact") == "High") == (group == "High")]
        entry: dict[str, Any] = {
            "peak_1": summarize(_values(mine, "peak_1", 1)),
            "peak_5": summarize(_values(mine, "peak_5", 5)),
            "ttp_1_s": summarize(_values(mine, "ttp_1_s", 1)),
            "ttp_30_s": summarize(_values(mine, "ttp_30_s", 30)),
        }
        if symbol == "XAUUSD":
            peaks = _values(mine, "peak_1", 1)
            entry["bands"] = {name: sum(1 for p in peaks if lo <= p < hi) for name, lo, hi in PEAK_BANDS}
        out[group] = entry
    return out
