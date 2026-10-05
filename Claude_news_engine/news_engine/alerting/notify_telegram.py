"""
Telegram Bot API push for shock alerts. Originally High-only; 2026-10: all
severities are pushed (poll_once.py's TELEGRAM_MIN_SEVERITY decides the
floor), each labelled so a Medium/Low is visually distinct from a High.
"""
from __future__ import annotations

import re
import time
from typing import Optional

import requests

from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

_MAX_ATTEMPTS = 3
_BASE_DELAY_SECONDS = 0.1  # small on purpose -- doubles each retry, kept tiny so tests stay fast

_SEVERITY_PREFIX = {
    "High": "\U0001F6A8 HIGH",
    "Medium": "⚠️ MEDIUM",
    "Low": "ℹ️ LOW",
}


_LEAN_LABEL = {
    "buy": "\U0001F7E2 potential BUY",
    "sell": "\U0001F534 potential SELL-OFF",
    "mixed": "⚪ no clear lean",
}
_PROVENANCE_TAG = re.compile(r"\s*\[(?:convention|Layer2)\]")


def _affects_block(affected_symbols: list[dict]) -> str:
    """
    With lean data (alerting/direction.py): one line per instrument saying
    which way it would typically move, plus a not-a-signal disclaimer.
    Rows stored before leans existed have no "lean" key and keep the old
    compact one-line form, so escalation pushes for old alerts still work.
    """
    if not affected_symbols:
        return "Affects: none currently tracked"
    if not any("lean" in s for s in affected_symbols):
        return "Affects: " + ", ".join(f"{s['symbol']} ({s['channel']})" for s in affected_symbols)
    lines = ["Affects:"]
    for s in affected_symbols:
        label = _LEAN_LABEL.get(s.get("lean"), _LEAN_LABEL["mixed"])
        why = _PROVENANCE_TAG.sub("", s.get("lean_why") or "")
        channel = s["channel"].replace("_", " ")
        lines.append(f"  {s['symbol']} ({channel}): {label}" + (f" -- {why}" if why else ""))
    lines.append("Typical reaction, not a trade signal.")
    return "\n".join(lines)


def _sleep(seconds: float) -> None:
    """Isolated seam so tests can monkeypatch this to a no-op and run fast."""
    time.sleep(seconds)


def send_alert(
    headline: str, category: str, severity: str, rationale: Optional[str],
    affected_symbols: list[dict], sources: list[dict], is_escalation: bool = False,
    classification_failed: bool = False,
) -> bool:
    """
    Returns True on a confirmed 200 from Telegram's API, False on any
    failure (missing config, network error, non-200) -- never raises.
    The alert row must already be persisted by the caller (alerting/
    poll_once.py) before this is called, so a False return here never
    means a lost alert -- the caller records delivery_status separately.

    is_escalation=True labels the push as an update to an ALREADY-KNOWN
    story that just got reassessed as more severe (e.g. Medium -> High),
    rather than a brand-new event -- poll_once.py sets this when a
    dedup-matched corroborating article's own severity exceeds the
    existing alert's stored severity. Wording only; delivery/retry
    behavior is identical either way.

    classification_failed=True labels the push UNCLASSIFIED: every LLM
    provider failed, so `severity` is just the Medium fallback and the
    reader should judge the headline themselves rather than trust it.

    Retries up to _MAX_ATTEMPTS total attempts, with a small exponential
    backoff, on a `requests.RequestException` or a 5xx response -- both
    plausibly transient. A non-5xx failure response (e.g. 401/400 -- a
    client/auth error) is NOT retried since retrying can't help and would
    just delay the caller for no benefit.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[notify_telegram] WARNING: TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set -- skipping push")
        return False

    affects_block = _affects_block(affected_symbols)
    source_line = sources[0]["url"] if sources else ""
    if is_escalation:
        prefix = f"⬆️ ESCALATION ({severity.upper()})"
    elif classification_failed:
        prefix = "❓ UNCLASSIFIED (needs review)"
    else:
        prefix = _SEVERITY_PREFIX.get(severity, f"{severity.upper()}")
    text = (
        f"{prefix} -- {category}\n"
        f"{headline}\n"
        f"{affects_block}\n"
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
