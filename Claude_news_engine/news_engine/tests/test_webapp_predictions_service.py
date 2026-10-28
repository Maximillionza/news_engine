"""Tests for webapp/predictions_service.py's compute_tier1_sentiment_conflict() — the shared Tier1-vs-sentiment comparison used by both /api/predictions (Dashboard) and webapp/history.py (History tab)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webapp.predictions_service import compute_tier1_sentiment_conflict
from webapp.predictions_service import _relevance_magnitude_read
from webapp.predictions_service import _tier1_prediction_dict
from types import SimpleNamespace


def _tier1_row(source, value):
    return SimpleNamespace(id=1, value=value, confidence="Likely", source=source, predicted_direction="neutral")


def test_tier1_prediction_tier_is_market_implied_for_a_fedwatch_valued_row():
    print("=== _tier1_prediction_dict: a URL-sourced row whose value leads with a FedWatch citation is market_implied (B12) ===")
    url_source = "https://fxstreet.com/news/us-dollar-index-falls ; https://alanlongbon.substack.com/p/a-pause"
    fedwatch = _tier1_row(url_source, "FedWatch: ~91% hold priced, Dec hike ~80-87% priced")
    assert _tier1_prediction_dict(fedwatch)["tier"] == "market_implied"
    assert _tier1_prediction_dict(_tier1_row(url_source, "Hold expected per Fed speakers"))["tier"] == "judgment"
    print("PASS\n")


def test_opposing_directional_calls_flagged_as_conflict():
    print("=== compute_tier1_sentiment_conflict: bullish vs bearish is a real conflict ===")
    result = compute_tier1_sentiment_conflict("bearish", "bullish")
    assert result == {"sentiment_direction": "bearish", "tier1_direction": "bullish", "tier1_tier": None}
    print("PASS\n")


def test_conflict_names_its_tier1_tier_when_given():
    print("=== compute_tier1_sentiment_conflict: tier1_tier is carried through, None when not passed ===")
    assert compute_tier1_sentiment_conflict("bearish", "bullish", "formula") == {
        "sentiment_direction": "bearish", "tier1_direction": "bullish", "tier1_tier": "formula",
    }
    assert compute_tier1_sentiment_conflict("bearish", "bullish") == {
        "sentiment_direction": "bearish", "tier1_direction": "bullish", "tier1_tier": None,
    }
    print("PASS\n")


def test_agreeing_directional_calls_are_not_a_conflict():
    print("=== compute_tier1_sentiment_conflict: agreement is never flagged ===")
    assert compute_tier1_sentiment_conflict("bullish", "bullish") is None
    print("PASS\n")


def test_neutral_or_missing_side_is_never_a_conflict():
    print("=== compute_tier1_sentiment_conflict: 'neutral' or None on either side is never a conflict ===")
    assert compute_tier1_sentiment_conflict("bullish", "neutral") is None
    assert compute_tier1_sentiment_conflict(None, "bullish") is None
    assert compute_tier1_sentiment_conflict("bearish", None) is None
    assert compute_tier1_sentiment_conflict(None, None) is None
    print("PASS\n")


def test_relevance_magnitude_read_not_relevant_case(monkeypatch):
    # Synthetic NOT_RELEVANT fixture -- no real cell in the shipped table
    # is NOT_RELEVANT (Phase 1 shipped 0 NOT_RELEVANT cells), so this
    # patches get_relevance() to return one for this test only, per the
    # spec's explicit note that this case needs a synthetic fixture.
    from data_layer.event_symbol_relevance import RelevanceJudgment, RelevanceStatus
    import webapp.predictions_service as svc

    def fake_get_relevance(event_type, symbol):
        assert event_type == "CPI m/m"
        assert symbol == "XAUUSD"
        return RelevanceJudgment(RelevanceStatus.NOT_RELEVANT, "synthetic test fixture")

    monkeypatch.setattr(svc, "get_relevance", fake_get_relevance)
    result = _relevance_magnitude_read("CPI m/m", "XAUUSD")
    assert result == "not_relevant"


def test_relevance_magnitude_read_low_magnitude_case():
    # Real shipped cell: ("Retail Sales m/m", "USDJPY") is a real LOW-tier
    # entry per docs/event-symbol-magnitude.md -- verify against the real
    # table directly rather than mocking, since this is a real shipped case.
    from data_layer.event_symbol_relevance import get_relevance, RelevanceStatus
    from data_layer.event_symbol_magnitude import get_magnitude, MagnitudeTier
    assert get_relevance("Retail Sales m/m", "USDJPY").status == RelevanceStatus.RELEVANT
    assert get_magnitude("Retail Sales m/m", "USDJPY").tier == MagnitudeTier.LOW
    result = _relevance_magnitude_read("Retail Sales m/m", "USDJPY")
    assert result == "low_magnitude"


def test_relevance_magnitude_read_relevant_medium_or_high_is_neutral():
    # Real shipped cell: ("CPI m/m", "XAUUSD") is RELEVANT + MEDIUM.
    result = _relevance_magnitude_read("CPI m/m", "XAUUSD")
    assert result is None


def test_relevance_magnitude_read_unverified_relevance_is_neutral():
    # A real UNVERIFIED relevance cell exists in the shipped table --
    # find one live rather than hardcoding a guess at which pair.
    from data_layer.event_symbol_relevance import EVENT_TYPES, SYMBOLS, get_relevance, RelevanceStatus
    unverified_pair = None
    for event_type in EVENT_TYPES:
        for symbol in SYMBOLS:
            if get_relevance(event_type, symbol).status == RelevanceStatus.UNVERIFIED:
                unverified_pair = (event_type, symbol)
                break
        if unverified_pair:
            break
    assert unverified_pair is not None, "expected at least one real UNVERIFIED relevance cell"
    result = _relevance_magnitude_read(*unverified_pair)
    assert result is None


def test_relevance_magnitude_read_unverified_magnitude_is_neutral():
    # A real UNVERIFIED magnitude cell exists in the shipped table (9 of
    # them) -- find one live among RELEVANT pairs rather than guessing.
    from data_layer.event_symbol_relevance import EVENT_TYPES, SYMBOLS, get_relevance, RelevanceStatus
    from data_layer.event_symbol_magnitude import get_magnitude, MagnitudeTier
    unverified_pair = None
    for event_type in EVENT_TYPES:
        for symbol in SYMBOLS:
            if get_relevance(event_type, symbol).status != RelevanceStatus.RELEVANT:
                continue
            if get_magnitude(event_type, symbol).tier == MagnitudeTier.UNVERIFIED:
                unverified_pair = (event_type, symbol)
                break
        if unverified_pair:
            break
    assert unverified_pair is not None, "expected at least one real UNVERIFIED magnitude cell"
    result = _relevance_magnitude_read(*unverified_pair)
    assert result is None


def test_relevance_magnitude_read_unmapped_title_is_neutral():
    result = _relevance_magnitude_read("Unemployment Claims", "XAUUSD")
    assert result is None


def test_relevance_magnitude_read_relevance_keyerror_is_neutral(monkeypatch):
    # CORRECTED (final whole-branch review): this test previously claimed
    # ("ISM Services PMI", "US30") was "genuinely absent from both tables
    # (KeyError), not UNVERIFIED" -- that's false. The shipped
    # data_layer/event_symbol_relevance.py's _RELEVANCE_TABLE is
    # EXHAUSTIVELY populated at 108/108 cells (9 event types x 12
    # symbols, verified directly: len(_RELEVANCE_TABLE) == 108, zero
    # missing keys), so get_relevance("ISM Services PMI", "US30") really
    # returns UNVERIFIED, not a KeyError -- the old test happened to still
    # pass (UNVERIFIED is also neutral from _relevance_magnitude_read's
    # perspective) but was exercising the wrong code path, leaving
    # _relevance_magnitude_read's `except KeyError` branch around
    # get_relevance() untested against any real gap.
    #
    # No real (mapped title, tracked symbol) pair can ever KeyError
    # against the relevance table today. The `except KeyError` branch is
    # correct defensive/future-proofing (e.g. for a symbol added to
    # symbol-picker.js but not yet added to SYMBOLS/_RELEVANCE_TABLE) per
    # the design doc's explicit "KeyError-as-neutral" requirement, not
    # something reachable via shipped data -- so it's verified directly
    # here via mocking, matching this file's own
    # test_relevance_magnitude_read_not_relevant_case monkeypatch style.
    import webapp.predictions_service as svc

    def fake_get_relevance(event_type, symbol):
        assert event_type == "ISM Services PMI"
        assert symbol == "US30"
        raise KeyError((event_type, symbol))

    monkeypatch.setattr(svc, "get_relevance", fake_get_relevance)
    result = _relevance_magnitude_read("ISM Services PMI", "US30")
    assert result is None


def test_relevance_magnitude_read_magnitude_keyerror_is_neutral(monkeypatch):
    # The magnitude table (data_layer/event_symbol_magnitude.py) IS
    # deliberately scoped to only the 94 real RELEVANT (event_type,
    # symbol) pairs (verified directly: len(_MAGNITUDE_TABLE) == 94,
    # exactly matching the relevant-pair count, zero missing) -- so, like
    # the relevance table, no real RELEVANT pair can KeyError against it
    # today either. Same defensive/future-proofing reasoning as the
    # relevance KeyError test above -- verified here via mocking rather
    # than relying on a currently-nonexistent real gap.
    import webapp.predictions_service as svc
    from data_layer.event_symbol_relevance import RelevanceJudgment, RelevanceStatus

    def fake_get_relevance(event_type, symbol):
        return RelevanceJudgment(RelevanceStatus.RELEVANT, "synthetic test fixture")

    def fake_get_magnitude(event_type, symbol):
        assert event_type == "CPI m/m"
        assert symbol == "XAUUSD"
        raise KeyError((event_type, symbol))

    monkeypatch.setattr(svc, "get_relevance", fake_get_relevance)
    monkeypatch.setattr(svc, "get_magnitude", fake_get_magnitude)
    result = _relevance_magnitude_read("CPI m/m", "XAUUSD")
    assert result is None


# --- B8 (2026-10-27): standardized surprise in the read-time recompute ------------------------------

_CLAIMS_PRIORS = [("225K", "215K"), ("220K", "215K"), ("202K", "209K"), ("210K", "206K"), ("208K", "203K"), ("205K", "206K")]


def _claims_history(conn, event_time, n_priors=6):
    import datetime as dt
    import webapp.store as store
    for k, (forecast, actual) in enumerate(_CLAIMS_PRIORS[:n_priors], start=1):
        when = event_time - dt.timedelta(days=7 * k)
        store.insert_event_history_if_absent(conn, "Unemployment Claims", when, forecast, "210K", actual, None, "live", "Medium", "USD", when)
    store.insert_event_history_if_absent(conn, "Unemployment Claims", event_time, "225K", "210K", "219K", "lower", "live", "Medium", "USD", event_time)


def test_recompute_stale_pending_uses_sigma_when_conn_given(tmp_path):
    import datetime as dt
    import math
    import pytest
    import webapp.store as store
    from webapp.predictions_service import _recompute_stale_pending
    from webapp.symbols import classify_symbol, usd_sign

    event_time = dt.datetime(2026, 10, 22, 12, 30, tzinfo=dt.timezone.utc)
    conn = store.get_connection(tmp_path / "d.db")
    _claims_history(conn, event_time)
    event = {"title": "Unemployment Claims", "event_time_utc": event_time.isoformat(), "impact": "Medium"}
    history = store.get_event_history(conn, "Unemployment Claims")
    symbol_class = classify_symbol("XAUUSD")

    without_conn = _recompute_stale_pending(event, symbol_class, history)
    with_conn = _recompute_stale_pending(event, symbol_class, history, conn)
    conn.close()

    sign = usd_sign(symbol_class.usd_relationship)
    assert without_conn.raw_score == pytest.approx(sign * 0.079830, abs=1e-6)      # today's percent method
    z = -6000 / 5887.84
    assert with_conn.raw_score == pytest.approx(sign * -math.tanh(z * 0.5), abs=1e-5)
    assert with_conn.raw_score == pytest.approx(-0.469575, abs=1e-6)
    assert with_conn.raw_score != without_conn.raw_score


def test_build_predictions_payload_recompute_uses_sigma(tmp_path):
    import datetime as dt
    import math
    import pytest
    import webapp.store as store
    import scoring.backtest_store as bs
    from webapp.predictions_service import build_predictions_payload

    event_time = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)).replace(microsecond=0)
    conn = store.get_connection(tmp_path / "d.db")
    bt = bs.get_connection(tmp_path / "bt.db")
    store.add_tracked_symbol(conn, "XAUUSD")
    _claims_history(conn, event_time)
    payload = build_predictions_payload(conn, bt)
    conn.close()
    bt.close()

    xau = next(p for p in payload["predictions"] if p["symbol"] == "XAUUSD")
    claims = next(e for e in xau["events"] if e["event_title"] == "Unemployment Claims")
    assert claims["recomputed_from_event_history"] is True
    assert claims["probability"] == pytest.approx(0.5 + 0.5 * math.tanh(3.0 * -0.469575), abs=1e-5)


if __name__ == "__main__":
    test_opposing_directional_calls_flagged_as_conflict()
    test_agreeing_directional_calls_are_not_a_conflict()
    test_neutral_or_missing_side_is_never_a_conflict()
    print("All webapp_predictions_service tests passed.")
