"""
Convert the Cleveland Fed's published monthly nowcast history (nowcast_month.json) into the CSV that
scripts/backfill_tier1_reconstructed.py reads: event_title,release_utc,as_of_utc,value,source.

Structure of the source file (observed 2026-10-15, see docs/superpowers/specs/2026-10-15-stats-phase0-report.md):
a JSON list of FusionCharts objects, one per reference month (chart.subcaption "2026-7"). Each chart has
categories[0].category: a flat list mixing date labels ("07/01", no year) with vline release markers
("CPI Jun"); and a dataset of eight series, each with exactly one slot per DATE label (markers have no slot).
The "CPI Inflation" / "Core CPI Inflation" series hold one nowcast per business day; the "Actual CPI
Inflation" / "Actual Core CPI Inflation" series hold a value only on the release day, which is how the
release date is found. The nowcast slot on the release day itself is blank in the real file.

Rules (spec section 8: no hindsight):
  * A nowcast dated D is treated as available only at the END of day D (as_of = D 23:59:59 UTC), although the
    Fed publishes around 10:00 Eastern, so the usable snapshot never leaks intraday information.
  * Only values dated strictly before the release day are emitted (never the release-day slot).
  * Only releases that exist in our own event_history (title + same UTC date) are emitted, and release_utc is
    that row's own event_time_utc, so 12:30Z vs 13:30Z follows US daylight saving automatically and every
    CSV row joins to a real occurrence.
  * Every business-day value is emitted; the provider's "latest as_of <= release" picks the last one.

Data is CC BY 4.0 (Cleveland Fed); keep the attribution in the source column.

Usage:
    python scripts/cleveland_nowcast_to_csv.py nowcast_month.json nowcasts.csv --dash-db dashboard.db \
        [--since 2026-01-01] [--until 2027-01-01] [--download]
--download first fetches the JSON (one HTTP GET) to the given path, which must be OUTSIDE the repo.
Do not commit the JSON or the CSV.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sqlite3
import urllib.request
from pathlib import Path
from typing import Iterable, Optional

UTC = dt.timezone.utc
APP_ROOT = Path(__file__).resolve().parents[1]

SOURCE = "Cleveland Fed Inflation Nowcasting (CC BY 4.0)"
NOWCAST_URL = "https://www.clevelandfed.org/-/media/files/webcharts/inflationnowcasting/nowcast_month.json"
CSV_COLUMNS = ["event_title", "release_utc", "as_of_utc", "value", "source"]

# event_history title -> (nowcast series, actual series that marks the release day)
SERIES_MAP = {
    "CPI m/m": ("CPI Inflation", "Actual CPI Inflation"),
    "Core CPI m/m": ("Core CPI Inflation", "Actual Core CPI Inflation"),
}


def load_charts(json_path: Path) -> list[dict]:
    """Read a LOCAL copy of nowcast_month.json. Never touches the network."""
    with open(json_path, encoding="utf-8") as handle:
        return json.load(handle)


def download(dest: Path, url: str = NOWCAST_URL) -> Path:
    """One HTTP GET of the published file; only used by the CLI --download flag. Refuses paths inside the repo."""
    dest = Path(dest).resolve()
    if dest == APP_ROOT or APP_ROOT in dest.parents:
        raise ValueError(f"refusing to save the nowcast JSON inside the repo ({dest}); use a temp directory")
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "news_engine-stats-backfill/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:      # noqa: S310 -- fixed https URL
        dest.write_bytes(response.read())
    return dest


def load_known_occurrences(dash_db: Path) -> list[tuple[str, dt.datetime]]:
    """
    (title, event_time_utc) of every USD CPI-family row in event_history. Opened read-only (mode=ro).
    USD only, like the Stats tab: unattributed rows reuse US titles at unrelated times.
    """
    titles = list(SERIES_MAP)
    conn = sqlite3.connect(f"file:{Path(dash_db).resolve().as_posix()}?mode=ro", uri=True)
    try:
        marks = ",".join("?" for _ in titles)
        rows = conn.execute(
            f"SELECT DISTINCT event_title, event_time_utc FROM event_history "
            f"WHERE country = 'USD' AND event_title IN ({marks}) ORDER BY event_time_utc", titles).fetchall()
    finally:
        conn.close()
    return [(title, dt.datetime.fromisoformat(when).astimezone(UTC)) for title, when in rows]


def _date_labels(chart: dict) -> list[str]:
    """The "MM/DD" labels in order, skipping vline release markers (which own no data slot)."""
    return [item["label"] for item in chart["categories"][0]["category"] if "vline" not in item]


def _slot_dates(chart: dict) -> list[dt.date]:
    """Attach a year to each "MM/DD" label: the chart starts in its reference month; year rolls on a month decrease."""
    ref_year, ref_month = (int(part) for part in chart["chart"]["subcaption"].split("-"))
    labels = _date_labels(chart)
    first_month = int(labels[0][:2])
    if first_month != ref_month:
        raise ValueError(f"chart {chart['chart']['subcaption']} starts in month {first_month}, expected {ref_month}")
    year, previous_month, dates = ref_year, first_month, []
    for label in labels:
        month, day = int(label[:2]), int(label[3:5])
        if month < previous_month:
            year += 1
        previous_month = month
        dates.append(dt.date(year, month, day))
    return dates


def _series(chart: dict, name: str) -> list[str]:
    """Raw value strings ("" = blank slot) of one series."""
    for series in chart["dataset"]:
        if series["seriesname"] == name:
            return [str(point.get("value", "")).strip() for point in series["data"]]
    raise ValueError(f"series {name!r} missing from chart {chart['chart']['subcaption']}")


def convert(charts: Iterable[dict], known_occurrences: Iterable[tuple[str, dt.datetime]],
            since: dt.datetime, until: dt.datetime, source: str = SOURCE) -> list[dict]:
    """
    Rows for every (title, release) that is both published by the Fed and present in known_occurrences,
    with since <= release_utc < until. Pure: no file, DB or network access.
    """
    known: dict[tuple[str, dt.date], dt.datetime] = {}
    for title, when in known_occurrences:
        if when.tzinfo is None or when.utcoffset() is None:
            raise ValueError(f"known occurrence {title!r} {when!r} must be timezone-aware")
        when = when.astimezone(UTC)
        key = (title, when.date())
        if key not in known or when < known[key]:
            known[key] = when

    rows: list[dict] = []
    for chart in charts:
        for title, (nowcast_name, actual_name) in SERIES_MAP.items():
            actuals = _series(chart, actual_name)
            released = [i for i, value in enumerate(actuals) if value != ""]
            if not released:
                continue                                   # not released yet (or never, e.g. Oct 2025): nothing to attach
            if len(released) > 1:
                raise ValueError(f"{actual_name} has {len(released)} values in chart {chart['chart']['subcaption']}")
            dates = _slot_dates(chart)
            nowcasts = _series(chart, nowcast_name)
            if len(nowcasts) != len(dates) or len(actuals) != len(dates):
                raise ValueError(f"chart {chart['chart']['subcaption']}: series length does not match its date labels")
            release_date = dates[released[0]]
            release_utc = known.get((title, release_date))
            if release_utc is None or not (since <= release_utc < until):
                continue
            for date, value in zip(dates, nowcasts):
                if value == "" or date >= release_date:    # blank slot, or release day / later: never emitted
                    continue
                as_of = dt.datetime.combine(date, dt.time(23, 59, 59), tzinfo=UTC)
                rows.append({"event_title": title, "release_utc": release_utc.isoformat(),
                             "as_of_utc": as_of.isoformat(), "value": value, "source": source})
    rows.sort(key=lambda r: (r["release_utc"], r["event_title"], r["as_of_utc"]))
    return rows


def write_csv(rows: Iterable[dict], csv_path: Path) -> int:
    count = 0
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def _parse_day(text: str) -> dt.datetime:
    return dt.datetime.fromisoformat(text).replace(tzinfo=UTC)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("json_path", type=Path, help="local copy of nowcast_month.json (outside the repo)")
    parser.add_argument("csv_path", type=Path, help="CSV to write (outside the repo)")
    parser.add_argument("--dash-db", type=Path, required=True, help="dashboard.db to read event_history from (opened read-only)")
    parser.add_argument("--since", default="2026-01-01", help="first release day, UTC, inclusive")
    parser.add_argument("--until", default="2027-01-01", help="last release day, UTC, exclusive")
    parser.add_argument("--download", action="store_true", help="fetch the JSON to json_path first (one HTTP GET)")
    args = parser.parse_args(argv)
    if args.download:
        download(args.json_path)
    known = load_known_occurrences(args.dash_db)
    rows = convert(load_charts(args.json_path), known, _parse_day(args.since), _parse_day(args.until))
    count = write_csv(rows, args.csv_path)
    releases = {(r["event_title"], r["release_utc"]) for r in rows}
    print(f"wrote {count} rows for {len(releases)} releases to {args.csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
