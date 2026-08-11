"""
Print-surprise classifier — "will THIS release come in higher or lower
than forecast," derived from real article text via
config.settings.PRINT_SURPRISE_LEXICON. Same shape and honesty
conventions as scoring/sentiment.py's lexicon scorer (case-insensitive
substring matching, never fabricates a call for untracked event titles
or an empty article set), but a distinct axis: sentiment.py answers "is
this article USD-bullish/bearish," this answers "does article language
suggest this specific number will beat or miss consensus."

Deliberately NOT wired into score_bundle()'s instrument-score math —
this is an additive, separately-stored signal (see
docs/superpowers/specs/2026-08-11-economic-print-prediction-trend-history-design.md).
"""
from __future__ import annotations

from dataclasses import dataclass

from config.settings import PRINT_SURPRISE_LEXICON
from data_layer.event_context import EventNewsBundle

# A call built from zero phrase hits is a shrug, not a lean — kept
# distinct from a genuine (even weak) majority so callers can tell
# "articles were silent on this" from "articles leaned one way, barely."
NO_HIT_CONFIDENCE = 0.15


@dataclass
class PrintCall:
    direction: str       # 'higher' | 'lower' | 'in_line'
    confidence: float     # 0.0 to 1.0
    article_count: int


def _hit_count(text: str, phrases: list[str]) -> int:
    lower_text = text.lower()
    return sum(1 for phrase in phrases if phrase in lower_text)


def score_print_direction(bundle: EventNewsBundle) -> "PrintCall | None":
    """
    Returns None (no call made) if the event's title has no
    PRINT_SURPRISE_LEXICON entry, or if the bundle has no articles to
    reason from — both are "no data," not "no surprise."
    """
    lexicon = PRINT_SURPRISE_LEXICON.get(bundle.event.title)
    if lexicon is None or not bundle.articles:
        return None

    higher_phrases = lexicon.get("higher", [])
    lower_phrases = lexicon.get("lower", [])

    higher_hits = 0
    lower_hits = 0
    for article in bundle.articles:
        text = f"{article.title} {article.summary}"
        higher_hits += _hit_count(text, higher_phrases)
        lower_hits += _hit_count(text, lower_phrases)

    total_hits = higher_hits + lower_hits
    article_count = len(bundle.articles)

    if total_hits == 0:
        return PrintCall(direction="in_line", confidence=NO_HIT_CONFIDENCE, article_count=article_count)

    if higher_hits == lower_hits:
        direction = "in_line"
        agreement = 0.5
    elif higher_hits > lower_hits:
        direction = "higher"
        agreement = higher_hits / total_hits
    else:
        direction = "lower"
        agreement = lower_hits / total_hits

    # Confidence scales with both agreement (unanimous > narrow majority)
    # and coverage (more hits = more signal), capped at 0.9 — same
    # "never claim full certainty from a lexicon" ceiling spirit as
    # scoring/sentiment.py's clamped range.
    coverage = min(1.0, total_hits / max(article_count, 1))
    confidence = min(0.9, agreement * (0.5 + 0.5 * coverage))

    return PrintCall(direction=direction, confidence=confidence, article_count=article_count)
