"""
Claude-API-based sentiment scoring — the second-tier contextual fallback,
called only when FinBERT itself is uncertain (its top-class confidence is
below CONTEXTUAL_CONFIDENCE_THRESHOLD) or unavailable but an API key is
configured. Deliberately not the default path for every article: this
costs money per call, and FinBERT already handles the clear-cut majority
of cases for free.

This is the tier actually built to solve the hedged-language failure mode
(the June-NFP case: "rate hike risk IF data surprises to upside" scored
as declarative "rate hike" by the lexicon) — an LLM reads the whole
sentence's logical structure, not a phrase list or a general pos/neg
read, and is explicitly instructed below to weigh hedging/conditionality.

Gracefully unavailable if ANTHROPIC_API_KEY isn't set or the `anthropic`
package isn't installed — callers must check `is_available()` first and
fall back to the lexicon rather than crash.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from config.settings import ANTHROPIC_API_KEY, LLM_SENTIMENT_MODEL

try:
    import anthropic
    _SDK_AVAILABLE = True
except ImportError:
    _SDK_AVAILABLE = False


@dataclass
class LlmSentimentResult:
    usd_score: float          # -1.0 to +1.0
    reasoning: str             # short justification, for the audit trail


_client = None


def is_available() -> bool:
    return _SDK_AVAILABLE and bool(ANTHROPIC_API_KEY)


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


_SYSTEM_PROMPT = """You score US economic/financial news text for USD-directional sentiment.

Output a single float from -1.0 (strongly USD-bearish / dovish) to +1.0
(strongly USD-bullish / hawkish), where 0.0 is genuinely neutral or
no directional content.

Critical: distinguish DECLARATIVE statements ("X is happening", "data
showed X") from HEDGED or CONDITIONAL ones ("X could happen if Y",
"risk of X", "X expected but not confirmed"). Hedged/conditional language
about a hawkish outcome should score close to neutral, NOT as if the
hawkish outcome already happened — that is the single most common
mistake to avoid. Also handle negation ("not raising rates" is dovish,
not hawkish).

Respond with ONLY a JSON object, no other text: {"usd_score": <float>, "reasoning": "<one short sentence>"}"""


def score_article_llm(title: str, summary: str) -> Optional[LlmSentimentResult]:
    """
    Returns None on any failure (no key, SDK missing, API error, bad
    response) — callers must fall back to the lexicon, never treat this
    as a neutral read.
    """
    if not is_available():
        return None

    text = f"{title}. {summary}".strip()
    if not text or text == ".":
        return None

    try:
        client = _get_client()
        response = client.messages.create(
            model=LLM_SENTIMENT_MODEL,
            max_tokens=150,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text}],
        )
        raw = response.content[0].text.strip()
        parsed = json.loads(raw)
        score = float(parsed["usd_score"])
        score = max(-1.0, min(1.0, score))  # clamp — don't trust the model to respect the range
        return LlmSentimentResult(usd_score=score, reasoning=parsed.get("reasoning", ""))
    except Exception as exc:  # noqa: BLE001 — any failure here must degrade to the next tier, not crash scoring
        print(f"[llm_sentiment] WARNING: LLM sentiment call failed: {exc}")
        return None
