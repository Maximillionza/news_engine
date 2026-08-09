"""
Fallback sentiment scoring for articles that don't come with a native
sentiment score (which is most of them — Alpha Vantage and APITube provide
one, but the free RSS sources do not).

This is a naive lexicon-based scorer, not a trained model. It's deliberately
simple for v1 so the *pipeline logic* (time-decay, trust weighting,
contradiction flagging) can be validated first without a black-box NLP
component muddying the backtest results. If backtesting shows sentiment
accuracy itself is the weak link rather than the aggregation logic, this
is the component to swap out first — e.g. for a finance-tuned model like
FinBERT, or a paid NLP API.

Output convention: score is USD-directional, -1.0 (bearish USD) to +1.0
(bullish USD). Every downstream instrument mapping (gold=inverse, etc.)
is built on top of this single USD-sentiment axis, per the user's framing
that "anything against USD moves in the buy or sell direction" — one
consistent axis, not a separate lexicon per instrument.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Terms suggesting USD strength / hawkish Fed / robust US economy
BULLISH_USD_TERMS = {
    "hawkish": 1.0,
    "rate hike": 1.0,
    "raise rates": 0.9,
    "raising rates": 0.9,
    "higher for longer": 0.8,
    "inflation surge": 0.6,
    "inflation rises": 0.5,
    "strong dollar": 1.0,
    "dollar strength": 0.9,
    "dollar rallies": 0.9,
    "beats expectations": 0.6,
    "better than expected": 0.6,
    "beats forecast": 0.6,
    "job growth": 0.4,
    "unemployment falls": 0.5,
    "strong jobs report": 0.8,
    "economy resilient": 0.5,
    "hot inflation": 0.6,
    "tightening": 0.6,
    "restrictive policy": 0.5,
}

# Terms suggesting USD weakness / dovish Fed / soft US economy
BEARISH_USD_TERMS = {
    "dovish": -1.0,
    "rate cut": -1.0,
    "cutting rates": -0.9,
    "cut rates": -0.9,
    "lower rates": -0.7,
    "dollar weakness": -1.0,
    "dollar falls": -0.9,
    "dollar slides": -0.8,
    "weak dollar": -1.0,
    "misses expectations": -0.6,
    "worse than expected": -0.6,
    "misses forecast": -0.6,
    "job losses": -0.6,
    "unemployment rises": -0.6,
    "weak jobs report": -0.8,
    "economy slows": -0.5,
    "cooling inflation": -0.5,
    "recession fears": -0.7,
    "easing": -0.5,
    "accommodative policy": -0.5,
    "soft landing concerns": -0.4,
}

# Simple negation handling — if one of these precedes a term within a few
# words, flip its contribution. Naive but catches the common cases like
# "not raising rates" or "no longer hawkish".
NEGATION_WORDS = {"not", "no", "won't", "isn't", "aren't", "unlikely", "without"}
NEGATION_WINDOW = 4  # words


@dataclass
class SentimentScore:
    usd_score: float          # -1.0 to +1.0
    matched_terms: list[str]  # which lexicon terms fired, for debugging/audit
    term_count: int           # total matches — used as a rough confidence proxy (more signal = more reliable)


def _find_negation_nearby(text_words: list[str], term_start_idx: int) -> bool:
    window_start = max(0, term_start_idx - NEGATION_WINDOW)
    preceding = text_words[window_start:term_start_idx]
    return any(w.strip(".,!?").lower() in NEGATION_WORDS for w in preceding)


def score_text(text: str) -> SentimentScore:
    """
    Score a block of text (title + summary, typically) for USD-directional
    sentiment using the lexicon above. Case-insensitive substring matching
    on multi-word phrases, with basic negation flipping.
    """
    if not text:
        return SentimentScore(usd_score=0.0, matched_terms=[], term_count=0)

    lower_text = text.lower()
    words = re.findall(r"\S+", lower_text)

    total = 0.0
    matched: list[str] = []

    for lexicon in (BULLISH_USD_TERMS, BEARISH_USD_TERMS):
        for phrase, weight in lexicon.items():
            for match in re.finditer(re.escape(phrase), lower_text):
                # Locate approximate word index of the match to check negation
                char_idx = match.start()
                word_idx = len(lower_text[:char_idx].split())
                negated = _find_negation_nearby(words, word_idx)
                contribution = -weight if negated else weight
                total += contribution
                matched.append(f"{'~' if negated else ''}{phrase}")

    term_count = len(matched)
    if term_count == 0:
        return SentimentScore(usd_score=0.0, matched_terms=[], term_count=0)

    # Average rather than sum, so a long article repeating one term doesn't
    # dominate an article that hits several distinct, meaningful terms.
    avg_score = total / term_count
    clamped = max(-1.0, min(1.0, avg_score))
    return SentimentScore(usd_score=clamped, matched_terms=matched, term_count=term_count)


def score_article_text(title: str, summary: str) -> SentimentScore:
    """Convenience wrapper — titles carry more signal, weighted 2x over summary text."""
    combined = f"{title} {title} {summary}"
    return score_text(combined)
