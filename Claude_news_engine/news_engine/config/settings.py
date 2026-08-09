"""
Central config for the fundamental news engine.
API keys are read from environment variables — never hardcode them here.
"""
import os
from zoneinfo import ZoneInfo

# --- Timezones ---
# Masood is based in South Africa (SAST, UTC+2, no DST)
LOCAL_TZ = ZoneInfo("Africa/Johannesburg")
NY_TZ = ZoneInfo("America/New_York")     # most US macro releases are quoted in this tz
UTC_TZ = ZoneInfo("UTC")

# --- API keys (set these as environment variables before running) ---
ALPHA_VANTAGE_API_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY", "")
APITUBE_API_KEY = os.environ.get("APITUBE_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# --- Contextual sentiment scoring (optional upgrade over the naive lexicon) ---
# Tiered fallback, cheapest/most-deterministic first:
#   1. native_sentiment on the article, if a vendor already supplied one
#      (Alpha Vantage / APITube) — unchanged, always wins if present.
#   2. FinBERT (local model, scoring/finbert_sentiment.py) — free, no
#      network per call, but only loads if `transformers`+`torch` are
#      installed (see requirements-contextual.txt). Silently skipped if
#      not installed — the lexicon fallback still works with zero extra
#      dependencies, preserving the "no API keys required to start" setup.
#   3. Claude API (scoring/llm_sentiment.py) — only called when FinBERT's
#      own top-class confidence is below CONTEXTUAL_CONFIDENCE_THRESHOLD
#      (genuinely ambiguous cases: hedged/conditional language is exactly
#      what should trigger this), or when FinBERT isn't installed at all
#      but ANTHROPIC_API_KEY is set. Costs money per call — kept as a
#      fallback for ambiguous cases specifically so it isn't called on
#      every article.
#   4. scoring/sentiment.py's keyword lexicon — final fallback, always
#      available, zero dependencies, zero cost. This is what runs today
#      if neither of the above is configured.
FINBERT_MODEL_NAME = "ProsusAI/finbert"

# FinBERT's positive/negative/neutral axis is a proxy for hawkish/dovish
# USD-directional sentiment, not a perfect match — it was trained on
# general financial-news sentiment, not specifically Fed-speak. Treating
# "positive economic data framing" as hawkish/USD-bullish and "negative"
# as dovish/USD-bearish is a real simplification, same honesty as US30's
# risk_sentiment mapping in probability_engine.py. Worth revisiting if
# backtest accuracy under FinBERT comes out weak relative to the lexicon.
CONTEXTUAL_CONFIDENCE_THRESHOLD = 0.6  # below this, FinBERT's own top-class probability is treated as "not sure enough" -> try the LLM fallback

LLM_SENTIMENT_MODEL = "claude-haiku-4-5-20251001"  # cheapest current model — this is a short classification call, not a reasoning task

# --- Instruments tracked ---
# Each entry maps an instrument to the USD relationship used for directional logic
# "inverse" = instrument tends to move opposite to USD strength (e.g. gold, EURUSD)
# "direct"  = instrument tends to move with USD strength (e.g. USDJPY, US30 is more nuanced — risk-driven)
INSTRUMENTS = {
    "XAUUSD": {"label": "Gold", "usd_relationship": "inverse"},
    "US30":   {"label": "Dow Jones / US30", "usd_relationship": "risk_sentiment"},
}

# --- Rolling window config ---
PRE_EVENT_WINDOW_HOURS = 72   # start forming probability 3 days before a scheduled event
POST_EVENT_REFRESH_MINUTES = 15  # how often to refresh sentiment after release, to catch indecision

# --- Scoring engine config ---
# Exponential time-decay half-life for article weighting — an article this
# many minutes old carries half the weight of a fresh one. Starting value,
# needs tuning once backtesting shows how fast pre-event sentiment actually
# moves markets vs. how fast it goes stale.
TIME_DECAY_HALF_LIFE_MINUTES = 360  # 6 hours

# Window used to split "recent" vs "older" articles for contradiction
# detection — if sentiment in the last RECENT_WINDOW_HOURS disagrees with
# sentiment from before that, the engine flags indecision/fluctuation.
RECENT_WINDOW_HOURS = 6

# Minimum |instrument_score| for a window's sentiment to count as a real
# directional lean rather than noise, used by the contradiction check.
CONTRADICTION_MIN_MAGNITUDE = 0.15

# --- Source trust weighting (0-1), used in scoring engine later ---
# Placeholder starting weights — to be refined after backtest validation.
#
# IMPORTANT: these weights apply only to PRE-EVENT SCORING sources — i.e.
# sources that publish previews/expectations/positioning before a release.
# Official outcome feeds (Fed, BLS) are never scored for sentiment; they're
# ground truth used only by the backtest module to check what actually
# happened. Don't add them here — see data_layer/rss_sources.py for the
# tier split.
SOURCE_TRUST_WEIGHTS = {
    "forexfactory_calendar": 1.0,   # ground truth for scheduled event timing, not sentiment
    "alpha_vantage_news": 0.7,
    "apitube_news": 0.7,
    "rss_reuters_business": 0.85,   # wire service, fast + historically reliable
    "rss_cnbc_top_news": 0.6,
    "rss_cnbc_economy": 0.65,
    "rss_investing_com_forex": 0.55,  # broader syndication, mixed editorial quality
}

# --- Leading-indicator precursor events ---
# Minor/medium USD releases that are known leading indicators for a later
# major event — e.g. ADP prints ~2 days before NFP and is widely watched as
# a preview. Unlike article sentiment (lexicon-guessed from prose), a
# precursor's forecast-vs-actual is a real structured number straight from
# the calendar feed — no text interpretation involved.
#
# Hand-curated starter list, not exhaustive — easy to extend. Real-world
# release ordering (does PPI actually land before CPI this particular
# month?) varies, so this is "if it happens to have already printed in the
# target's pre-event window," not a guaranteed sequence.
PRECURSOR_EVENTS = {
    "Non-Farm Employment Change": ["ADP Nonfarm Employment Change", "Unemployment Claims", "Challenger Job Cuts"],
    "Unemployment Rate": ["ADP Nonfarm Employment Change", "Unemployment Claims"],
    "Average Hourly Earnings m/m": ["ADP Nonfarm Employment Change"],
    "CPI m/m": ["PPI m/m", "Core PPI m/m", "Import Prices m/m"],
    "CPI y/y": ["PPI m/m", "Core PPI m/m"],
    "Core CPI m/m": ["Core PPI m/m"],
    "Core CPI y/y": ["Core PPI m/m"],
    # FOMC rate decisions are driven more by speeches/minutes/dot-plot than
    # a clean single precursor print — deliberately left empty rather than
    # guessing a mapping that isn't real.
}

# For each event TITLE (major or precursor), whether an actual print ABOVE
# forecast is USD-bullish ("higher_bullish") or USD-bearish
# ("higher_bearish"). Needed because the "beat = bullish" direction isn't
# uniform across indicator types (a higher unemployment rate is bearish,
# a higher CPI print is bullish).
EVENT_SURPRISE_DIRECTION = {
    "Non-Farm Employment Change": "higher_bullish",
    "ADP Nonfarm Employment Change": "higher_bullish",
    "Average Hourly Earnings m/m": "higher_bullish",
    "Unemployment Rate": "higher_bearish",
    "Unemployment Claims": "higher_bearish",
    "Challenger Job Cuts": "higher_bearish",
    "CPI m/m": "higher_bullish",
    "CPI y/y": "higher_bullish",
    "Core CPI m/m": "higher_bullish",
    "Core CPI y/y": "higher_bullish",
    "PPI m/m": "higher_bullish",
    "Core PPI m/m": "higher_bullish",
    "Import Prices m/m": "higher_bullish",
    "ISM Manufacturing PMI": "higher_bullish",
    "Retail Sales m/m": "higher_bullish",
}

# Trust weight for a precursor's structured surprise contribution — high,
# since it's a real released number rather than lexicon-guessed text, but
# not 1.0: the higher_bullish/higher_bearish direction mapping above is
# itself a simplification (e.g. a beat that's already fully priced in
# shouldn't move markets the same as a genuine surprise, which this can't
# tell apart).
PRECURSOR_TRUST_WEIGHT = 0.9

# Precursors use their OWN, much slower time-decay half-life than article
# sentiment. A structured forecast-vs-actual print doesn't go "stale"
# minute to minute the way news chatter does — ADP's number is exactly as
# informative right before NFP as it was the moment it printed. Reusing
# TIME_DECAY_HALF_LIFE_MINUTES (6h, tuned for ephemeral text) would crush
# a 2-day-old precursor to near-zero weight for no real reason. Set equal
# to PRE_EVENT_WINDOW_HOURS in minutes so a precursor barely decays across
# the whole window it's eligible to be found in.
PRECURSOR_TIME_DECAY_HALF_LIFE_MINUTES = PRE_EVENT_WINDOW_HOURS * 60

# How many "percent-surprise units" it takes to saturate the surprise
# score toward +-1.0 — same tanh-saturation idea as _score_to_probability's
# k. Untuned placeholder, same honesty caveat as every other fixed
# constant in this file: needs real backtest data to calibrate.
SURPRISE_SENSITIVITY = 3.0

# --- Free-tier API sources worth adding later (not yet implemented) ---
# GDELT      — free, huge global news volume, good for a "how much is this
#               story spreading" signal rather than individual article quality
# Finnhub    — free tier has basic news + sentiment, useful as a secondary
#               cross-check against Alpha Vantage
# Marketaux  — free tier, wide source breadth
# NewsAPI.org — free dev tier is development-only (no production use) and
#               delayed, so it's only useful for testing pipeline logic,
#               not for real backtest timestamp accuracy
