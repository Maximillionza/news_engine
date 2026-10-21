# tests/test_ops_health.py
# B4 O6: the health check grades every job, feed, classifier and Tier 1 capture
# against its expected interval, and turns red items into at most one Telegram
# notice per UTC day. In-memory dashboard/backtest/alerts DBs, a tmp ops DB and
# a tmp macro marker; nothing real is read or sent.
from __future__ import annotations

import datetime as dt
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from alerting import store as alerting_store
from ops import health
from ops import state as ops_state
from scoring import backtest_store as bs
from webapp import store as ws

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 10, 20, 10, 0, tzinfo=UTC)

EXPECTED_KEYS = [
    "shock_poll", "outcome_confirm", "reaction_incremental", "reaction_baselines",
    "tier1_capture_daily", "tier1_capture_weekly", "tier1_research", "nowcast_live",
    "shock_reality_check", "article_accumulator", "calendar_refresh", "macro_calendar",
    "classifier:ollama", "classifier:claude",
    "feed:reuters_business", "feed:cnbc_top_news", "feed:cnbc_economy", "feed:investing_com_forex",
]


def _open(tmp_path: Path, tracking_since: dt.datetime = NOW - dt.timedelta(days=30), name: str = "ops.db"):
    return SimpleNamespace(
        dash=ws.get_connection(":memory:"),
        bt=bs.get_connection(":memory:"),
        alerts=alerting_store.get_connection(":memory:"),
        ops=ops_state.get_connection(tmp_path / name, now=tracking_since),
        marker=tmp_path / "macro_marker",
    )


@pytest.fixture
def c(tmp_path: Path):
    conns = _open(tmp_path)
    yield conns
    for conn in (conns.dash, conns.bt, conns.alerts, conns.ops):
        try:
            conn.close()
        except Exception:
            pass


def _build(c, now: dt.datetime = NOW) -> dict[str, health.HealthItem]:
    items = health.build_health(
        now, dash_conn=c.dash, bt_conn=c.bt, alerts_conn=c.alerts, ops_conn=c.ops, macro_marker_path=c.marker)
    return {item.key: item for item in items}


def _fresh_jobs(c, now: dt.datetime = NOW) -> None:
    for job in ops_state.JOB_NAMES:
        ops_state.record_job_run(c.ops, job, now - dt.timedelta(minutes=1), 0)


def _event(c, title: str, when: str, country: str = "USD") -> None:
    c.dash.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, surprise_direction, "
        "recorded_at_utc, updated_at_utc, source, impact, country) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (title, when, None, None, None, None, when, when, "live", "High", country))
    c.dash.commit()


def _tier1_call(c, title: str, event_time: str, logged_at: str, source: str = "BLS consensus") -> None:
    c.bt.execute(
        "INSERT INTO tier1_predictions (event_title, instrument, event_time_utc, value, confidence, source, "
        "predicted_direction, logged_at_utc) VALUES (?,?,?,?,?,?,?,?)",
        (title, "XAUUSD", event_time, "0.3%", "Likely", source, "bullish", logged_at))
    c.bt.commit()


def _macro(c, event_date: str, recorded_at: str) -> None:
    c.dash.execute(
        "INSERT INTO macro_calendar (event_title, event_date, estimated_time_utc, time_source, confirmed, "
        "confirmed_event_time_utc, source, recorded_at_utc, updated_at_utc) VALUES (?,?,?,?,?,?,?,?,?)",
        (f"Event {event_date}", event_date, None, "unconfirmed", 0, None, "fred", recorded_at, recorded_at))
    c.dash.commit()


def _alert(c, method: str, detected: dt.datetime) -> None:
    alerting_store.record_alert(
        c.alerts, headline=f"headline {method} {detected.isoformat()}", source="cnbc_top_news",
        url="https://example.com", published_utc=detected, detected_at_utc=detected, category="geopolitical",
        severity="Medium", classification_method=method, rationale=None, affected_symbols=[])


def _clean_feeds(c, now: dt.datetime = NOW) -> None:
    for name in ("reuters_business", "cnbc_top_news", "cnbc_economy", "investing_com_forex"):
        alerting_store.record_source_success(c.alerts, name, now - dt.timedelta(minutes=1))


def test_health_flags_the_three_known_silent_failures(c):
    _fresh_jobs(c)
    _clean_feeds(c)
    _event(c, "PPI m/m", "2026-10-15T12:30:00+00:00")
    _event(c, "CPI m/m", "2026-10-14T12:30:00+00:00")
    _tier1_call(c, "PPI m/m", "2026-09-14T12:30:00+00:00", "2026-09-13T08:00:00+00:00")
    for day in ("2026-08-20", "2026-09-03", "2026-09-17"):
        _macro(c, day, "2026-08-16T10:48:00+00:00")
    alerting_store.set_provider_cooldown(c.alerts, "claude", dt.datetime(2026, 10, 20, 9, 55, tzinfo=UTC))
    _alert(c, "llm", dt.datetime(2026, 10, 14, 9, 0, tzinfo=UTC))
    _alert(c, "llm_ollama", dt.datetime(2026, 10, 19, 9, 0, tzinfo=UTC))
    _alert(c, "llm_ollama", dt.datetime(2026, 10, 20, 8, 0, tzinfo=UTC))

    items = _build(c)

    assert items["tier1_research"].status == "red"
    assert "PPI m/m" in items["tier1_research"].detail
    assert items["nowcast_live"].status == "red"
    assert "CPI m/m" in items["nowcast_live"].detail
    assert items["macro_calendar"].status == "red"
    assert "2026-09-17" in items["macro_calendar"].detail
    assert items["classifier:claude"].status == "red"
    assert items["classifier:ollama"].status == "ok"
    assert items["shock_poll"].status == "ok"
    assert health.overall_status(list(items.values())) == "red"


def test_job_heartbeat_statuses_follow_amber_and_red_thresholds(c):
    for minutes, expected in ((5, "ok"), (15, "amber"), (31, "red")):
        ops_state.record_job_run(c.ops, "shock_poll", NOW - dt.timedelta(minutes=minutes), 0)
        item = _build(c)["shock_poll"]
        assert item.status == expected, minutes
        assert item.age_seconds == minutes * 60
        assert item.expected_every_seconds == 120


def test_never_run_job_is_amber_until_red_after_tracking(tmp_path):
    young = _open(tmp_path, tracking_since=NOW - dt.timedelta(days=1), name="young.db")
    item = _build(young)["tier1_capture_weekly"]
    assert item.status == "amber"
    assert "no successful run" in item.detail
    assert item.last_success_utc is None

    old = _open(tmp_path, tracking_since=NOW - dt.timedelta(days=10), name="old.db")
    assert _build(old)["tier1_capture_weekly"].status == "red"


def test_missed_release_compares_naive_and_offset_stamps_as_instants(tmp_path):
    on_time = _open(tmp_path, name="a.db")
    _event(on_time, "PPI m/m", "2026-10-15T12:30:00")
    _tier1_call(on_time, "PPI m/m", "2026-10-15T12:30:00+00:00", "2026-10-15T14:29:00+02:00")
    assert _build(on_time)["tier1_research"].status == "ok"

    late = _open(tmp_path, name="b.db")
    _event(late, "PPI m/m", "2026-10-15T12:30:00")
    _tier1_call(late, "PPI m/m", "2026-10-15T12:30:00+00:00", "2026-10-15T14:31:00+02:00")
    item = _build(late)["tier1_research"]
    assert item.status == "red"
    assert "missed: PPI m/m 2026-10-15 14:30 SAST" in item.detail


def test_missed_release_ignores_non_usd_and_out_of_window_occurrences(c):
    _event(c, "PPI m/m", "2026-10-15T12:30:00+00:00", country="EUR")
    _event(c, "Retail Sales m/m", "2026-10-10T12:30:00+00:00")      # 10 days back: outside the 7-day lookback
    assert _build(c)["tier1_research"].status == "ok"


def test_missed_release_detail_lists_three_then_counts_the_rest(c):
    for day in (13, 14, 15, 16, 17):
        _event(c, "PPI m/m", f"2026-10-{day}T12:30:00+00:00")
    item = _build(c)["tier1_research"]
    assert item.status == "red"
    assert item.detail.count("PPI m/m") == 3
    assert item.detail.endswith("and 2 more")


def test_tier1_research_amber_when_a_release_within_24h_has_no_call(c):
    when = (NOW + dt.timedelta(hours=20)).isoformat()
    _event(c, "Non-Farm Employment Change", when)
    item = _build(c)["tier1_research"]
    assert item.status == "amber"
    assert "due within 24h without a call" in item.detail
    assert "Non-Farm Employment Change" in item.detail

    _tier1_call(c, "Non-Farm Employment Change", when, (NOW - dt.timedelta(hours=1)).isoformat())
    assert _build(c)["tier1_research"].status == "ok"


def test_nowcast_live_ok_with_a_pre_release_live_snapshot(c):
    release = dt.datetime(2026, 10, 14, 12, 30, tzinfo=UTC)
    _event(c, "CPI m/m", release.isoformat())
    bs.record_nowcast_snapshot(c.bt, "CPI m/m", release, 0.3, release - dt.timedelta(hours=10), "cleveland", "live")
    item = _build(c)["nowcast_live"]
    assert item.status == "ok"
    assert item.last_success_utc is not None


def test_outcome_confirm_amber_when_a_prediction_waits_more_than_3_days(c):
    _fresh_jobs(c)
    bs.record_prediction(c.bt, "NFP", "XAUUSD", NOW - dt.timedelta(days=5), 0.6, "bullish", 0.4, 3, False,
                         scored_at_utc=NOW - dt.timedelta(days=6))
    bs.record_prediction(c.bt, "CPI", "XAUUSD", NOW - dt.timedelta(days=1), 0.6, "bullish", 0.4, 3, False,
                         scored_at_utc=NOW - dt.timedelta(days=2))
    item = _build(c)["outcome_confirm"]
    assert item.status == "amber"
    assert "1 awaiting more than 3 days (no price data)" in item.detail


def test_feed_states_backoff_amber_and_two_weeks_failing_red(c):
    for minutes in (6, 4, 2):
        alerting_store.record_source_failure(
            c.alerts, "reuters_business", NOW - dt.timedelta(minutes=minutes), "boom", NOW + dt.timedelta(minutes=8))
    alerting_store.record_source_failure(c.alerts, "cnbc_top_news", NOW - dt.timedelta(days=15), "boom", None)
    alerting_store.record_source_failure(
        c.alerts, "cnbc_top_news", NOW - dt.timedelta(hours=1), "boom", NOW + dt.timedelta(hours=5))
    alerting_store.record_source_success(c.alerts, "cnbc_economy", NOW - dt.timedelta(minutes=1))

    items = _build(c)

    assert items["feed:reuters_business"].status == "amber"
    assert "in backoff until" in items["feed:reuters_business"].detail
    assert items["feed:cnbc_top_news"].status == "red"
    assert "candidate to drop" in items["feed:cnbc_top_news"].detail
    assert items["feed:cnbc_economy"].status == "ok"
    assert items["feed:investing_com_forex"].status == "amber"
    assert items["feed:investing_com_forex"].detail == "no poll recorded yet"


def test_feed_with_one_failure_is_amber(c):
    alerting_store.record_source_failure(c.alerts, "cnbc_economy", NOW - dt.timedelta(minutes=2), "boom", None)
    item = _build(c)["feed:cnbc_economy"]
    assert item.status == "amber"
    assert item.detail == "1 consecutive failure(s)"


def test_classifier_intermittent_failures_are_amber(c):
    _alert(c, "llm_ollama", NOW - dt.timedelta(hours=2))
    alerting_store.set_provider_cooldown(c.alerts, "ollama", NOW - dt.timedelta(hours=1))
    item = _build(c)["classifier:ollama"]
    assert item.status == "amber"
    assert item.detail == "intermittent failures in the last 24h"


def test_classifier_failure_with_no_success_ever_is_red(c):
    alerting_store.set_provider_cooldown(c.alerts, "claude", NOW + dt.timedelta(minutes=5))
    item = _build(c)["classifier:claude"]
    assert item.status == "red"
    assert "last success never" in item.detail
    assert "cooling down until 2026-10-20 12:05 SAST" in item.detail


def test_macro_calendar_red_when_horizon_exhausted_even_if_recently_refreshed(c):
    c.marker.write_text((NOW - dt.timedelta(days=1)).isoformat())
    _macro(c, "2026-10-19", (NOW - dt.timedelta(days=1)).isoformat())
    item = _build(c)["macro_calendar"]
    assert item.status == "red"
    assert "2026-10-19" in item.detail


def test_macro_calendar_ok_when_refreshed_with_rows_ahead(c):
    c.marker.write_text((NOW - dt.timedelta(days=1)).isoformat())
    _macro(c, "2026-11-20", (NOW - dt.timedelta(days=1)).isoformat())
    assert _build(c)["macro_calendar"].status == "ok"


def test_data_timestamp_counts_when_the_job_has_no_run_record(c):
    bs.record_check(c.bt, NOW - dt.timedelta(hours=2))
    item = _build(c)["article_accumulator"]
    assert item.status == "ok"
    assert item.last_success_utc == NOW - dt.timedelta(hours=2)


def test_one_failing_check_does_not_break_the_others(c):
    _fresh_jobs(c)
    c.dash.close()
    items = _build(c)
    for key in ("tier1_research", "nowcast_live", "calendar_refresh", "macro_calendar"):
        assert items[key].status == "amber", key
        assert items[key].detail.startswith("check failed"), key
    assert items["shock_poll"].status == "ok"
    assert items["outcome_confirm"].status == "ok"


def test_item_keys_and_order_are_stable(c):
    keys = [item.key for item in health.build_health(
        NOW, dash_conn=c.dash, bt_conn=c.bt, alerts_conn=c.alerts, ops_conn=c.ops, macro_marker_path=c.marker)]
    assert keys == EXPECTED_KEYS


def test_provider_method_map_matches_poll_once():
    from alerting import poll_once
    assert health.PROVIDER_METHOD == poll_once._METHOD_BY_PROVIDER


def test_macro_marker_path_matches_the_refresh_script():
    from scripts import refresh_macro_calendar
    assert health.MACRO_MARKER_PATH == refresh_macro_calendar._LAST_MACRO_REFRESH_FILE


def test_awaiting_stuck_threshold_matches_the_final_no_reaction_rule():
    from scripts import confirm_backtest_outcomes
    assert health.AWAITING_STUCK_AFTER == confirm_backtest_outcomes.FINAL_NO_REACTION_AFTER


def test_job_detail_names_a_failed_last_run(c):
    ops_state.record_job_run(c.ops, "outcome_confirm", NOW - dt.timedelta(minutes=10), 0)
    ops_state.record_job_run(c.ops, "outcome_confirm", NOW - dt.timedelta(minutes=5), 1)
    item = _build(c)["outcome_confirm"]
    assert item.status == "ok"                  # graded on the last success, 10 min ago
    assert "exited 1" in item.detail


def test_health_item_dict_has_exact_keys_and_whole_second_age():
    item = health.HealthItem(
        key="shock_poll", label="Shock poll", status="ok", last_success_utc=NOW, age_seconds=61.4,
        expected_every_seconds=120, detail="")
    d = health.health_item_dict(item)
    assert set(d) == {"key", "label", "status", "last_success_utc", "age_seconds", "expected_every_seconds", "detail"}
    assert d["last_success_utc"] == NOW.isoformat()
    assert d["age_seconds"] == 61
    blank = health.health_item_dict(health.HealthItem("x", "X", "amber", None, None, 60, "d"))
    assert blank["last_success_utc"] is None and blank["age_seconds"] is None


def test_overall_status_is_the_worst():
    def item(status: str) -> health.HealthItem:
        return health.HealthItem("k", "K", status, None, None, 60, "")
    assert health.overall_status([item("ok"), item("ok")]) == "ok"
    assert health.overall_status([item("ok"), item("amber")]) == "amber"
    assert health.overall_status([item("amber"), item("red"), item("ok")]) == "red"


# ---------------------------------------------------------------------------
# Daily Telegram notice
# ---------------------------------------------------------------------------
RED = health.HealthItem("macro_calendar", "Macro calendar (FRED)", "red", None, None, 86400,
                        "no macro_calendar rows after 2026-09-17")
RED2 = health.HealthItem("classifier:claude", "Shock classifier: claude", "red", None, None, 86400, "failing")
AMBER = health.HealthItem("feed:cnbc_economy", "Feed: cnbc_economy", "amber", None, None, 120,
                          "1 consecutive failure(s)")


def _conn_tuple(c) -> tuple:
    return (c.dash, c.bt, c.alerts, c.ops)


def test_health_notice_sent_once_per_utc_day_listing_red_items_only(c, monkeypatch):
    build = MagicMock(return_value=[RED, AMBER, RED2])
    monkeypatch.setattr(health, "build_health", build)
    send = MagicMock(return_value=True)

    assert health.maybe_send_health_notice(NOW, send=send, connections=_conn_tuple(c)) is True
    assert send.call_count == 1
    text = send.call_args.args[0]
    assert "Macro calendar (FRED): no macro_calendar rows after 2026-09-17" in text
    assert "Shock classifier: claude" in text
    assert "cnbc_economy" not in text
    assert "2 item(s) need attention" in text
    assert "2026-10-20 12:00 SAST" in text
    assert ops_state.health_notice_sent(c.ops, NOW.date())

    later = NOW + dt.timedelta(hours=13)        # 23:00Z, same UTC day
    assert health.maybe_send_health_notice(later, send=send, connections=_conn_tuple(c)) is False
    assert send.call_count == 1
    assert build.call_count == 1                 # the ledger is checked before building

    next_day = NOW + dt.timedelta(hours=14)     # 00:00Z the next UTC day
    assert health.maybe_send_health_notice(next_day, send=send, connections=_conn_tuple(c)) is True
    assert send.call_count == 2


def test_failed_send_leaves_the_day_open(c, monkeypatch):
    monkeypatch.setattr(health, "build_health", MagicMock(return_value=[RED]))
    send = MagicMock(side_effect=[False, True])
    assert health.maybe_send_health_notice(NOW, send=send, connections=_conn_tuple(c)) is False
    assert not ops_state.health_notice_sent(c.ops, NOW.date())
    assert health.maybe_send_health_notice(NOW, send=send, connections=_conn_tuple(c)) is True
    assert send.call_count == 2
    assert ops_state.health_notice_sent(c.ops, NOW.date())


def test_no_red_items_sends_nothing(c, monkeypatch):
    monkeypatch.setattr(health, "build_health", MagicMock(return_value=[AMBER]))
    send = MagicMock(return_value=True)
    assert health.maybe_send_health_notice(NOW, send=send, connections=_conn_tuple(c)) is False
    send.assert_not_called()
    assert not ops_state.health_notice_sent(c.ops, NOW.date())


def test_notice_never_raises(c, monkeypatch, capsys):
    monkeypatch.setattr(health, "build_health", MagicMock(side_effect=RuntimeError("boom")))
    send = MagicMock(return_value=True)
    assert health.maybe_send_health_notice(NOW, send=send, connections=_conn_tuple(c)) is False
    send.assert_not_called()
    assert "[ops.health] WARNING" in capsys.readouterr().out

    monkeypatch.setattr(health, "build_health", MagicMock(return_value=[RED]))
    assert health.maybe_send_health_notice(
        NOW, send=MagicMock(side_effect=RuntimeError("net")), connections=_conn_tuple(c)) is False


def test_notice_with_its_own_connections_closes_them(monkeypatch, tmp_path):
    opened = _open(tmp_path)
    monkeypatch.setattr(health, "open_health_connections",
                        lambda: (opened.dash, opened.bt, opened.alerts, opened.ops))
    monkeypatch.setattr(health, "build_health", MagicMock(return_value=[RED]))
    send = MagicMock(return_value=True)
    assert health.maybe_send_health_notice(NOW, send=send) is True
    assert send.call_count == 1
    with pytest.raises(Exception):
        opened.ops.execute("SELECT 1")
