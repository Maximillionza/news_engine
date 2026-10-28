"""
Federal Reserve FOMC decision adapter (ACT Task 1).

Reads the monetary-policy press-release RSS feed, keeps the items titled
exactly "Federal Reserve issues FOMC statement" (never minutes, discount-rate
minutes or projections), fetches each statement page and parses the target
range sentence. Result: {statement date in New York: upper bound in %}.

Statement pages may put markup inside the sentence (2026-09-16:
"point<strong> </strong>to 3-3/4<strong> </strong>to 4 percent"), so tags are
stripped and whitespace collapsed before the match. Fractions: "3-3/4" ->
3.75, "1/4" -> 0.25. Links are followed only on www.federalreserve.gov.
"""
from __future__ import annotations

import datetime as dt
import html
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from typing import Optional
from zoneinfo import ZoneInfo

from data_layer.official_actuals.http import Fetcher, SourceError, call

FED_RSS_URL = "https://www.federalreserve.gov/feeds/press_monetary.xml"
FED_SITE_PREFIX = "https://www.federalreserve.gov/"
FOMC_STATEMENT_TITLE = "Federal Reserve issues FOMC statement"
_NY = ZoneInfo("America/New_York")

_NUMBER = r"(\d+(?:-\d/\d)?|\d/\d)"
# Bounded gap (no sentence end) so a later sentence's "X to Y percent" can never be borrowed.
_TARGET_RANGE = re.compile(
    r"target range for the federal funds rate[^.]{0,200}?" + _NUMBER + r"\s+to\s+" + _NUMBER + r"\s+percent",
    re.S | re.I,
)
_TAG = re.compile(r"<[^>]+>")


def _to_float(text: str) -> float:
    """"3-3/4" -> 3.75, "1/4" -> 0.25, "4" -> 4.0."""
    whole, _, frac = text.partition("-")
    if "/" in whole:                     # bare fraction
        whole, frac = "0", whole
    value = float(whole)
    if frac:
        num, den = frac.split("/")
        value += float(num) / float(den)
    return value


def parse_target_range(page: str) -> Optional[tuple[float, float]]:
    """(lower, upper) of the first target-range sentence on a statement page, else None."""
    text = re.sub(r"\s+", " ", html.unescape(_TAG.sub(" ", page)))
    m = _TARGET_RANGE.search(text)
    if not m:
        return None
    return _to_float(m.group(1)), _to_float(m.group(2))


def _statement_items(rss: str) -> list[tuple[str, dt.date]]:
    start = rss.find("<")
    try:
        root = ET.fromstring(rss[start:] if start >= 0 else rss)
    except ET.ParseError:
        raise SourceError("fed: unparseable RSS") from None
    items: list[tuple[str, dt.date]] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        if title != FOMC_STATEMENT_TITLE or not link.startswith(FED_SITE_PREFIX):
            continue
        try:
            when = parsedate_to_datetime(pub)
        except (TypeError, ValueError):
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=dt.timezone.utc)
        items.append((link, when.astimezone(_NY).date()))
    return items


def fetch_fomc_upper_bounds(fetcher: Fetcher, since: dt.date) -> dict[dt.date, float]:
    """Upper bound of the target range for every FOMC statement dated `since` or later."""
    resp = call(fetcher, "fed", "GET", FED_RSS_URL)
    out: dict[dt.date, float] = {}
    for link, statement_date in _statement_items(resp.text):
        if statement_date < since:
            continue
        page = call(fetcher, "fed", "GET", link)
        parsed = parse_target_range(page.text)
        if parsed is not None:
            out[statement_date] = parsed[1]
    return out
