"""
B11 (C1, C2): the dead exogenous-shock path and the tier1_comparisons writer are gone,
but their tables stay in the schema so old DBs are untouched.
"""
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scoring.backtest_store as backtest_store
import webapp.predictions_service as predictions_service
import scripts.confirm_backtest_outcomes as confirm_outcomes
import scripts.event_study_once as once
from dukascopy_python.instruments import INSTRUMENT_IDX_AMERICA_DOLLAR_IDX_USD


def test_removed_modules_are_gone():
    print("=== B11: discovery_detector / exposure / tier1_comparison modules no longer exist ===")
    for name in ("data_layer.discovery_detector", "data_layer.exposure", "scoring.tier1_comparison"):
        assert importlib.util.find_spec(name) is None, name
    print("PASS\n")


def test_backtest_store_no_longer_exports_dead_api():
    print("=== B11: backtest_store no longer exports the shock / taxonomy / tier1_comparison API ===")
    for name in ("_VALID_TAXONOMY_CATEGORIES", "ExogenousShockRow", "record_exogenous_shock",
                 "get_exogenous_shock_for_date", "record_tier1_comparison", "get_tier1_comparison_for_occurrence"):
        assert not hasattr(backtest_store, name), name
    print("PASS\n")


def test_dead_tables_kept_in_schema():
    print("=== B11: exogenous_shocks and tier1_comparisons tables are still created, so old DBs keep them ===")
    conn = backtest_store.get_connection(":memory:")
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"exogenous_shocks", "tier1_comparisons"} <= tables, tables
    conn.close()
    print("PASS\n")


def test_confirm_outcomes_no_longer_writes_tier1_comparisons():
    print("=== B11: confirm_backtest_outcomes has no tier1_comparison hook any more ===")
    assert not hasattr(confirm_outcomes, "_try_record_tier1_comparison")
    assert "tier1_comparison" not in Path(confirm_outcomes.__file__).read_text(encoding="utf-8")
    print("PASS\n")


def test_event_study_dxy_instrument_is_dukascopy_dollar_index():
    print("=== B11: the B5 event-study tool still resolves DXY to the Dukascopy dollar index ===")
    assert once.dukascopy_instrument("DXY") == INSTRUMENT_IDX_AMERICA_DOLLAR_IDX_USD
    print("PASS\n")


def test_predictions_service_has_no_shock_path():
    print("=== B11: predictions_service has no exogenous-shock helpers ===")
    assert not hasattr(predictions_service, "_get_todays_exogenous_shocks")
    assert not hasattr(predictions_service, "_first_exposing_shock")
    print("PASS\n")


if __name__ == "__main__":
    test_removed_modules_are_gone()
    test_backtest_store_no_longer_exports_dead_api()
    test_dead_tables_kept_in_schema()
    test_confirm_outcomes_no_longer_writes_tier1_comparisons()
    test_event_study_dxy_instrument_is_dukascopy_dollar_index()
    test_predictions_service_has_no_shock_path()
    print("All dead-code-removal tests passed.")
