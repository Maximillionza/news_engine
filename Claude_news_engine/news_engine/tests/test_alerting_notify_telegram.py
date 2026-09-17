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
