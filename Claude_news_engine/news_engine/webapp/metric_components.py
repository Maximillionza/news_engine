"""
Static breakdowns behind the Stats tab's information icons (spec §6, ruling R2).
Sources cited verbatim from the Cleveland Fed page checked 2026-10-15
(clevelandfed.org/indicators-and-data/inflation-nowcasting).
"""
from __future__ import annotations

from typing import Optional

_CLEVELAND = "Cleveland Fed Inflation Nowcasting"

_REGISTRY: dict[str, dict] = {
    "cleveland_nowcast": {
        "title": "Cleveland Fed inflation nowcast",
        "summary": "A model estimate of the coming CPI print, refreshed daily from ten inputs. Core CPI nowcasts use only past core CPI.",
        "components": [
            {"name": "Brent crude (daily)", "detail": "Daily spot price.", "source": "Financial Times / EIA"},
            {"name": "Retail gasoline (weekly)", "detail": "Weekly retail price.", "source": "EIA"},
            {"name": "CPI (monthly, SA)", "detail": "Past headline inflation.", "source": "BLS"},
            {"name": "Core CPI (monthly, SA)", "detail": "Past core inflation.", "source": "BLS"},
            {"name": "CPI food (monthly, SA)", "detail": "Past food inflation.", "source": "BLS"},
            {"name": "CPI food at home (monthly, SA)", "detail": "Past grocery inflation.", "source": "BLS"},
            {"name": "CPI gasoline (monthly, SA)", "detail": "Past gasoline CPI.", "source": "BLS"},
            {"name": "PCE price index (monthly, SA)", "detail": "Past PCE inflation.", "source": "BEA"},
            {"name": "Core PCE price index (monthly, SA)", "detail": "Past core PCE.", "source": "BEA"},
            {"name": "PCE food and beverages, off-premises (monthly, SA)", "detail": "Past PCE food.", "source": "BEA"},
        ],
        "note": "Brent and gasoline are already inputs, so they are not weighted again in Tier 1. "
                "The stored value is a snapshot: its 'as of' time is shown on each row.",
    },
    "news_lean": {
        "title": "News sentiment lean",
        "summary": "How hot or cool the article flow leans for this release, from -1 (cooler) to +1 (hotter).",
        "components": [
            {"name": "Print call", "detail": "Hotter / cooler / in line versus forecast, with its confidence. Used first when it takes a side.", "source": "scoring/print_direction.py"},
            {"name": "XAUUSD accumulator prediction", "detail": "Used when the print call is in line or absent; mapped to a hotter/cooler side, strength |2p - 1|.", "source": "scoring/probability_engine.py"},
            {"name": "Article sentiment, trust weighting, time decay, contradiction flag", "detail": "What the accumulator itself is built from.", "source": "scoring/sentiment.py, scoring/probability_engine.py"},
        ],
        "note": "News-only predicted values scale the lean by the event's typical surprise size (an assumption).",
    },
    "combined": {
        "title": "Combined score",
        "summary": "A fixed 70% / 30% blend of the Tier 1 surprise and the news surprise. There is no conflicting state.",
        "components": [
            {"name": "Tier 1 (nowcast vs forecast)", "detail": "70% of the blend.", "source": _CLEVELAND},
            {"name": "News sentiment lean", "detail": "30% of the blend. If no articles exist, the row is Tier 1 only.", "source": "Stats tab spec D3"},
        ],
        "note": "Weights are fixed in advance and reviewed on 2027-01-15; they are not tuned on results.",
    },
}

METRICS: tuple[str, ...] = tuple(_REGISTRY)


def get_components(metric: str) -> Optional[dict]:
    entry = _REGISTRY.get(metric)
    return None if entry is None else {"metric": metric, **entry}
