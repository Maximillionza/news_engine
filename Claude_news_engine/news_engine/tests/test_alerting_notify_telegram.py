from __future__ import annotations

from unittest.mock import MagicMock, patch

from alerting import notify_telegram


def test_missing_config_returns_false_without_network_call():
    with patch.object(notify_telegram, "TELEGRAM_BOT_TOKEN", ""), \
         patch.object(notify_telegram, "TELEGRAM_CHAT_ID", ""), \
         patch("alerting.notify_telegram.requests.post") as mock_post:
        result = notify_telegram.send_alert("Headline", "energy", "High", "rationale", [], [])
    assert result is False
    mock_post.assert_not_called()


def test_escalation_uses_escalation_wording_not_plain_high():
    mock_response = MagicMock(status_code=200)
    with patch.object(notify_telegram, "TELEGRAM_BOT_TOKEN", "fake-token"), \
         patch.object(notify_telegram, "TELEGRAM_CHAT_ID", "12345"), \
         patch("alerting.notify_telegram.requests.post", return_value=mock_response) as mock_post:
        result = notify_telegram.send_alert(
            "Strait of Hormuz closed", "energy", "High", "Escalated from an earlier Medium read",
            [{"symbol": "XAUUSD", "channel": "safe_haven"}], [{"source": "reuters", "url": "https://x"}],
            is_escalation=True,
        )
    assert result is True
    sent_text = mock_post.call_args.kwargs["json"]["text"]
    assert "ESCALATION" in sent_text
    assert "HIGH --" not in sent_text


def test_successful_send_returns_true():
    mock_response = MagicMock(status_code=200)
    with patch.object(notify_telegram, "TELEGRAM_BOT_TOKEN", "fake-token"), \
         patch.object(notify_telegram, "TELEGRAM_CHAT_ID", "12345"), \
         patch("alerting.notify_telegram.requests.post", return_value=mock_response) as mock_post:
        result = notify_telegram.send_alert(
            "Strait of Hormuz closed", "energy", "High", "Chokepoint closure",
            [{"symbol": "XAUUSD", "channel": "safe_haven"}], [{"source": "reuters", "url": "https://x"}],
        )
    assert result is True
    assert mock_post.called
    sent_text = mock_post.call_args.kwargs["json"]["text"]
    assert "Strait of Hormuz closed" in sent_text
    assert "XAUUSD" in sent_text


def test_non_200_response_returns_false():
    mock_response = MagicMock(status_code=401)
    with patch.object(notify_telegram, "TELEGRAM_BOT_TOKEN", "fake-token"), \
         patch.object(notify_telegram, "TELEGRAM_CHAT_ID", "12345"), \
         patch("alerting.notify_telegram.requests.post", return_value=mock_response):
        result = notify_telegram.send_alert("Headline", "energy", "High", None, [], [])
    assert result is False


def test_network_exception_returns_false_not_raised():
    import requests
    with patch.object(notify_telegram, "TELEGRAM_BOT_TOKEN", "fake-token"), \
         patch.object(notify_telegram, "TELEGRAM_CHAT_ID", "12345"), \
         patch("alerting.notify_telegram.requests.post", side_effect=requests.RequestException("timeout")), \
         patch("alerting.notify_telegram._sleep"):
        result = notify_telegram.send_alert("Headline", "energy", "High", None, [], [])
    assert result is False


def test_non_200_response_is_not_retried():
    """A 401 is a client/auth error -- retrying can't help, so only one attempt should be made."""
    mock_response = MagicMock(status_code=401)
    with patch.object(notify_telegram, "TELEGRAM_BOT_TOKEN", "fake-token"), \
         patch.object(notify_telegram, "TELEGRAM_CHAT_ID", "12345"), \
         patch("alerting.notify_telegram.requests.post", return_value=mock_response) as mock_post, \
         patch("alerting.notify_telegram._sleep") as mock_sleep:
        result = notify_telegram.send_alert("Headline", "energy", "High", None, [], [])
    assert result is False
    assert mock_post.call_count == 1
    mock_sleep.assert_not_called()


def test_retries_on_request_exception_then_succeeds():
    import requests
    mock_response = MagicMock(status_code=200)
    with patch.object(notify_telegram, "TELEGRAM_BOT_TOKEN", "fake-token"), \
         patch.object(notify_telegram, "TELEGRAM_CHAT_ID", "12345"), \
         patch(
             "alerting.notify_telegram.requests.post",
             side_effect=[requests.RequestException("timeout"), mock_response],
         ) as mock_post, \
         patch("alerting.notify_telegram._sleep") as mock_sleep:
        result = notify_telegram.send_alert("Headline", "energy", "High", None, [], [])
    assert result is True
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once()


def test_exhausts_retries_on_persistent_request_exception_returns_false():
    import requests
    with patch.object(notify_telegram, "TELEGRAM_BOT_TOKEN", "fake-token"), \
         patch.object(notify_telegram, "TELEGRAM_CHAT_ID", "12345"), \
         patch(
             "alerting.notify_telegram.requests.post",
             side_effect=requests.RequestException("timeout"),
         ) as mock_post, \
         patch("alerting.notify_telegram._sleep") as mock_sleep:
        result = notify_telegram.send_alert("Headline", "energy", "High", None, [], [])
    assert result is False
    assert mock_post.call_count == notify_telegram._MAX_ATTEMPTS
    assert mock_sleep.call_count == notify_telegram._MAX_ATTEMPTS - 1


# --- severity labelling and UNCLASSIFIED (2026-10: all severities are pushed) ---

def _sent_text(severity="High", **kwargs):
    from unittest.mock import MagicMock, patch
    from alerting.notify_telegram import send_alert
    with patch("alerting.notify_telegram.TELEGRAM_BOT_TOKEN", "t"), \
         patch("alerting.notify_telegram.TELEGRAM_CHAT_ID", "c"), \
         patch("alerting.notify_telegram.requests.post", return_value=MagicMock(status_code=200)) as post:
        send_alert("Oil prices jump", "energy", severity, "why", [], [{"source": "s", "url": "https://u"}], **kwargs)
    return post.call_args.kwargs["json"]["text"]


def test_each_severity_gets_its_own_label():
    assert "HIGH --" in _sent_text("High")
    assert "MEDIUM --" in _sent_text("Medium")
    assert "LOW --" in _sent_text("Low")


def test_classification_failed_push_is_labelled_unclassified_not_with_its_fallback_severity():
    text = _sent_text("Medium", classification_failed=True)
    assert "UNCLASSIFIED" in text
    assert "MEDIUM --" not in text


def test_escalation_label_names_the_new_severity():
    text = _sent_text("Medium", is_escalation=True)
    assert "ESCALATION (MEDIUM)" in text


# --- direction: which way each affected instrument would typically move ---

def _sent_text_for(affected, severity="High", **kwargs):
    from unittest.mock import MagicMock, patch
    from alerting.notify_telegram import send_alert
    with patch("alerting.notify_telegram.TELEGRAM_BOT_TOKEN", "t"), \
         patch("alerting.notify_telegram.TELEGRAM_CHAT_ID", "c"), \
         patch("alerting.notify_telegram.requests.post", return_value=MagicMock(status_code=200)) as post:
        send_alert("Strait of Hormuz closed", "energy", severity, "why", affected,
                   [{"source": "s", "url": "https://u"}], **kwargs)
    return post.call_args.kwargs["json"]["text"]


_WITH_LEANS = [
    {"symbol": "XAUUSD", "channel": "safe_haven", "lean": "buy",
     "lean_why": "safe-haven bid and inflation hedge on an oil-supply shock [convention]"},
    {"symbol": "US30", "channel": "risk_sentiment", "lean": "sell", "lean_why": "oil-supply shock weighs on risk appetite [convention]"},
    {"symbol": "EURUSD", "channel": "usd_relationship", "lean": "mixed",
     "lean_why": "gold's link to rate expectations has been unreliable since 2024 [Layer2]"},
]


def test_each_instrument_gets_its_own_buy_or_sell_off_or_no_lean_line():
    text = _sent_text_for(_WITH_LEANS)
    assert "XAUUSD (safe haven): \U0001F7E2 potential BUY" in text
    assert "US30 (risk sentiment): \U0001F534 potential SELL-OFF" in text
    assert "EURUSD (usd relationship): ⚪ no clear lean" in text
    assert "Typical reaction, not a trade signal." in text


def test_reason_is_shown_but_provenance_tags_are_not():
    text = _sent_text_for(_WITH_LEANS)
    assert "oil-supply shock weighs on risk appetite" in text
    assert "[convention]" not in text and "[Layer2]" not in text


def test_rows_stored_before_leans_existed_keep_the_compact_line():
    old = [{"symbol": "XAUUSD", "channel": "safe_haven"}, {"symbol": "US30", "channel": "risk_sentiment"}]
    text = _sent_text_for(old, is_escalation=True)
    assert "Affects: XAUUSD (safe_haven), US30 (risk_sentiment)" in text
    assert "trade signal" not in text


def test_no_tracked_instruments_still_says_so():
    assert "Affects: none currently tracked" in _sent_text_for([])
