"""Telegram Bot API push for High-severity shock alerts only."""
from __future__ import annotations

import time
from typing import Optional

import requests

from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

_MAX_ATTEMPTS = 3
_BASE_DELAY_SECONDS = 0.1  # small on purpose -- doubles each retry, kept tiny so tests stay fast


def _sleep(seconds: float) -> None:
    """Isolated seam so tests can monkeypatch this to a no-op and run fast."""
    time.sleep(seconds)


def send_alert(
    headline: str, category: str, severity: str, rationale: Optional[str],
    affected_symbols: list[dict], sources: list[dict],
) -> bool:
    """
    Returns True on a confirmed 200 from Telegram's API, False on any
    failure (missing config, network error, non-200) -- never raises.
    The alert row must already be persisted by the caller (alerting/
    poll_once.py) before this is called, so a False return here never
    means a lost alert -- the caller records delivery_status separately.

    Retries up to _MAX_ATTEMPTS total attempts, with a small exponential
    backoff, on a `requests.RequestException` or a 5xx response -- both
    plausibly transient. A non-5xx failure response (e.g. 401/400 -- a
    client/auth error) is NOT retried since retrying can't help and would
    just delay the caller for no benefit.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[notify_telegram] WARNING: TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set -- skipping push")
        return False

    symbols_line = ", ".join(f"{s['symbol']} ({s['channel']})" for s in affected_symbols) or "none currently tracked"
    source_line = sources[0]["url"] if sources else ""
    text = (
        f"\U0001F6A8 HIGH -- {category}\n"
        f"{headline}\n"
        f"Affects: {symbols_line}\n"
        f"{rationale or ''}\n"
        f"{source_line}"
    ).strip()

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    delay = _BASE_DELAY_SECONDS
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            resp = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=10)
        except requests.RequestException as exc:
            print(f"[notify_telegram] WARNING: send failed (attempt {attempt}/{_MAX_ATTEMPTS}): {exc}")
            if attempt == _MAX_ATTEMPTS:
                return False
            _sleep(delay)
            delay *= 2
            continue

        if resp.status_code == 200:
            return True
        if resp.status_code < 500:
            # Client/auth error -- retrying won't help, fail fast.
            return False
        print(f"[notify_telegram] WARNING: send failed (attempt {attempt}/{_MAX_ATTEMPTS}): HTTP {resp.status_code}")
        if attempt == _MAX_ATTEMPTS:
            return False
        _sleep(delay)
        delay *= 2

    return False
