"""Pure-helper tests for scripts/event_study_groups.py (synthetic members and rows; no network, no DB)."""
import datetime as dt

import pytest

from scripts import event_study_groups as g
from scripts import event_study_metrics as m

UTC = dt.timezone.utc
T = dt.datetime(2026, 3, 12, 12, 30, 0, tzinfo=UTC)


def _m(title: str, forecast, actual, when: dt.datetime = T, impact=None) -> g.Member:
    return g.Member(title=title, when_utc=when, forecast=forecast, actual=actual, impact=impact)


def _cluster(*members: g.Member) -> g.Cluster:
    clusters = g.build_clusters(list(members))
    assert len(clusters) == 1
    return clusters[0]


def _row(**values) -> dict:
    """A release row with every RELEASE_ROW_KEYS key (None unless given)."""
    row = {key: None for key in g.RELEASE_ROW_KEYS}
    row.update(status="ok", symbol="XAUUSD")
    row.update(values)
    return row


CPI_HOT = ("CPI m/m", "0.3", "0.4")
CORE_HOT = ("Core CPI m/m", "0.3", "0.4")
CORE_IN_LINE = ("Core CPI m/m", "0.3", "0.3")
CLAIMS_HIGH = ("Unemployment Claims", "220K", "230K")


# ---- duplicate collapse ----------------------------------------------------------------------

def test_duplicate_within_3_minutes_collapses_and_keeps_actual():
    rows = [
        _m("CPI m/m", "0.3", None, T),
        _m("CPI m/m", "0.3", "0.4", T + dt.timedelta(minutes=2)),
        _m("CPI m/m", "0.3", "0.5", T + dt.timedelta(minutes=4)),
    ]
    kept = g.collapse_members(rows)
    assert len(kept) == 2
    first, second = kept
    assert first.when_utc == T and first.actual == "0.4" and first.forecast == "0.3"
    assert second.when_utc == T + dt.timedelta(minutes=4) and second.actual == "0.5"


def test_collapse_keeps_earliest_row_values_when_readable():
    rows = [
        _m("CPI m/m", "0.3", "0.6", T + dt.timedelta(minutes=1)),
        _m("CPI m/m", "0.2", "0.2", T),
    ]
    kept = g.collapse_members(rows)
    assert kept == [_m("CPI m/m", "0.2", "0.2", T)]


# ---- directions --------------------------------------------------------------------------------

def test_directions_cpi_and_claims():
    cpi = _m(*CPI_HOT)
    assert g.surprise_side(cpi) == 1
    assert g.usd_direction(cpi) == 1
    assert g.instrument_direction(cpi, "XAUUSD") == -1
    assert g.instrument_direction(cpi, "US30") == -1
    assert g.surprise_steps(cpi) == pytest.approx(1.0)

    claims = _m(*CLAIMS_HIGH)
    assert g.surprise_side(claims) == 1
    assert g.usd_direction(claims) == -1
    assert g.instrument_direction(claims, "XAUUSD") == 1

    flat = _m("CPI m/m", "0.3", "0.3")
    assert g.surprise_side(flat) == 0
    assert g.usd_direction(flat) == 0
    assert g.instrument_direction(flat, "XAUUSD") == 0
    assert g.instrument_direction(flat, "US30") == 0
    assert g.surprise_steps(flat) == 0.0


def test_unreadable_numbers_give_no_direction():
    missing = _m("CPI m/m", "0.3", None)
    assert g.surprise_side(missing) is None
    assert g.surprise_steps(missing) is None
    assert g.usd_direction(missing) is None
    assert g.instrument_direction(missing, "XAUUSD") is None


# ---- clusters ----------------------------------------------------------------------------------

def test_cluster_classes():
    conflict = _cluster(_m(*CPI_HOT), _m(*CLAIMS_HIGH))
    assert g.cluster_class(conflict) == "conflict"
    assert g.all_same(conflict) is False

    agree_mixed = _cluster(_m(*CPI_HOT), _m(*CORE_IN_LINE))
    assert g.cluster_class(agree_mixed) == "agree"
    assert g.all_same(agree_mixed) is False

    agree_all = _cluster(_m(*CPI_HOT), _m(*CORE_HOT))
    assert g.cluster_class(agree_all) == "agree"
    assert g.all_same(agree_all) is True
    assert g.cluster_instrument_direction(agree_all, "XAUUSD") == -1

    in_line = _cluster(_m("CPI m/m", "0.3", "0.3"), _m(*CORE_IN_LINE))
    assert g.cluster_class(in_line) == "all_in_line"
    assert g.cluster_instrument_direction(in_line, "XAUUSD") is None

    single = _cluster(_m(*CPI_HOT))
    assert g.cluster_class(single) == "single_directional"
    assert g.cluster_instrument_direction(single, "US30") == -1
    assert g.cluster_class(_cluster(_m("CPI m/m", "0.3", "0.3"))) == "single_in_line"
    assert g.cluster_instrument_direction(conflict, "XAUUSD") is None


def test_unmapped_title_is_partial_not_in_line():
    unmapped = _m("Some Unmapped Index", "50.1", "50.1")
    assert g.usd_direction(unmapped) is None
    assert g.cluster_class(_cluster(_m(*CPI_HOT), unmapped)) == "partial"
    assert g.cluster_class(_cluster(unmapped)) == "single_unknown"


def test_build_clusters_groups_by_utc_minute_and_sorts():
    later = T + dt.timedelta(minutes=90)
    clusters = g.build_clusters([
        _m(*CLAIMS_HIGH, when=later),
        _m(*CPI_HOT, when=T + dt.timedelta(seconds=20)),
        _m(*CORE_HOT, when=T),
    ])
    assert [c.minute for c in clusters] == [T, later]
    assert [mem.title for mem in clusters[0].members] == ["Core CPI m/m", "CPI m/m"]


def test_effective_impact_falls_back_to_registry():
    assert g.effective_impact(_m("Non-Farm Employment Change", "100K", "120K")) == "High"
    assert g.effective_impact(_m("Some Unmapped Index", "1", "1")) == "Unknown"
    assert g.effective_impact(_m("Some Unmapped Index", "1", "1", impact="low")) == "Low"
    assert g.effective_impact(_m("Non-Farm Employment Change", "1", "1", impact="Medium")) == "Medium"
    cluster = _cluster(_m(*CLAIMS_HIGH), _m("Some Unmapped Index", "1", "1", impact="Low"),
                       _m(*CPI_HOT))
    assert g.cluster_impact(cluster) == "High"


def test_next_release_gap_min():
    minutes = [T, T + dt.timedelta(minutes=10), T - dt.timedelta(minutes=5)]
    assert g.next_release_gap_min(T, minutes) == 10.0
    assert g.next_release_gap_min(T + dt.timedelta(minutes=10), minutes) is None


# ---- release rows ------------------------------------------------------------------------------

def test_build_release_row_exact_keys_and_units():
    metrics = {key: None for key in m.METRIC_KEYS}
    metrics.update(status="ok", bar_source="sec1", resolution_s=1, p0=4080.0, p0_lag_s=0,
                   peak_1=9.0, peak_5=10.0, peak_30=12.0, net_5=3.0, net_30=-8.5)
    dxy = {"bar_source": "sec1", "p0": 99.5, "net_5": 0.03, "net_30": 0.05, "status": "ok"}
    cluster = _cluster(_m(*CPI_HOT), _m(*CORE_HOT))
    row = g.build_release_row(cluster, "XAUUSD", metrics, 1.5, 10.0, dxy)
    assert tuple(row) == g.RELEASE_ROW_KEYS
    assert row["t_utc"] == "2026-03-12T12:30:00+00:00"
    assert row["t_sast"] == "2026-03-12 14:30 SAST"
    assert row["titles"] == "CPI m/m | Core CPI m/m"
    assert row["n_members"] == 2 and row["cluster_class"] == "agree" and row["all_same"] is True
    assert row["impact"] == "High" and row["implied_dir"] == -1
    assert row["peak_1_x"] == pytest.approx(6.0)
    assert row["peak_30_x"] == pytest.approx(8.0)
    assert row["abs_net_30_x"] == pytest.approx(8.5 / 1.5)
    assert row["dir_net_30_x"] == pytest.approx(8.5 / 1.5)   # gold fell, as implied
    assert row["peak_1_owner"] == pytest.approx(900.0)
    assert row["owner_unit"] == "pips"
    assert row["dxy_bar_source"] == "sec1" and row["dxy_p0"] == 99.5
    assert row["dxy_net_5"] == 0.03 and row["dxy_net_30"] == 0.05
    assert row["next_release_gap_min"] == 10.0 and row["baseline"] == 1.5


def test_build_release_row_no_data_and_no_baseline():
    metrics = {key: None for key in m.METRIC_KEYS}
    metrics.update(status="no_data", bar_source="none", resolution_s=0)
    row = g.build_release_row(_cluster(_m(*CPI_HOT)), "US30", metrics, None, None, {})
    assert tuple(row) == g.RELEASE_ROW_KEYS
    assert row["owner_unit"] == "points"
    for key in ("peak_1_x", "abs_net_5_x", "dir_net_30_x", "peak_1_owner", "dxy_p0", "dxy_bar_source"):
        assert row[key] is None


# ---- contamination -----------------------------------------------------------------------------

def test_rows_with_next_release_inside_horizon_are_excluded():
    near = _row(next_release_gap_min=10.0)
    assert g.usable(near, 1) and g.usable(near, 5)
    assert not g.usable(near, 30)
    alone = _row(next_release_gap_min=None)
    assert all(g.usable(alone, k) for k in (1, 5, 30))
    assert not g.usable(_row(status="no_data"), 1)

    rows = [
        _row(cluster_class="agree", peak_5_x=2.0, peak_30_x=3.0, next_release_gap_min=10.0),
        _row(cluster_class="agree", peak_5_x=4.0, peak_30_x=5.0, next_release_gap_min=None),
    ]
    table = g.magnitude_table(rows, "XAUUSD")
    assert table["agree"]["peak_5_x"]["n"] == 2
    assert table["agree"]["peak_30_x"]["n"] == 1
    assert table["agree"]["peak_30_x"]["median"] == 5.0


# ---- group tables ------------------------------------------------------------------------------

def test_magnitude_table_classes_subset_and_hits():
    rows = [
        _row(cluster_class="agree", all_same=True, implied_dir=-1, net_30=-2.0, peak_1_x=1.0),
        _row(cluster_class="agree", all_same=False, implied_dir=1, net_30=-1.0, peak_1_x=3.0),
        _row(cluster_class="conflict", implied_dir=None, net_30=1.0, peak_1_x=5.0),
        _row(cluster_class="agree", symbol="US30", implied_dir=1, net_30=1.0, peak_1_x=9.0),
    ]
    table = g.magnitude_table(rows, "XAUUSD")
    assert set(table) == set(g.CLASS_ORDER)
    assert table["agree"]["peak_1_x"]["n"] == 2
    assert table["agree_all_same"]["peak_1_x"]["n"] == 1
    assert table["agree"]["implied_hit_30"] == {"n": 2, "hits": 1}
    assert table["conflict"]["implied_hit_30"] == {"n": 0, "hits": 0}
    assert table["partial"]["peak_1_x"]["n"] == 0


def test_pullback_table_counts_per_horizon():
    rows = [
        _row(cluster_class="conflict", first_min_dir=1, spike_pullback_5=True, spike_pullback_30=True),
        _row(cluster_class="conflict", first_min_dir=-1, spike_pullback_5=False, spike_pullback_30=True,
             next_release_gap_min=10.0),
        _row(cluster_class="conflict", first_min_dir=0),
    ]
    table = g.pullback_table(rows, "XAUUSD")
    assert table["conflict"] == {"n_first_dir": 2, "n_5": 2, "spike_pullback_5": 1,
                                 "n_30": 1, "spike_pullback_30": 1}


def test_conflict_detail_follows():
    cpi = _m("CPI m/m", "0.3", "0.5", impact="High")
    claims = _m("Unemployment Claims", "220K", "221K", impact="Medium")
    cluster = _cluster(cpi, claims)
    assert g.cluster_class(cluster) == "conflict"
    row = _row(first_min_dir=1, net_5=0.5, net_30=-2.0, spike_pullback_5=False, spike_pullback_30=True)
    detail = g.conflict_detail(cluster, row, "XAUUSD")
    assert set(detail) == set(g.CONFLICT_DETAIL_KEYS)
    assert detail["t_sast"] == "2026-03-12 14:30 SAST"
    assert detail["members"] == [
        {"title": "CPI m/m", "impact": "High", "instrument_dir": -1, "surprise_steps": pytest.approx(2.0)},
        {"title": "Unemployment Claims", "impact": "Medium", "instrument_dir": 1,
         "surprise_steps": pytest.approx(1.0)},
    ]
    assert detail["first_min_dir"] == 1 and detail["net_5_sign"] == 1 and detail["net_30_sign"] == -1
    assert detail["first_followed"] == ["Unemployment Claims"]
    assert detail["net30_followed"] == ["CPI m/m"]
    assert detail["largest_surprise_title"] == "CPI m/m"
    assert detail["first_followed_largest"] is False
    assert detail["net30_followed_largest"] is True
    assert detail["highest_impact_title"] == "CPI m/m"
    assert detail["net30_followed_highest_impact"] is True
    assert detail["spike_pullback_5"] is False and detail["spike_pullback_30"] is True


def test_conflict_detail_ties_and_contamination():
    cpi = _m("CPI m/m", "0.3", "0.4")                       # High (registry), 1 step
    core = _m("Core CPI m/m", "0.3", "0.2")                 # High (registry), 1 step, opposite
    cluster = _cluster(cpi, core)
    row = _row(first_min_dir=1, net_5=0.5, net_30=-2.0, spike_pullback_30=True, next_release_gap_min=15.0)
    detail = g.conflict_detail(cluster, row, "XAUUSD")
    assert detail["largest_surprise_title"] is None
    assert detail["highest_impact_title"] is None
    assert detail["net30_followed_highest_impact"] is None
    assert detail["first_followed_largest"] is None
    # Another release 15 min later: the 30-min net is contaminated, so nothing is credited at 30 min.
    assert detail["net_30_sign"] is None and detail["net30_followed"] is None
    assert detail["spike_pullback_30"] is None
    assert detail["net_5_sign"] == 1


def test_peak_distribution_bands():
    peaks = [4.99, 5.0, 10.0, 15.0, 20.01]
    rows = [_row(impact="High", peak_1=p, ttp_1_s=5) for p in peaks]
    rows.append(_row(impact="Medium", peak_1=1.0, peak_5=2.0, ttp_1_s=30, ttp_30_s=600))
    rows.append(_row(impact="High", symbol="US30", peak_1=50.0))
    dist = g.peak_distribution(rows, "XAUUSD")
    assert set(dist) == {"High", "others"}
    assert dist["High"]["bands"] == {"lt5": 1, "5_10": 1, "10_15": 1, "15_20": 1, "20_plus": 1}
    assert dist["High"]["peak_1"]["n"] == 5 and dist["High"]["peak_1"]["median"] == 10.0
    assert dist["High"]["ttp_1_s"]["median"] == 5
    assert dist["others"]["peak_1"]["n"] == 1 and dist["others"]["ttp_30_s"]["max"] == 600
    us30 = g.peak_distribution(rows, "US30")
    assert "bands" not in us30["High"] and us30["High"]["peak_1"]["n"] == 1

    s = g.summarize([1, 2, 3, 4])
    assert set(s) == {"n", "mean", "p25", "median", "p75", "p90", "max"}
    assert s["n"] == 4 and s["median"] == 2.5 and s["p25"] == pytest.approx(1.75)
    assert s["mean"] == 2.5 and s["max"] == 4
    empty = g.summarize([])
    assert empty["n"] == 0 and empty["median"] is None and empty["max"] is None
