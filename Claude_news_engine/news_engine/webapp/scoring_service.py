"""
Essence-only scoring — a symbol's directional call driven purely by
structured calendar data (forecast vs. actual), with no article
fetching/sentiment involved at all. Parallel to, and independent of, the
article-based pipeline in scoring/probability_engine.py; this is what the
dashboard uses.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from config.settings import SURPRISE_SENSITIVITY
from data_layer.calendar_feed import EconomicEvent
from scoring.probability_engine import Direction
from webapp.symbols import SymbolClass


@dataclass
class EssenceScore:
    symbol: str
    event_title: str
    applicable: bool           # False for fx_cross symbols — no USD exposure, no score at all
    pending: bool               # True if the event hasn't printed an actual value yet
    probability: Optional[float] = None    # 0.0-1.0, None if not applicable/pending
    direction: Optional[Direction] = None  # None if not applicable/pending
    raw_score: Optional[float] = None       # the underlying -1..1 symbol-directional score, None if not applicable/pending


def score_event_for_symbol(event: EconomicEvent, symbol_class: SymbolClass) -> EssenceScore:
    if symbol_class.usd_relationship is None:
        return EssenceScore(
            symbol=symbol_class.symbol, event_title=event.title,
            applicable=False, pending=False,
        )

    usd_surprise = event.usd_surprise_score()
    if usd_surprise is None:
        # NOTE: pending=True conflates two distinct cases:
        # (1) Event has no 'actual' value yet (genuinely pending, will resolve when actual prints)
        # (2) Event title is not in config.settings.EVENT_SURPRISE_DIRECTION (untracked indicator,
        #     will NEVER resolve). Distinguishing these would require EssenceScore to carry
        #     an additional field explaining the reason, which is out of scope for this task.
        return EssenceScore(
            symbol=symbol_class.symbol, event_title=event.title,
            applicable=True, pending=True,
        )

    relationship = symbol_class.usd_relationship
    if relationship == "inverse":
        symbol_score = -usd_surprise
    elif relationship == "direct":
        symbol_score = usd_surprise
    elif relationship == "risk_sentiment":
        symbol_score = -usd_surprise * 0.7
    else:
        raise ValueError(f"Unknown usd_relationship {relationship!r} for {symbol_class.symbol!r}")

    probability = 0.5 + 0.5 * math.tanh(SURPRISE_SENSITIVITY * symbol_score)

    if symbol_score > 0.02:
        direction = Direction.BULLISH
    elif symbol_score < -0.02:
        direction = Direction.BEARISH
    else:
        direction = Direction.NEUTRAL

    return EssenceScore(
        symbol=symbol_class.symbol, event_title=event.title,
        applicable=True, pending=False,
        probability=probability, direction=direction, raw_score=symbol_score,
    )
