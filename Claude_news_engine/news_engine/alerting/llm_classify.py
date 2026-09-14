"""
Single plain Anthropic API call per ambiguous candidate -- NOT a Claude
Code session, no fixed per-poll-cycle cost. Called only for candidates
triage.py couldn't resolve with a hard rule (see
docs/superpowers/specs/2026-09-14-realtime-news-shock-alerting-design.md).
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import anthropic

from alerting.taxonomy import SHOCK_CATEGORIES
from alerting.triage import TriageResult
from data_layer.news_feed import NewsArticle

_MODEL = "claude-haiku-4-5"
_VALID_SEVERITIES = ("High", "Medium", "Low")


@dataclass
class ClassificationResult:
    category: str
    severity: str
    rationale: str
    classification_failed: bool = False


def _build_prompt(article: NewsArticle, triage: TriageResult) -> str:
    return (
        "Classify this news headline for a forex/macro shock-alerting tool.\n"
        f"Headline: {article.title}\n"
        f"Summary: {article.summary}\n"
        f"Source: {article.source}\n"
        f"Plausible category from initial keyword triage: {triage.category}\n\n"
        f"Valid categories: {', '.join(SHOCK_CATEGORIES)}\n"
        "Respond with ONLY a JSON object, no other text, in exactly this shape:\n"
        '{"category": "<one of the valid categories>", "severity": "High"|"Medium"|"Low", "rationale": "<one sentence>"}\n'
        "severity should reflect how likely this event is to cause an immediate, sharp market "
        "reaction -- not a routine, already-priced-in development."
    )


def _call_model(prompt: str) -> str:
    """
    Isolated so classify_candidate()'s parsing/fallback logic can be unit
    tested by monkeypatching this function instead of mocking the SDK's
    response object shape.
    """
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=_MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def classify_candidate(article: NewsArticle, triage: TriageResult) -> ClassificationResult:
    """
    On any API error or malformed/invalid response: falls back to
    triage.category at severity="Medium" with classification_failed=True
    -- never dropped, never crashes the poll cycle. Caller
    (alerting/poll_once.py) is expected to persist the fallback result
    with classification_method="llm_failed_fallback" for manual review.
    """
    prompt = _build_prompt(article, triage)
    try:
        text = _call_model(prompt)
        data = json.loads(text)
        category = data["category"]
        severity = data["severity"]
        rationale = data["rationale"]
        if category not in SHOCK_CATEGORIES or severity not in _VALID_SEVERITIES:
            raise ValueError(f"model returned invalid category/severity: {data!r}")
        return ClassificationResult(category=category, severity=severity, rationale=rationale)
    except Exception as exc:  # noqa: BLE001 -- any API/parse failure must degrade safely, never crash the poll cycle
        print(f"[llm_classify] WARNING: classification failed for {article.title!r}: {exc}")
        return ClassificationResult(
            category=triage.category,
            severity="Medium",
            rationale=f"LLM classification failed ({exc}) -- falling back to rule-tier category at Medium for manual review.",
            classification_failed=True,
        )
