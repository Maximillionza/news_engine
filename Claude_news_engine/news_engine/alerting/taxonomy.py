"""
Real-time shock taxonomy for alerting/triage.py — deliberately broader
than docs/News_Engine_Causation_Matrix_v2.xlsx's AdHoc_Category_Taxonomy
(that 8-category set was sized for backward-looking backtest research on
already-detected price anomalies; live headlines need a wider net). See
docs/superpowers/specs/2026-09-14-realtime-news-shock-alerting-design.md.

HARD_RULE_PATTERNS: an exact-phrase match here skips the LLM entirely and
is always severity="High" -- reserved for genuinely unambiguous events
(a named chokepoint closure, a war declaration) where waiting on an LLM
call would cost real seconds for no judgment benefit.

CATEGORY_SIGNAL_KEYWORDS: a match here means "plausible candidate," not
an automatic tier -- escalated to llm_classify.py for a real severity
judgment. Broader and noisier than HARD_RULE_PATTERNS by design.

Both are v1, researched from real historical wire-service phrasing per
category, not exhaustive -- expected to grow as shock_near_misses (see
alerting/store.py's record_near_miss()) surfaces real missed events.
"""
from __future__ import annotations

SHOCK_CATEGORIES = [
    "energy",
    "geopolitical_conflict",
    "central_bank",
    "sovereign_fiscal",
    "trade_policy",
    "natural_disaster_supply_chain",
]

NEAR_MISS_LOG_THRESHOLD = 0.3  # triage.py's near_miss_score scale — tunable once real examples exist

HARD_RULE_PATTERNS: dict[str, list[str]] = {
    "energy": [
        "strait of hormuz closed",
        "strait of hormuz blocked",
        "strait of hormuz shut",
        "bab el-mandeb closed",
        "opec+ agrees to cut",
        "opec+ agrees to increase",
        "oil export ban",
        "tanker attacked",
        "pipeline attack",
    ],
    "geopolitical_conflict": [
        "declares war",
        "declaration of war",
        "military invasion",
        "state of war declared",
    ],
    "central_bank": [
        "emergency rate decision",
        "unscheduled rate cut",
        "unscheduled rate hike",
        "fed chair fired",
        "fed chair resigns",
    ],
    "sovereign_fiscal": [
        "sovereign default",
        "credit rating downgraded",
    ],
    "trade_policy": [
        "retaliatory tariffs announced",
    ],
    "natural_disaster_supply_chain": [
        "suez canal blocked",
    ],
}

CATEGORY_SIGNAL_KEYWORDS: dict[str, list[str]] = {
    "energy": [
        "strait of hormuz", "strait of malacca", "bab el-mandeb", "opec+", "opec output",
        "oil pipeline", "refinery strike", "sanctions on oil", "chokepoint", "shipping lane",
        "houthi attack", "oil production cut", "oil production increase",
    ],
    "geopolitical_conflict": [
        "invasion", "airstrike", "missile strike", "military strike", "state of emergency",
        "coup d'etat", "martial law", "ceasefire collapses", "troops mobilized",
    ],
    "central_bank": [
        "emergency meeting", "surprise rate move", "central bank independence",
        "intervenes in currency market", "central bank governor resigns",
    ],
    "sovereign_fiscal": [
        "credit rating upgraded", "government shutdown begins", "government shutdown ends",
        "debt ceiling", "treasury buyback", "fiscal emergency",
    ],
    "trade_policy": [
        "tariffs announced", "tariffs imposed", "trade war escalates", "export ban",
        "import ban", "trade deal collapses",
    ],
    "natural_disaster_supply_chain": [
        "earthquake", "hurricane", "port closed", "supply chain disruption",
        "factory shutdown", "chip shortage", "grounded ships",
    ],
}
