"""Records a LIVE Cleveland nowcast snapshot (spec §6.1 Freshness). Called by the research task."""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path
from typing import Optional

# Allow `python scripts/capture_nowcast_snapshot.py ...` (script dir, not the app root, is on sys.path).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scoring import backtest_store  # noqa: E402

_OFFSET_HINT = "timestamps must include a UTC offset, e.g. 2026-11-12T13:30:00+00:00"


def parse_aware(text: str) -> dt.datetime:
    """Parse an ISO-8601 timestamp that must carry a UTC offset (naive input is refused)."""
    parsed = dt.datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(_OFFSET_HINT)
    return parsed


def capture(conn, event_title: str, release_utc: dt.datetime, value: float,
            as_of_utc: Optional[dt.datetime] = None, source: str = "cleveland_fed_nowcast") -> int:
    # Check awareness here so a naive value raises ValueError, not the TypeError Python gives
    # when it compares naive with aware datetimes below.
    if release_utc.tzinfo is None or release_utc.utcoffset() is None:
        raise ValueError(f"release_utc must be timezone-aware, got naive {release_utc!r}")
    as_of = as_of_utc or dt.datetime.now(dt.timezone.utc)
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError(f"as_of_utc must be timezone-aware, got naive {as_of!r}")
    if as_of > release_utc:
        raise ValueError("as_of_utc is after the release: a snapshot taken after the print cannot be scored")
    return backtest_store.record_nowcast_snapshot(conn, event_title, release_utc, value, as_of, source, "live")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", required=True)
    parser.add_argument("--release", required=True, help="release time with UTC offset, e.g. 2026-11-12T13:30:00+00:00")
    parser.add_argument("--value", required=True, type=float)
    parser.add_argument("--as-of", help="snapshot time with UTC offset; defaults to now (UTC)")
    parser.add_argument("--source", default="cleveland_fed_nowcast")
    args = parser.parse_args()
    try:
        release_utc = parse_aware(args.release)
        as_of_utc = parse_aware(args.as_of) if args.as_of else None
    except ValueError as exc:
        parser.error(str(exc))
    row_id = capture(
        backtest_store.get_connection(), args.event, release_utc, args.value, as_of_utc, args.source)
    print(f"recorded snapshot id={row_id}")


if __name__ == "__main__":
    main()
