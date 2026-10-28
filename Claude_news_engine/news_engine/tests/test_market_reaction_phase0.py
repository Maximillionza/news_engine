"""Pure-helper tests for scripts/market_reaction_phase0.py (synthetic data only; no network, no DB)."""
import datetime as dt

from scripts import market_reaction_phase0 as p0

UTC = dt.timezone.utc


def _t(day: int, hour: int, minute: int) -> dt.datetime:
    return dt.datetime(2026, 3, day, hour, minute, tzinfo=UTC)


# ---- gap detection ---------------------------------------------------------------------------

def test_find_gaps_reports_missing_start_end_or_both():
    releases = [_t(2, 12, 30), _t(2, 13, 30), _t(2, 14, 0), _t(2, 15, 0)]
    bars = {
        _t(2, 12, 30), _t(2, 12, 35),   # both present
        _t(2, 13, 30),                  # t+5 missing
        _t(2, 14, 5),                   # t missing
        # 15:00 / 15:05 both missing
    }
    gaps = p0.find_gaps(releases, bars)
    assert [(g.minute, g.missing) for g in gaps] == [
        (_t(2, 13, 30), ("t+5",)),
        (_t(2, 14, 0), ("t",)),
        (_t(2, 15, 0), ("t", "t+5")),
    ]


def test_find_gaps_empty_when_all_covered():
    assert p0.find_gaps([_t(2, 12, 30)], {_t(2, 12, 30), _t(2, 12, 35)}) == []


def test_coverage_counts_releases_with_both_bars():
    releases = [_t(2, 12, 30), _t(2, 13, 30)]
    gaps = p0.find_gaps(releases, {_t(2, 12, 30), _t(2, 12, 35), _t(2, 13, 30)})
    assert p0.coverage(releases, gaps) == (1, 2)


# ---- cluster-size bucketing --------------------------------------------------------------------

def test_cluster_bucket_edges():
    assert [p0.cluster_bucket(n) for n in (1, 2, 3, 4, 9)] == ["1", "2", "3+", "3+", "3+"]


def test_group_clusters_counts_events_per_exact_minute():
    events = [("A", _t(2, 12, 30)), ("B", _t(2, 12, 30)), ("C", _t(2, 12, 31)), ("D", _t(2, 14, 0)),
              ("E", _t(2, 14, 0)), ("F", _t(2, 14, 0))]
    clusters = p0.group_clusters(events)
    assert {m: len(titles) for m, titles in clusters.items()} == {
        _t(2, 12, 30): 2, _t(2, 12, 31): 1, _t(2, 14, 0): 3}


def test_classify_cluster_solo_agree_conflict_none():
    assert p0.classify_cluster(["mixed", "mixed"]) == "no_signal"
    assert p0.classify_cluster(["buy", "mixed"]) == "solo"
    assert p0.classify_cluster(["buy", "buy", "mixed"]) == "agree"
    assert p0.classify_cluster(["sell", "buy"]) == "conflict"


# ---- overlap-window counting -------------------------------------------------------------------

def test_overlap_windows_flags_release_minutes_inside_the_window():
    minutes = [_t(2, 12, 30), _t(2, 12, 33), _t(2, 13, 0), _t(2, 13, 5), _t(2, 14, 0)]
    over = p0.overlap_windows(minutes)
    # 12:30 window is [12:30, 12:35) -> holds 12:33. 13:00 window is [13:00, 13:05) -> 13:05 is NOT inside.
    assert over == [(_t(2, 12, 30), [_t(2, 12, 33)])]


def test_overlap_windows_none_when_thirty_minutes_apart():
    assert p0.overlap_windows([_t(2, 12, 30), _t(2, 13, 0), _t(2, 13, 30)]) == []


def test_overlap_windows_duplicates_are_one_minute_not_overlap():
    assert p0.overlap_windows([_t(2, 12, 30), _t(2, 12, 30)]) == []


# ---- baselines (the spec_baseline_* tests moved to tests/test_minute_bars.py, B10 C4) ----

def _flat_day(day: int, hour: int, step_value: float) -> dict:
    """One bar per minute for the hour (plus the next 5), open rising by step_value per minute."""
    return {_t(day, hour, 0) + dt.timedelta(minutes=i): 100.0 + step_value * i for i in range(66)}


def test_audit_price_at_takes_next_bar_within_five_minutes_else_none():
    opens = {_t(2, 12, 0): 1.0, _t(2, 12, 3): 2.0}
    assert p0.audit_price_at(opens, _t(2, 12, 0)) == 1.0
    assert p0.audit_price_at(opens, _t(2, 12, 1)) == 2.0          # skips the gap forward, no lookback
    assert p0.audit_price_at(opens, _t(2, 12, 9)) is None         # nothing at/after within range


def test_audit_baseline_uses_quarter_hour_grid_and_does_not_exclude_releases():
    opens = _flat_day(2, 12, 1.0)
    moves = p0.audit_baseline_moves(opens, 12)
    assert len(moves) == 4 and set(moves) == {5.0}


def test_median_even_and_odd():
    assert p0.median([3.0, 1.0, 2.0]) == 2.0
    assert p0.median([1.0, 2.0, 3.0, 4.0]) == 2.5
    assert p0.median([]) is None
