"""
End-to-end live check.

Fetches this week's high-impact USD calendar events from Forex Factory,
and for any event currently inside its pre-event window, pulls news from
the free RSS sources (Reuters, CNBC, Investing.com) — plus Alpha Vantage
too, automatically, if ALPHA_VANTAGE_API_KEY is set in .env — and scores
XAUUSD.

No API keys are required to start; this still runs RSS-only without one.
Run it with:

    python scripts/run_live_check.py

If nothing prints under "Events in active pre-event window", it means no
tracked high-impact USD event is currently within PRE_EVENT_WINDOW_HOURS
of now — check config/settings.py or try again closer to a scheduled
release (NFP, CPI, FOMC, etc.)
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import ALPHA_VANTAGE_API_KEY
from data_layer.calendar_feed import fetch_calendar, filter_relevant_events, events_in_pre_window
from data_layer.event_context import build_event_news_bundle
from data_layer.rss_sources import build_all_preview_sources
from scoring.probability_engine import score_bundle


def main():
    print("Fetching this week's Forex Factory calendar...")
    all_events = fetch_calendar("thisweek")
    high_impact_usd = filter_relevant_events(all_events)
    print(f"  {len(all_events)} total events, {len(high_impact_usd)} high-impact USD events\n")

    active = events_in_pre_window(high_impact_usd)
    if not active:
        print("No high-impact USD events currently in their pre-event window.")
        print("Upcoming high-impact USD events this week:")
        for e in high_impact_usd:
            print(f"  {e}  (watch from {e.watch_from_local.strftime('%Y-%m-%d %H:%M %Z')})")
        return

    print(f"Events in active pre-event window: {len(active)}\n")
    sources = build_all_preview_sources()
    source_note = "RSS + Alpha Vantage" if ALPHA_VANTAGE_API_KEY else "RSS only (no ALPHA_VANTAGE_API_KEY set)"
    print(f"Sources: {source_note}\n")

    for event in active:
        print(f"--- {event.title} ({event.event_time_local.strftime('%Y-%m-%d %H:%M %Z')}) ---")
        bundle = build_event_news_bundle(event, sources, query="", mode="live")
        print(f"  {len(bundle.articles)} articles pulled")

        result = score_bundle(bundle, "XAUUSD")
        print(f"  {result.summary()}")
        if result.contradiction_flag:
            print(f"  NOTE: {result.contradiction_note}")
        print()


if __name__ == "__main__":
    main()
