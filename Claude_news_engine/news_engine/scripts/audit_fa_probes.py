"""
Reproducible probes behind docs/fundamental-analysis-audit-2026-10-16.md.

Read-only: no network, no DB writes. Feeds hand-written headlines and
calendar rows through the engine's REAL code paths (lexicon sentiment,
FOMC relevance filter, shock triage, shock symbol relevance,
usd_surprise_score) and prints what each one does with non-USD and
trade-flow news. Re-run after any fix to confirm the finding is closed.

    python scripts/audit_fa_probes.py
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alerting.symbol_relevance import affected_symbols
from alerting.triage import triage_article
from data_layer import event_context
from data_layer.calendar_feed import EconomicEvent
from data_layer.news_feed import NewsArticle
from scoring.sentiment import score_article_text

_NOW = dt.datetime.now(dt.timezone.utc)

# Probe 1 -- foreign central-bank headlines vs. the FOMC relevance filter + USD lexicon.
# Correct USD sign in brackets: a dovish foreign CB is USD-SUPPORTIVE, a hawkish one USD-NEGATIVE.
FOREIGN_CB_HEADLINES: list[tuple[str, str, str]] = [
    ("ECB signals faster rate cuts as euro zone stalls", "Lagarde said the central bank is ready to ease further.", "+"),
    ("Bank of England delivers surprise rate cut", "The BoE cut rates by 50bp citing weak growth.", "+"),
    ("Bank of Japan hawkish, signals rate hike in December", "Ueda said the central bank could raise rates.", "-"),
    ("RBA holds, warns rate hike possible", "Australia's central bank kept rates on hold.", "-"),
]

# Probe 2 -- non-USD / trade-flow shocks vs. real-time triage and symbol relevance.
SHOCK_HEADLINES: list[tuple[str, str]] = [
    ("US slows soybean exports to Japan amid shipping dispute", "Grain shipments to Japanese buyers fell 40%."),
    ("China halts US soybean purchases in retaliation", "Beijing told state buyers to stop buying American soybeans."),
    ("Bank of Japan raises rates to 1%, yen surges", "The BoJ hiked its policy rate in a surprise move."),
    ("Japan LNG import bill soars as Hormuz tensions rise", "Japan's trade deficit widened on energy imports."),
    ("Iron ore price collapses as China steel output slumps", "Benchmark iron ore fell 8%, hitting Australian miners."),
    ("Tariffs imposed on Japanese autos", "Washington imposed 25% tariffs on Japanese car imports."),
]
TRACKED_FOR_PROBE: list[str] = ["XAUUSD", "US30", "USDJPY", "EURUSD", "AUDUSD", "EURJPY"]

# Probe 3 -- one-notch surprises through usd_surprise_score(): are they comparable across indicators?
SURPRISE_CASES: list[tuple[str, str, str, str]] = [
    ("USD", "CPI m/m", "0.2%", "0.3%"),
    ("USD", "CPI y/y", "2.9%", "3.0%"),
    ("USD", "Core PCE Price Index m/m", "0.0%", "0.1%"),
    ("USD", "Unemployment Rate", "4.2%", "4.3%"),
    ("USD", "Non-Farm Employment Change", "150K", "200K"),
    ("USD", "ISM Manufacturing PMI", "49.0", "51.0"),
    ("JPY", "CPI m/m", "0.2%", "0.4%"),  # a JAPANESE print -- since B6 the function returns None for non-USD rows
]


def _article(title: str, summary: str) -> NewsArticle:
    return NewsArticle(title=title, summary=summary, source="probe", source_type="probe",
                       published_utc=_NOW, url="")


def probe_foreign_cb_sign() -> list[str]:
    """Returns one line per headline: kept/dropped by the FOMC filter, lexicon USD score, correct sign."""
    articles = [_article(t, s) for t, s, _ in FOREIGN_CB_HEADLINES]
    kept_titles = {a.title for a in event_context._filter_relevant(articles, "FOMC Statement")}
    lines = []
    for (title, summary, correct_sign) in FOREIGN_CB_HEADLINES:
        score = score_article_text(title, summary).usd_score
        status = "KEPT" if title in kept_titles else "DROP"
        wrong = (score > 0 and correct_sign == "-") or (score < 0 and correct_sign == "+")
        lines.append(f"{status} usd={score:+.2f} correct={correct_sign} {'SIGN-INVERTED' if wrong else ''} | {title}")
    return lines


def probe_shock_triage() -> list[str]:
    """Returns one line per headline: triage match/category and which tracked symbols it would reach."""
    lines = []
    for title, summary in SHOCK_HEADLINES:
        result = triage_article(_article(title, summary))
        impacts = affected_symbols(result.category, TRACKED_FOR_PROBE) if result.matched else []
        reached = [i.symbol for i in impacts] or "nothing"
        lines.append(f"matched={result.matched!s:5s} category={result.category} reaches={reached} | {title}")
    return lines


def probe_surprise_scale() -> list[str]:
    """Returns one line per case: the USD surprise score the engine assigns."""
    lines = []
    for country, title, forecast, actual in SURPRISE_CASES:
        event = EconomicEvent(title=title, country=country, impact="High", event_time_utc=_NOW,
                              forecast=forecast, actual=actual)
        score = event.usd_surprise_score()
        score_text = "None" if score is None else f"{score:+.3f}"  # None: non-USD row (B6) or no computable surprise
        lines.append(f"{country} {title:28s} f={forecast:>5s} a={actual:>5s} -> usd_surprise_score={score_text}")
    return lines


if __name__ == "__main__":
    print("Probe 1: foreign central-bank headlines through the FOMC filter + USD lexicon")
    for line in probe_foreign_cb_sign():
        print("  " + line)
    print("\nProbe 2: non-USD / trade-flow shocks through real-time triage")
    for line in probe_shock_triage():
        print("  " + line)
    print("\nProbe 3: one-notch surprises through usd_surprise_score()")
    for line in probe_surprise_scale():
        print("  " + line)
