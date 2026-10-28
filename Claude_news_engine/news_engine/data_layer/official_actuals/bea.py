"""
Bureau of Economic Analysis NIPA adapter (ACT Task 1).

GET https://apps.bea.gov/api/data with UserID, method=GetData,
datasetname=NIPA, TableName, Frequency (Q | M), Year (comma list),
ResultFormat=JSON. Result: {SeriesCode: {period: value}}; `TimePeriod`
"2026Q2" -> 2026-04-01, "2026M08" -> 2026-08-01. `DataValue` carries
thousands separators ("27,626,933"); "(NA)"-style cells are skipped.

BEA answers errors with HTTP 200 and an `Error` object. A rejected UserID
raises KeyInactiveError: live BEA (checked 2026-10-28) answers a made-up key
with APIErrorCode 1 and "Invalid Request - Invalid API UserId.", so the
description is matched as well as the documented code 3. Code 1 alone is not
enough (BEA uses it for every "Invalid Request - ..." error); any other
error raises SourceError.
BEA echoes the key back in Request.RequestParam (USERID), so a body must
never be logged or saved unscrubbed.

The table's own note (`Results.Notes`, NoteRef == TableName) ends with
"- LastRevised: September 30, 2026": the day BEA last published the table,
which proves a GDP re-estimate is out even when its value did not change.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from typing import Optional, Sequence

from data_layer.official_actuals.http import Fetcher, KeyInactiveError, SourceError, call

BEA_URL = "https://apps.bea.gov/api/data"
_BEA_INVALID_USER_ID = "3"
_LAST_REVISED = re.compile(r"LastRevised:\s*([A-Za-z]+\s+\d{1,2},\s*\d{4})")


def _period(text: str) -> Optional[dt.date]:
    m = re.fullmatch(r"(\d{4})(?:Q([1-4])|M(\d{2}))", text.strip())
    if not m:
        return None
    year = int(m.group(1))
    month = 3 * (int(m.group(2)) - 1) + 1 if m.group(2) else int(m.group(3))
    return dt.date(year, month, 1) if 1 <= month <= 12 else None


def _error(payload: dict) -> Optional[dict]:
    root = payload.get("BEAAPI") or {}
    err = root.get("Error") or (root.get("Results") or {}).get("Error")
    if isinstance(err, list):
        err = err[0] if err else None
    return err if isinstance(err, dict) else None


def parse_nipa(body: str) -> dict[str, dict[dt.date, float]]:
    try:
        payload = json.loads(body)
    except ValueError:
        raise SourceError("bea: unparseable body") from None
    if not isinstance(payload, dict):
        raise SourceError("bea: unparseable body")
    err = _error(payload)
    if err is not None:
        code = str(err.get("APIErrorCode", "")).strip()
        description = str(err.get("APIErrorDescription", "")).lower()
        if code == _BEA_INVALID_USER_ID or "userid" in description:
            raise KeyInactiveError("bea: UserID rejected")
        raise SourceError(f"bea: API error {code or 'unknown'}")
    data = ((payload.get("BEAAPI") or {}).get("Results") or {}).get("Data")
    if not isinstance(data, list):
        raise SourceError("bea: no Data in answer")
    out: dict[str, dict[dt.date, float]] = {}
    for row in data:
        try:
            period = _period(str(row["TimePeriod"]))
            value = float(str(row["DataValue"]).replace(",", ""))
            code = str(row["SeriesCode"])
        except (KeyError, TypeError, ValueError):
            continue
        if period is not None:
            out.setdefault(code, {})[period] = value
    return out


def parse_last_revised(body: str, table: str) -> Optional[dt.date]:
    """The "LastRevised" date of `table`'s own note; None when the note is absent or unparseable."""
    try:
        notes = ((json.loads(body).get("BEAAPI") or {}).get("Results") or {}).get("Notes") or []
    except (ValueError, AttributeError):
        return None
    for note in notes if isinstance(notes, list) else []:
        if not isinstance(note, dict) or str(note.get("NoteRef", "")).strip() != table:
            continue
        m = _LAST_REVISED.search(str(note.get("NoteText", "")))
        if m:
            try:
                return dt.datetime.strptime(" ".join(m.group(1).replace(",", ", ").split()), "%B %d, %Y").date()
            except ValueError:
                return None
    return None


def fetch_nipa_table(table: str, frequency: str, years: Sequence[int], key: str,
                     fetcher: Fetcher) -> tuple[dict[str, dict[dt.date, float]], Optional[dt.date]]:
    """`fetch_nipa` plus the table's LastRevised date (one call)."""
    if not key:
        raise KeyInactiveError("bea: no key configured")
    params = {
        "UserID": key, "method": "GetData", "datasetname": "NIPA", "TableName": table,
        "Frequency": frequency, "Year": ",".join(str(y) for y in years), "ResultFormat": "JSON",
    }
    resp = call(fetcher, "bea", "GET", BEA_URL, params)
    return parse_nipa(resp.text), parse_last_revised(resp.text, table)


def fetch_nipa(table: str, frequency: str, years: Sequence[int], key: str, fetcher: Fetcher) -> dict[str, dict[dt.date, float]]:
    """Every series of one NIPA table at one frequency, keyed by BEA SeriesCode."""
    return fetch_nipa_table(table, frequency, years, key, fetcher)[0]
