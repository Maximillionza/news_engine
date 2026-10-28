"""
One fetch for many registry specs (ACT Task 2).

Specs are grouped by publisher request so a burst of titles costs as few
calls as possible: one BLS POST for every BLS series (50 per POST inside the
adapter), one BEA call per table/frequency, one Census call per program, one
EIA or FRED call per series, one Fed call, one Treasury call per security
type. Data comes back flat, keyed by `series_key(spec)`, as {period: value}
in source units, ready for `registry.value_for`.

Failures never raise: each publisher request that fails puts its
`SourceError` in `errors[source]` and its specs get no data entry, while the
other sources' data is still returned (one publisher down never blocks the
rest). A request that succeeds but lacks a series yields an empty mapping,
which the fill rule reads as "awaiting publication" (fail closed).
"""
from __future__ import annotations

import datetime as dt
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from data_layer.official_actuals.bea import fetch_nipa
from data_layer.official_actuals.bls import BlsSeries, fetch_bls
from data_layer.official_actuals.census import fetch_eits
from data_layer.official_actuals.eia import fetch_eia_weekly
from data_layer.official_actuals.fed import fetch_fomc_upper_bounds
from data_layer.official_actuals.fred_current import fetch_fred_current
from data_layer.official_actuals.http import Fetcher, SourceError, call
from data_layer.official_actuals.keys import Keys
from data_layer.official_actuals.registry import OfficialSpec
from data_layer.official_actuals.treasury import TREASURY_URL, parse_auctions

# Reach back before `since` so prior-period changes and y/y bases are inside the data.
FETCH_LOOKBACK_DAYS = 400
_BLS_FIELDS = {"level": "levels", "pct1": "pct1", "pct12": "pct12"}


@dataclass(frozen=True)
class FetchOutcome:
    data: dict[str, dict[dt.date, Any]]          # keyed by series_key(spec)
    errors: dict[str, SourceError]               # keyed by source


def series_key(spec: OfficialSpec) -> str:
    """One data entry per (source, series, field): titles sharing a spec share the fetch."""
    return f"{spec.source}:{spec.series}:{spec.field}"


def _today() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).date()


def fetch_for_specs(specs: Iterable[OfficialSpec], since: dt.date, fetcher: Fetcher, keys: Keys) -> FetchOutcome:
    """Every spec's series from `since - FETCH_LOOKBACK_DAYS` on, grouped into as few requests as possible."""
    unique = list({series_key(s): s for s in specs}.values())
    start = since - dt.timedelta(days=FETCH_LOOKBACK_DAYS)
    today = max(_today(), since)
    data: dict[str, dict[dt.date, Any]] = {}
    errors: dict[str, SourceError] = {}
    by_source: dict[str, list[OfficialSpec]] = defaultdict(list)
    for spec in unique:
        by_source[spec.source].append(spec)

    def attempt(source: str, request: Callable[[], None]) -> None:
        try:
            request()
        except SourceError as exc:
            errors[source] = exc                 # last error of the source wins; earlier groups keep their data

    if by_source.get("bls"):
        bls_specs = by_source["bls"]

        def bls_request() -> None:
            got = fetch_bls([s.series for s in bls_specs], keys.bls, fetcher, start.year, today.year)
            for s in bls_specs:
                parsed = got.get(s.series, BlsSeries())
                data[series_key(s)] = dict(getattr(parsed, _BLS_FIELDS[s.field]))

        attempt("bls", bls_request)

    bea_groups: dict[tuple[str, str], list[OfficialSpec]] = defaultdict(list)
    for s in by_source.get("bea", []):
        table, frequency, _code = s.series.split(":")
        bea_groups[(table, frequency)].append(s)
    for (table, frequency), group in bea_groups.items():
        def bea_request(table: str = table, frequency: str = frequency, group: list[OfficialSpec] = group) -> None:
            got = fetch_nipa(table, frequency, list(range(start.year, today.year + 1)), keys.bea, fetcher)
            for s in group:
                data[series_key(s)] = dict(got.get(s.series.split(":")[2], {}))

        attempt("bea", bea_request)

    census_groups: dict[str, list[OfficialSpec]] = defaultdict(list)
    for s in by_source.get("census", []):
        census_groups[s.series.split(":")[0]].append(s)
    for program, group in census_groups.items():
        def census_request(program: str = program, group: list[OfficialSpec] = group) -> None:
            got = fetch_eits(program, keys.census, fetcher, start)
            for s in group:
                _program, category, data_type = s.series.split(":")
                data[series_key(s)] = dict(got.get((category, data_type), {}))

        attempt("census", census_request)

    weeks = (today - start).days // 7 + 2
    for s in by_source.get("eia", []):
        def eia_request(s: OfficialSpec = s) -> None:
            route, series_id = s.series.rsplit(":", 1)
            data[series_key(s)] = fetch_eia_weekly(route, series_id, keys.eia, fetcher, length=weeks)

        attempt("eia", eia_request)

    if by_source.get("fed"):
        fed_specs = by_source["fed"]

        def fed_request() -> None:
            got = fetch_fomc_upper_bounds(fetcher, start)
            for s in fed_specs:
                data[series_key(s)] = dict(got)

        attempt("fed", fed_request)

    treasury_groups: dict[str, list[OfficialSpec]] = defaultdict(list)
    for s in by_source.get("treasury", []):
        treasury_groups[s.series.split(":")[0]].append(s)
    for security_type, group in treasury_groups.items():
        def treasury_request(security_type: str = security_type, group: list[OfficialSpec] = group) -> None:
            params = {"format": "json", "type": security_type, "days": (today - start).days}
            resp = call(fetcher, "treasury", "GET", TREASURY_URL, params)
            for s in group:
                data[series_key(s)] = parse_auctions(resp.text, s.series.split(":", 1)[1])

        attempt("treasury", treasury_request)

    for s in by_source.get("fred", []):
        def fred_request(s: OfficialSpec = s) -> None:
            data[series_key(s)] = fetch_fred_current(s.series, keys.fred, fetcher, start)

        attempt("fred", fred_request)

    unknown = set(by_source) - {"bls", "bea", "census", "eia", "fed", "treasury", "fred"}
    for source in sorted(unknown):
        errors[source] = SourceError(f"{source}: no adapter")
    return FetchOutcome(data, errors)
