"""
TreasuryDirect auction results adapter (ACT Task 1).

GET https://www.treasurydirect.gov/TA_WS/securities/auctioned?format=json&type=<Note|Bond>&days=<n>.
Forex Factory's "10-y Bond Auction" covers the original 10-year issue AND its
reopenings (securityTerm "9-Year 11-Month", originalSecurityTerm "10-Year")
but not TIPS, so rows are kept on `originalSecurityTerm == term`,
`type != "TIPS"` and a non-empty high yield and bid-to-cover ratio (an
auction not yet closed has neither). Result: {competitiveAuctionCloseDate:
(high yield %, bid-to-cover)}. No key.
"""
from __future__ import annotations

import datetime as dt
import json

from data_layer.official_actuals.http import Fetcher, SourceError, call

TREASURY_URL = "https://www.treasurydirect.gov/TA_WS/securities/auctioned"


def parse_auctions(body: str, original_term: str) -> dict[dt.date, tuple[float, float]]:
    try:
        rows = json.loads(body)
    except ValueError:
        raise SourceError("treasury: unparseable body") from None
    if not isinstance(rows, list):
        raise SourceError("treasury: unexpected answer")
    out: dict[dt.date, tuple[float, float]] = {}
    for row in rows:
        try:
            if row.get("originalSecurityTerm") != original_term or row.get("type") == "TIPS":
                continue
            high_yield, cover = str(row.get("highYield") or ""), str(row.get("bidToCoverRatio") or "")
            if not high_yield or not cover:
                continue
            day = dt.date.fromisoformat(str(row["competitiveAuctionCloseDate"])[:10])
            out[day] = (float(high_yield), float(cover))
        except (AttributeError, KeyError, TypeError, ValueError):
            continue
    return out


def fetch_auctions(original_term: str, security_type: str, fetcher: Fetcher, days: int = 400) -> dict[dt.date, tuple[float, float]]:
    """Closed auctions of one original term (reopenings included, TIPS excluded) in the last `days` days."""
    resp = call(fetcher, "treasury", "GET", TREASURY_URL, {"format": "json", "type": security_type, "days": days})
    return parse_auctions(resp.text, original_term)
