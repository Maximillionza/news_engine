"""
Central config for the fundamental news engine.
API keys are read from environment variables — never hardcode them here.
"""
import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

# .env.example / README both document "copy to .env and fill in your
# keys," but nothing actually loaded that file — os.environ.get() alone
# only sees real process env vars, never a bare .env on disk. Found while
# wiring in Alpha Vantage: a key written to .env was silently never
# picked up. load_dotenv() here (no-ops harmlessly if .env doesn't exist)
# makes the documented workflow actually work.
load_dotenv()

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
# Explicit opt-in — NOT just "is the package importable." Installing
# torch/transformers for an unrelated check (e.g. verifying FinBERT works
# at all) must not silently change production scoring behavior, and it
# must not silently break every existing test that was written assuming
# deterministic lexicon-only scores. Set these to "1" in the environment
# to actually turn the contextual tiers on.
ENABLE_FINBERT_SENTIMENT = os.environ.get("ENABLE_FINBERT_SENTIMENT", "") == "1"
ENABLE_LLM_SENTIMENT = os.environ.get("ENABLE_LLM_SENTIMENT", "") == "1"

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

# Dampening applied to "risk_sentiment" instruments (currently just US30) —
# a hawkish/dovish USD read is treated as a weaker, indirect driver for an
# equity index than it is for gold's cleaner inverse relationship. Shared
# by scoring/probability_engine.py's article-based path and
# webapp/scoring_service.py's essence-only path — was previously
# hardcoded as a duplicated 0.7 literal in both, a real DRY violation
# flagged in review and left unfixed until now. Still an unvalidated
# simplification, same honesty as INSTRUMENTS' usd_relationship choices —
# worth revisiting if US30 backtest accuracy comes out weak.
RISK_SENTIMENT_DAMPENING = 0.7

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
    # Added for dashboard coverage (final-review fix, Step 6). Titles are
    # best-effort standard Forex Factory naming — not independently
    # verified against a live feed capture in this environment, since the
    # feed isn't reachable from this sandbox (see data_layer/calendar_feed.py's
    # module docstring). Re-verify title strings exact-match once this runs
    # against the live feed.
    "Core PCE Price Index m/m": "higher_bullish",
    "Advance GDP q/q": "higher_bullish",
    "ISM Services PMI": "higher_bullish",
    "Prelim UoM Consumer Sentiment": "higher_bullish",
    # "Federal Funds Rate" and "FOMC Statement" deliberately NOT added:
    # both are policy-decision/text events with no forecast-vs-actual
    # numeric pair for usd_surprise_score() to compare (FF publishes them
    # without a meaningful "forecast" field to beat/miss) — forcing a
    # mapping here would produce scores that are always None anyway, or
    # worse, a fabricated one from unrelated fields.
}

# Medium-impact USD titles genuinely worth accumulator (article-based)
# coverage despite Forex Factory's generic "Medium" tag — curated, not a
# blanket Medium+ threshold, to protect the accumulator's tuned signal
# budget from dilution. Grounded against the LIVE calendar's real impact
# tags (2026-08-14), not assumed: Unemployment Claims and Retail Sales
# m/m/Prelim UoM Consumer Sentiment were confirmed Medium (not High) on
# the actual feed. All three already have an EVENT_SURPRISE_DIRECTION
# entry. Excluded: Core Retail Sales m/m (redundant with Retail Sales
# m/m, no EVENT_SURPRISE_DIRECTION entry yet), Prelim UoM Inflation
# Expectations (no forecast field to compare against), any
# non-scheduled-print title (e.g. speeches).
ACCUMULATOR_MEDIUM_ALLOWLIST = frozenset({
    "Unemployment Claims",
    "Retail Sales m/m",
    "Prelim UoM Consumer Sentiment",
})

# Phrase-based lexicon for scoring/print_direction.py's print-surprise call
# — "will THIS release come in higher or lower than forecast," derived from
# article language, distinct from scoring/sentiment.py's general USD-
# directional lexicon. Initial 4 highest-traffic events (from
# EVENT_SURPRISE_DIRECTION) plus PPI m/m/Core PPI m/m (added ahead of the
# 2026-08-13 PPI release); an event title with no entry here always
# returns None from score_print_direction() — never a guessed call.
# Adding coverage for another event later is a config-only change here,
# no code changes required.
PRINT_SURPRISE_LEXICON = {
    "CPI m/m": {
        "higher": ["sticky inflation", "hotter than expected", "upside surprise", "inflation accelerat"],
        "lower": ["cooling inflation", "softer than expected", "downside surprise", "disinflation"],
    },
    "Core CPI m/m": {
        "higher": ["sticky core inflation", "hotter than expected", "upside surprise"],
        "lower": ["cooling", "softer than expected", "downside surprise"],
    },
    "Non-Farm Employment Change": {
        "higher": ["blowout jobs", "stronger than expected", "beat estimates", "hot jobs report"],
        "lower": ["weaker than expected", "missed estimates", "soft jobs report", "payrolls disappoint"],
    },
    "Unemployment Rate": {
        "higher": ["rate ticks up", "unemployment rises", "labor market cooling"],
        "lower": ["rate ticks down", "unemployment falls", "labor market tightening"],
    },
    "PPI m/m": {
        "higher": ["producer prices surge", "hotter than expected", "upside surprise", "wholesale prices rise"],
        "lower": ["producer prices cool", "softer than expected", "downside surprise", "wholesale prices fall"],
    },
    "Core PPI m/m": {
        "higher": ["producer prices surge", "hotter than expected", "upside surprise", "wholesale prices rise"],
        "lower": ["producer prices cool", "softer than expected", "downside surprise", "wholesale prices fall"],
    },
    # Added so CPI y/y, Core CPI y/y, and Unemployment Claims get a
    # print-direction call at all — without a lexicon entry here,
    # score_print_direction() never fires for a title, which means no
    # print_predictions row ever gets written for it and it can never
    # appear as a numeric row in the History tab, regardless of whether
    # event_history has a real resolved actual (surfaced 2026-08-14: real
    # CPI y/y/Core CPI y/y/Unemployment Claims actuals existed but were
    # invisible in the History tab for exactly this reason).
    "CPI y/y": {
        "higher": ["annual inflation accelerat", "yearly inflation hotter", "y/y inflation surprise to the upside", "inflation rate climbs"],
        "lower": ["annual inflation cools", "yearly inflation eases", "y/y inflation surprise to the downside", "disinflation continues"],
    },
    "Core CPI y/y": {
        "higher": ["annual core inflation accelerat", "yearly core inflation hotter", "sticky annual core inflation"],
        "lower": ["annual core inflation cools", "yearly core inflation eases", "core disinflation continues"],
    },
    "Unemployment Claims": {
        "higher": ["claims rise unexpectedly", "jobless claims jump", "layoffs increase", "claims surprise to the upside"],
        "lower": ["claims fall", "jobless claims decline", "layoffs ease", "claims surprise to the downside"],
    },
}

# Trust weight for a precursor's structured surprise contribution — high,
# since it's a real released number rather than lexicon-guessed text, but
# not 1.0: the higher_bullish/higher_bearish direction mapping above is
# itself a simplification (e.g. a beat that's already fully priced in
# shouldn't move markets the same as a genuine surprise, which this can't
# tell apart).
PRECURSOR_TRUST_WEIGHT = 0.9

# Trust weight for THIS occurrence's print-direction call
# (scoring/print_direction.py's score_print_direction()) when blended into
# score_bundle() — below PRECURSOR_TRUST_WEIGHT (a real released number for
# a DIFFERENT event, near-certain) since this is inference about a number
# that hasn't printed yet, even though it's already an aggregate read
# across the whole article bundle.
PRINT_CALL_TRUST_WEIGHT = 0.5

# Trust weight for the event's historical beat/miss streak
# (webapp/trend.py's compute_trend_signal()) when blended into
# score_bundle() — weaker than PRINT_CALL_TRUST_WEIGHT, since a streak is
# a pattern over PAST events, not evidence about this one.
TREND_STREAK_TRUST_WEIGHT = 0.3

# Minimum confirmed (non-pending) historical occurrences required before
# the trend streak contributes to scoring AT ALL — enforced by
# scoring/backtest_accumulator.py before it ever calls
# webapp.trend.compute_trend_signal(). Below this, zero contribution, not
# a low-weight one. Deliberately stricter than webapp/trend.py's own
# MIN_CONFIRMED_ROWS_FOR_A_TREND=2 (which only gates the DISPLAY string) —
# trusting a 2-3 event pattern to nudge a live prediction is a bigger
# claim than merely showing it on a dashboard.
MIN_OCCURRENCES_FOR_TREND_PRIOR = 3

# Precursors use their OWN, much slower time-decay half-life than article
# sentiment. A structured forecast-vs-actual print doesn't go "stale"
# minute to minute the way news chatter does — ADP's number is exactly as
# informative right before NFP as it was the moment it printed. Reusing
# TIME_DECAY_HALF_LIFE_MINUTES (6h, tuned for ephemeral text) would crush
# a 2-day-old precursor to near-zero weight for no real reason. Set equal
# to PRE_EVENT_WINDOW_HOURS in minutes so a precursor barely decays across
# the whole window it's eligible to be found in.
PRECURSOR_TIME_DECAY_HALF_LIFE_MINUTES = PRE_EVENT_WINDOW_HOURS * 60

# --- Kalshi prediction-market integration ---
# Kalshi (kalshi.com) is a CFTC-regulated prediction-market exchange with
# free, unauthenticated public market-data access. Confirmed live this
# session: real, active series exist for 15 of this system's 19 tracked
# high-impact USD events, but 7 of the 15 (6 here plus FOMC below) use a
# DATE-based Kalshi ticker (a week-ending date, a specific release date,
# or a specific FOMC meeting date) rather than a month, which
# data_layer/kalshi_feed.py's _resolve_event_ticker() — month-suffix
# matching only — cannot correctly resolve; it would either never match
# (fail closed, silently dead) or, worse, match wrong. Those 7 are
# deliberately dropped from live coverage below, leaving 9 genuinely
# resolvable month-only-ticker events. Config-only-to-extend, same
# pattern as PRINT_SURPRISE_LEXICON — an event title with no entry here
# never triggers a Kalshi lookup at all.
KALSHI_SERIES_BY_EVENT_TITLE = {
    "Non-Farm Employment Change": "KXPAYROLLS",
    "ADP Nonfarm Employment Change": "KXADP",
    "Unemployment Rate": "KXU3",
    "CPI m/m": "KXCPI",
    "CPI y/y": "KXCPIYOY",
    "Core CPI m/m": "KXCPICORE",
    "Core CPI y/y": "KXCPICOREYOY",
    "ISM Manufacturing PMI": "KXISMPMI",
    "Core PCE Price Index m/m": "KXPCECORE",
    # "Unemployment Claims": "KXJOBLESSCLAIMS" — REMOVED. Kalshi tickets
    # this series to a WEEK-ENDING DATE (e.g. "-26jun18"), not a month —
    # month-suffix matching can't resolve it. Real coverage exists on
    # Kalshi; adding correct date-based ticket resolution is a real
    # follow-up feature, not implemented here.
    # "Advance GDP q/q": "KXGDP" — REMOVED. Kalshi tickets this series to
    # a specific RELEASE DATE (e.g. "-27jan30"), not a month — same
    # reason as Unemployment Claims above.
    # "Prelim UoM Consumer Sentiment": "KXUSMICHCSP" — REMOVED. Kalshi
    # tickets this series to a specific RELEASE DATE (e.g. "-26may08"),
    # not a month. Unlike CPI/PPI/etc., this one is NOT lagged — it's a
    # same-month preliminary read — but it's still date-, not
    # month-keyed, so month-suffix matching still can't resolve it.
    # "Challenger Job Cuts": "KXCHCUTS" — REMOVED. Live ground-truth check
    # of real Kalshi tickers (e.g. "KXCHCUTS-26SEP03", "KXCHCUTS-26AUG06")
    # shows this series is ticketed to a specific RELEASE DATE, not a
    # month — same month-suffix-matching problem as the 3 above.
    # "PPI m/m": "KXUSPPI" — REMOVED. Real ticker looks like
    # "KXUSPPI-26MAY13" — a specific release date, not a month. This
    # series also appears to have very few events listed at all,
    # possibly low-volume/stale, independent of the date-ticket issue.
    # "Retail Sales m/m": "KXUSRETAIL" — REMOVED. Real tickers look like
    # "KXUSRETAIL-26AUG14", "KXUSRETAIL-26JUL16" — a specific release
    # date, not a month, same problem as the others above.
}
# Confirmed with NO usable Kalshi coverage AT ALL (verified live, not
# left unchecked): Average Hourly Earnings m/m (Kalshi's closest match
# prices a different, inflation-adjusted metric), Core PPI m/m and
# Import Prices m/m (no matching series exists), ISM Services PMI
# (series exists but has zero markets currently listed — dormant).
# These four simply have no entry here and never will unless Kalshi
# lists new markets.
#
# Distinct from the above: REAL Kalshi coverage exists for Unemployment
# Claims, Advance GDP q/q, Prelim UoM Consumer Sentiment, Challenger Job
# Cuts, PPI m/m, and Retail Sales m/m (see the commented-out entries in
# the dict above) — they're excluded only because this integration's
# ticker resolution doesn't yet handle date-based tickers, not because
# Kalshi has no market for them.

# FOMC/Federal Funds Rate is a discrete cut/hold/hike DECISION, not a
# continuous forecast-vs-actual number — it can't reuse
# EVENT_SURPRISE_DIRECTION's convention, so it gets its own small,
# parallel mapping. Mutually exclusive with KALSHI_SERIES_BY_EVENT_TITLE
# per title — an event title matches at most one of the two dicts.
RATE_DECISION_DIRECTION = {
    "hike": "bullish",
    "hold": "neutral",
    "cut": "bearish",
}
# Deliberately emptied (was {"Federal Funds Rate": "KXFED"}) — KXFED is
# ticketed to a specific FOMC MEETING DATE (e.g. "-26mar19"), not a
# month, same date-based-ticker problem as the 3 removed entries above.
# _read_kalshi_signal()'s FOMC branch is left in place (see
# scoring/backtest_accumulator.py) so re-adding correct coverage later,
# once date-based ticket resolution exists, is a one-line change here.
KALSHI_RATE_DECISION_SERIES = {}

# A Kalshi market whose open_interest is below this floor is treated as
# NO signal at all — same "contribute nothing, not a diluted nudge"
# pattern already used for in_line print calls and thin trend history.
# Protects the highest-trust-weight contribution in the system from
# being driven by an illiquid, easily-skewed price (observed live: some
# Kalshi strikes currently show zero 24h volume).
MIN_KALSHI_OPEN_INTEREST = 10.0

# Trust weight for a Kalshi market read when blended into score_bundle()
# — above PRECURSOR_TRUST_WEIGHT (0.9), since this prices real money
# directly on the EXACT event being scored, not a related-but-different
# one via a structured surprise.
KALSHI_TRUST_WEIGHT = 0.95

# How many "percent-surprise units" it takes to saturate the surprise
# score toward +-1.0 — same tanh-saturation idea as _score_to_probability's
# k. Untuned placeholder, same honesty caveat as every other fixed
# constant in this file: needs real backtest data to calibrate.
SURPRISE_SENSITIVITY = 3.0

# Below this relative (or, when forecast≈0, absolute) delta between actual
# and forecast, classify_surprise() below calls it 'in_line' rather than
# 'higher'/'lower' — a literal actual-vs-forecast comparison for event
# history/trend display, distinct from usd_surprise_score()'s continuous
# bullish/bearish-mapped magnitude used for instrument-score blending.
EVENT_HISTORY_IN_LINE_TOLERANCE = 0.05

# --- Free-tier API sources worth adding later (not yet implemented) ---
# GDELT      — free, huge global news volume, good for a "how much is this
#               story spreading" signal rather than individual article quality
# Finnhub    — free tier has basic news + sentiment, useful as a secondary
#               cross-check against Alpha Vantage
# Marketaux  — free tier, wide source breadth
# NewsAPI.org — free dev tier is development-only (no production use) and
#               delayed, so it's only useful for testing pipeline logic,
#               not for real backtest timestamp accuracy
