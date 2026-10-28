"""
The one HTTP seam for every official-actuals adapter (ACT Task 1).

A `Fetcher` is `(method, url, params, json_body) -> HttpResponse`. The real
one (`requests_fetcher`) sends a fixed User-Agent and turns every requests
exception into `SourceTransportError(<exception class name>)`: a requests
error string embeds the full URL, and the URL carries the API key, so the
original message is dropped (`from None`). Tests pass a fake fetcher backed
by recorded fixtures.

`check_status` runs before any parse: 429 and 5xx are rate-limit/back-off
signals (`SourceRateLimited`, with a parsed Retry-After), any other 4xx is a
plain `SourceError`.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Callable, Optional

import requests

USER_AGENT = "news-engine/ACT official-actuals poller"
_BOM = chr(0xFEFF)     # byte-order mark some publishers prepend


@dataclass(frozen=True)
class HttpResponse:
    status: int
    text: str
    headers: dict[str, str]


class SourceError(RuntimeError):
    """Any publisher failure. The message never contains a URL, query or key."""


class SourceTransportError(SourceError):
    """No HTTP answer at all (timeout, DNS failure, connection reset)."""


class SourceRateLimited(SourceError):
    """HTTP 429 or 5xx (or a publisher's own quota message): back off, retry later."""

    def __init__(self, message: str, retry_after_seconds: Optional[float] = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class KeyInactiveError(SourceError):
    """The API key is missing, invalid or not yet activated by the publisher."""


Fetcher = Callable[[str, str, Optional[dict], Optional[dict]], HttpResponse]


def requests_fetcher(timeout_seconds: float = 20.0) -> Fetcher:
    """The production fetcher: one `requests.request` per call, errors reduced to their class name."""

    def fetch(method: str, url: str, params: Optional[dict], json_body: Optional[dict]) -> HttpResponse:
        try:
            resp = requests.request(
                method, url, params=params, json=json_body,
                headers={"User-Agent": USER_AGENT}, timeout=timeout_seconds,
            )
        except Exception as exc:  # noqa: BLE001 — the message would carry the URL (and key)
            raise SourceTransportError(type(exc).__name__) from None
        headers = dict(resp.headers)
        # No declared charset (the Fed RSS) makes requests fall back to ISO-8859-1; every publisher here sends UTF-8.
        if "charset" not in (_header(headers, "Content-Type") or "").lower():
            resp.encoding = "utf-8"
        return HttpResponse(resp.status_code, resp.text.lstrip(_BOM), headers)

    return fetch


def call(fetcher: Fetcher, source: str, method: str, url: str,
         params: Optional[dict] = None, json_body: Optional[dict] = None, check: bool = True) -> HttpResponse:
    """Run `fetcher` (then `check_status` unless `check` is False, for adapters that read a key
    error out of a 4xx body first); any non-SourceError a custom fetcher raises is reduced to its class name."""
    try:
        resp = fetcher(method, url, params, json_body)
    except SourceError:
        raise
    except Exception as exc:  # noqa: BLE001 — same leak rule as requests_fetcher
        raise SourceTransportError(f"{source}: {type(exc).__name__}") from None
    if check:
        check_status(resp, source)
    return resp


def _header(headers: dict[str, str], name: str) -> Optional[str]:
    wanted = name.lower()
    for key, value in (headers or {}).items():
        if key.lower() == wanted:
            return value
    return None


def _retry_after_seconds(raw: Optional[str], now: Optional[dt.datetime] = None) -> Optional[float]:
    """Retry-After as delta-seconds or an HTTP date; anything unparseable -> None."""
    if raw is None:
        return None
    text = raw.strip()
    try:
        return max(0.0, float(text))
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=dt.timezone.utc)
    now = now or dt.datetime.now(dt.timezone.utc)
    return max(0.0, (when - now).total_seconds())


def check_status(resp: HttpResponse, source: str) -> None:
    """Raise for a non-2xx answer: 429/5xx -> SourceRateLimited, other 4xx -> SourceError."""
    status = resp.status
    if status == 429 or status >= 500:
        raise SourceRateLimited(f"{source}: HTTP {status}", _retry_after_seconds(_header(resp.headers, "Retry-After")))
    if status >= 400:
        raise SourceError(f"{source}: HTTP {status}")
