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
FRED_API_KEY = os.environ.get("FRED_API_KEY", "")

# --- FRED (St. Louis Fed) month-lookahead calendar source — READ-ONLY,
# comparison/logging use only, NOT wired into scoring or the live
# dashboard/accumulator pipelines (see docs/calendar-lookahead-source-research-2026-08-15.md
# and scripts/compare_fred_lookahead.py). Forex Factory's feed only ever
# shows "thisweek" (data_layer/calendar_feed.py's docstring) — FRED's
# /fred/releases/dates endpoint is a genuinely free, official-source
# alternative for forward-looking RELEASE DATES (not forecast/consensus
# values — FRED doesn't have those, same gap every free source this
# project has checked has).
#
# Every rid below was live-verified 2026-08-15 by loading the actual FRED
# release page and confirming its title — not assumed from documentation.
# One release commonly covers several of this project's event titles
# (e.g. rid=10 "Consumer Price Index" covers CPI m/m, CPI y/y, Core CPI
# m/m, and Core CPI y/y all at once — FRED schedules the whole release,
# not each sub-series separately).
FRED_RELEASE_ID_BY_EVENT_TITLE = {
    "CPI m/m": 10, "CPI y/y": 10, "Core CPI m/m": 10, "Core CPI y/y": 10,          # Consumer Price Index
    "PPI m/m": 46, "Core PPI m/m": 46,                                             # Producer Price Index
    "Non-Farm Employment Change": 50, "Unemployment Rate": 50,                     # Employment Situation
    "Average Hourly Earnings m/m": 50,
    "ADP Nonfarm Employment Change": 194,                                          # ADP National Employment Report
    "Retail Sales m/m": 9,                                                         # Advance Monthly Sales for Retail and Food Services
    "Advance GDP q/q": 53,                                                         # Gross Domestic Product
    "Core PCE Price Index m/m": 54,                                                # Personal Income and Outlays
    "Prelim UoM Consumer Sentiment": 91,                                           # Surveys of Consumers (Univ. of Michigan)
    "Unemployment Claims": 180,                                                    # Unemployment Insurance Weekly Claims Report
    "Import Prices m/m": 188,                                                      # U.S. Import and Export Price Indexes
    # "Federal Funds Rate" deliberately NOT mapped here — the Federal
    # Reserve's own FOMC calendar page (federalreserve.gov/monetarypolicy/
    # fomccalendars.htm, live-verified reachable, meeting dates published
    # a year+ ahead) is the more authoritative primary source for that
    # one event specifically; not worth a second, weaker path through FRED.
    #
    # Confirmed with NO FRED coverage (live-verified 2026-08-15, not left
    # unchecked): "ISM Manufacturing PMI" / "ISM Services PMI" — FRED is
    # actively REMOVING Institute for Supply Management data entirely
    # (confirmed via fred.stlouisfed.org/series/NAPM redirecting to a
    # "Data To Be Removed from FRED" notice). "Challenger Job Cuts" —
    # zero search results on FRED; it's private-source data (Challenger,
    # Gray & Christmas) FRED has never carried.
}

# --- Contextual sentiment scoring (upgrade over the naive lexicon) ---
# R2 (docs/fundamental-analysis-swot-2026-08-14.md): ENABLE_FINBERT_SENTIMENT
# now defaults ON. The lexicon's one documented failure (BACKTEST_REPORT.md
# case #2 — "rate hike risk IF data surprises" scored as a flat +1.0
# declarative hawkish read) is a structural blind spot, not a fluke, and
# leaving the fix opt-in meant production ran with that blind spot active
# by default. FinBERT is local/free (no network per call, no API cost) and
# already gracefully falls back to the lexicon if torch/transformers
# aren't installed (scoring/finbert_sentiment.py's is_available() check) —
# defaulting it on costs nothing on a machine without the extra deps, and
# fixes a proven failure mode on one that has them. Still overridable via
# ENABLE_FINBERT_SENTIMENT=0 in the environment.
#
# ENABLE_LLM_SENTIMENT stays OPT-IN — unlike FinBERT it's a real per-call
# cost against a paid API, and this environment has no ANTHROPIC_API_KEY
# configured; defaulting a paid, keyless tier on would just silently no-op
# at best and isn't a decision to make without the user's consent either way.
ENABLE_FINBERT_SENTIMENT = os.environ.get("ENABLE_FINBERT_SENTIMENT", "1") != "0"
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
    # Added same day as the three above, same root cause: covered by
    # ACCUMULATOR_MEDIUM_ALLOWLIST and EVENT_SURPRISE_DIRECTION but had no
    # lexicon entry, so it could never produce a print_predictions row.
    "Prelim UoM Consumer Sentiment": {
        "higher": ["consumer sentiment improves", "confidence rises", "sentiment beats estimates", "upside surprise"],
        "lower": ["consumer sentiment falls", "confidence declines", "sentiment misses estimates", "downside surprise"],
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
}
# Confirmed with NO usable Kalshi coverage AT ALL (verified live, not
# left unchecked): Average Hourly Earnings m/m (Kalshi's closest match
# prices a different, inflation-adjusted metric), Core PPI m/m and
# Import Prices m/m (no matching series exists), ISM Services PMI
# (series exists but has zero markets currently listed — dormant).
# These four simply have no entry here and never will unless Kalshi
# lists new markets.

# R4 (docs/fundamental-analysis-swot-2026-08-14.md): the 6 series below
# ticket a specific RELEASE DATE (`-{yy}{MON}{DD}`, e.g.
# "KXUSRETAIL-26AUG14"), not a month — live-verified 2026-08-14 against
# Kalshi's real /events response for each series. Resolved via
# data_layer.kalshi_feed.get_market_read_by_date() /
# _resolve_event_ticker_by_date(), a separate path from the month-suffix
# matching KALSHI_SERIES_BY_EVENT_TITLE above uses. All six already have
# an EVENT_SURPRISE_DIRECTION entry — no new direction-mapping needed.
KALSHI_DATE_TICKETED_SERIES_BY_EVENT_TITLE = {
    "Unemployment Claims": "KXJOBLESSCLAIMS",
    "Advance GDP q/q": "KXGDP",
    "Prelim UoM Consumer Sentiment": "KXUSMICHCSP",
    "Challenger Job Cuts": "KXCHCUTS",
    "PPI m/m": "KXUSPPI",
    "Retail Sales m/m": "KXUSRETAIL",
}

# FOMC/Federal Funds Rate is a discrete cut/hold/hike DECISION, not a
# continuous forecast-vs-actual number — it can't reuse
# EVENT_SURPRISE_DIRECTION's convention, so it gets its own small,
# parallel mapping. Mutually exclusive with KALSHI_SERIES_BY_EVENT_TITLE
# and KALSHI_DATE_TICKETED_SERIES_BY_EVENT_TITLE per title — an event
# title matches at most one of the three dicts.
RATE_DECISION_DIRECTION = {
    "hike": "bullish",
    "hold": "neutral",
    "cut": "bearish",
}
# R4: RE-ENABLED, correcting a real classification bug. This was
# previously emptied on the belief that KXFED is ticketed to a specific
# FOMC MEETING DATE (e.g. "-26mar19") — live-verified 2026-08-14 against
# Kalshi's real /events?series_ticker=KXFED response and that's WRONG:
# real tickers are month-only (e.g. "KXFED-26SEP", "KXFED-26JUL",
# "KXFED-26JUN"), the exact same shape _resolve_event_ticker() (the
# MONTH-ticketed path) already handles — no new date-ticket resolution
# was actually needed for FOMC. scoring/backtest_accumulator.py's
# _read_kalshi_signal() resolves this via the month-ticketed path, using
# event.previous as a target_strike fallback when event.forecast doesn't
# parse (Forex Factory's Federal Funds Rate row doesn't reliably carry a
# numeric forecast for a hold-expected meeting).
KALSHI_RATE_DECISION_SERIES = {"Federal Funds Rate": "KXFED"}

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

# --- Sample-size-aware probability ceiling (R3, docs/fundamental-analysis-swot-2026-08-14.md) ---
# BACKTEST_REPORT.md's own conclusion flagged this: several "correct"
# calls only reached 1%/88%/98% probability from 2-3 signal-bearing
# articles — the sigmoid's k=2.5 saturates toward near-certainty from a
# thin sample regardless of whether that sample is representative.
# scoring/probability_engine.py's agreement x coverage math (see
# _agreement_and_coverage()) already discounts CONFIDENCE for a thin or
# disagreeing sample, but nothing discounted the raw PROBABILITY itself —
# a thin-but-UNANIMOUS sample still produced a 99% probability with 100%
# confidence. This caps how far probability can move from 50% until
# enough signal-bearing weight (articles + structured contributions
# combined) has accumulated, independent of the confidence discount.
# Untuned starting values, same honesty as every other constant in this
# file — needs revisiting once real backtest data exists (see R8).
THIN_SAMPLE_SIGNAL_THRESHOLD = 3     # fewer than this many signal-bearing contributions is "thin"
THIN_SAMPLE_PROBABILITY_CAP = 0.80   # max/min probability allowed on a thin sample — still directional, never near-certain

# --- Macro-backdrop cross-check (R5, docs/fundamental-analysis-swot-2026-08-14.md) ---
# The engine's single biggest identified design gap: every prior signal
# derived from either headline text or a tracked event's own
# forecast-vs-actual surprise — nothing independently checked where the
# dollar/rates market was already positioned. data_layer/macro_backdrop.py
# (DTWEXBGS trade-weighted dollar index + DFII10 10yr real yield, both
# live-verified 2026-08-16) supplies that independent read.
#
# Deliberately a CONFIDENCE modifier only, never a direction override —
# same discipline THIN_SAMPLE_PROBABILITY_CAP already established: no
# real backtested trust weight exists for this signal yet (unlike
# Kalshi/precursor weights, which at least have this project's own
# backtest history behind them), so it's not blended into
# aggregate_usd_sentiment as a weighted vote — it can only pull
# confidence DOWN on a clear disagreement, exactly like a weak
# agreement/coverage read already does, never invent a wrong-direction
# call. Untuned starting value, needs revisiting once real backtest data
# exists.
MACRO_BACKDROP_DISAGREEMENT_CONFIDENCE_MULTIPLIER = 0.7

# --- Correlation/redundancy discount (2026-08-16 follow-up to the R5 review) ---
# _weighted_aggregate()/_agreement_and_coverage() previously treated every
# article contribution as independent evidence — the same standard
# critique the dynamic-factor-model / Bayesian-model-averaging /
# Superforecasting literature all make of naive weighted averaging: a
# wire story and its syndicated rewrite on a second outlet aren't two
# confirmations, they're one fact counted twice. This is a discount on
# the EXISTING weighted-aggregate math, not a new model — right-sized for
# this engine's small per-event contribution count (typically well under
# 10), not a full PCA/factor-model (that's the right tool for hundreds of
# correlated series, not this).
#
# Both conditions are required together — time proximity alone (two
# genuinely different stories breaking the same hour) isn't enough, and
# matched-term overlap alone (two different stories that both happen to
# say "inflation") isn't enough either. Untuned starting values, same
# honesty as every other threshold constant in this file.
REDUNDANCY_TIME_PROXIMITY_MINUTES = 90     # articles further apart than this are never compared for redundancy
REDUNDANCY_TERM_OVERLAP_THRESHOLD = 0.6    # fraction of matched lexicon terms that must overlap (Jaccard) to count as the same underlying story
REDUNDANCY_DISCOUNT_MULTIPLIER = 0.3       # a redundant contribution is still WEAK corroborating evidence, not zero — discounted, not dropped

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
