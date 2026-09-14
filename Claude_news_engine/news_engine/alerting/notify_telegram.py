"""Telegram Bot API push for High-severity shock alerts only."""
from __future__ import annotations

from typing import Optional

import requests

from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


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
    try:
        resp = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=10)
        return resp.status_code == 200
    except requests.RequestException as exc:
        print(f"[notify_telegram] WARNING: send failed: {exc}")
        return False
