"""
Severity/category classification for ambiguous shock candidates -- one
plain API call per candidate (NOT a Claude Code session, no fixed
per-poll-cycle cost). Called only for candidates triage.py couldn't
resolve with a hard rule (see
docs/superpowers/specs/2026-09-14-realtime-news-shock-alerting-design.md).

Providers are tried in order: Claude Haiku, then a local Ollama model.
2026-10 change: Anthropic credits ran out and every classification
silently degraded to a Medium fallback that was never pushed to Telegram.
Notification latency is the constraint, so each provider is bounded by a
short timeout and, after any call failure, put on a persisted cooldown
(alerting/store.py's provider_cooldown) so a dead provider costs one
failed call per cooldown window instead of one per headline.
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from typing import Optional

import requests

try:
    import anthropic
    _SDK_AVAILABLE = True
except ImportError:
    _SDK_AVAILABLE = False

from alerting import store
from alerting.taxonomy import SHOCK_CATEGORIES
from alerting.triage import TriageResult
from config.settings import (
    CLAUDE_CLASSIFY_MODEL, CLAUDE_COOLDOWN_MINUTES, CLAUDE_TIMEOUT_SECONDS,
    OLLAMA_BASE_URL, OLLAMA_CLASSIFY_MODEL, OLLAMA_COOLDOWN_MINUTES,
    OLLAMA_KEEP_ALIVE, OLLAMA_TIMEOUT_SECONDS,
)
from data_layer.news_feed import NewsArticle

_VALID_SEVERITIES = ("High", "Medium", "Low")


def is_available() -> bool:
    """
    Whether the optional `anthropic` SDK (requirements-alerting.txt) is
    importable. `anthropic` is opt-in -- poll_once.py imports this module
    unconditionally even for the free, no-LLM hard-rule-tier alerting
    path, so a missing SDK must skip the Claude provider rather than let
    an ImportError at module scope take down the whole poller.
    """
    return _SDK_AVAILABLE


@dataclass
class ClassificationResult:
    category: str
    severity: str
    rationale: str
    classification_failed: bool = False
    provider: Optional[str] = None  # "claude" | "ollama" -- None when every provider failed


def _build_prompt(article: NewsArticle, triage: TriageResult) -> str:
    return (
        "Classify this news headline for a forex/macro shock-alerting tool.\n"
        f"Headline: {article.title}\n"
        f"Summary: {article.summary}\n"
        f"Source: {article.source}\n"
        f"Plausible category from initial keyword triage: {triage.category}\n\n"
        f"Valid categories: {', '.join(SHOCK_CATEGORIES)}\n\n"
        "Severity guide -- how likely is this news to move markets sharply RIGHT NOW?\n"
        '- "High": something concrete and NEW has actually happened that directly hits supply, rates or '
        "risk appetite (an attack, closure, embargo, surprise rate move, default, sanctions imposed, a sudden policy action).\n"
        '- "Medium": a developing situation with real market relevance but no new concrete action yet '
        "(threats, negotiations, official statements of intent, a strike being voted on, escalation warnings).\n"
        '- "Low": routine, scheduled, expected or already priced in (unchanged policy, long-term plans, '
        "denials or de-escalation, commentary, analysis).\n"
        'Most headlines are Medium or Low. Use "High" sparingly.\n\n'
        "Severity examples (headline -> severity):\n"
        "- Gunmen attack oil terminal, exports halted -> High\n"
        "- Union threatens strike at major refinery next month -> Medium\n"
        "- Central bank leaves rates unchanged, as expected -> Low\n"
        "- Minister says no plans for an export ban -> Low\n\n"
        "Respond with ONLY a JSON object, no other text, in exactly this shape:\n"
        '{"category": "<one of the valid categories>", "severity": "High"|"Medium"|"Low", '
        '"rationale": "<one short sentence explaining why, specific to the headline above>"}'
    )


def _call_claude(prompt: str) -> str:
    """
    Isolated so classify_candidate()'s chain/fallback logic can be unit
    tested by monkeypatching this function. max_retries=0 and an explicit
    timeout: the SDK defaults (multi-minute timeout, 2 retries) would let
    one hung request stall the whole 2-minute poll cycle.
    """
    client = anthropic.Anthropic(timeout=CLAUDE_TIMEOUT_SECONDS, max_retries=0)
    response = client.messages.create(
        model=CLAUDE_CLASSIFY_MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def _call_ollama(prompt: str) -> str:
    """
    Local Ollama model (default llama3.2:3b). format="json" constrains the
    output to valid JSON, which matters most for small models;
    temperature 0 keeps classifications repeatable; keep_alive holds the
    model in RAM so the first call after a quiet spell isn't a cold load.
    """
    resp = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json={
            "model": OLLAMA_CLASSIFY_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json",
            "keep_alive": OLLAMA_KEEP_ALIVE,
            "options": {"temperature": 0, "num_predict": 200},
        },
        timeout=OLLAMA_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def _providers() -> list[tuple]:
    """
    (name, call, is_usable, cooldown_minutes), in priority order. Built at
    call time (not module scope) so tests can monkeypatch the call
    functions and is_available().
    """
    return [
        ("claude", _call_claude, is_available, CLAUDE_COOLDOWN_MINUTES),
        ("ollama", _call_ollama, lambda: True, OLLAMA_COOLDOWN_MINUTES),
    ]


def _parse_and_validate(text: str) -> tuple[str, str, str]:
    """
    Normalizes surface form only (case, spaces) -- smaller local models
    often answer "high" or "Central Bank" -- then enforces the real
    category/severity vocabularies.
    """
    data = json.loads(text)
    category = str(data["category"]).strip().lower().replace(" ", "_")
    severity = str(data["severity"]).strip().capitalize()
    rationale = str(data.get("rationale") or "").strip()
    if category not in SHOCK_CATEGORIES or severity not in _VALID_SEVERITIES:
        raise ValueError(f"model returned invalid category/severity: {data!r}")
    return category, severity, rationale


def classify_candidate(
    article: NewsArticle, triage: TriageResult,
    conn=None, now: Optional[dt.datetime] = None,
) -> ClassificationResult:
    """
    Tries each provider in order. A provider is skipped if unavailable or
    cooling down; a call that raises puts it on cooldown (only when `conn`
    is given -- cooldown state lives in the alerts DB); an unusable
    response (bad JSON, invalid category) moves on to the next provider
    without a cooldown, since the provider itself is up.

    If every provider fails: falls back to triage.category at
    severity="Medium" with classification_failed=True -- never dropped,
    never crashes the poll cycle. The caller (alerting/poll_once.py)
    persists it with classification_method="llm_failed_fallback" and
    pushes it to Telegram labelled UNCLASSIFIED.
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    prompt = _build_prompt(article, triage)
    problems: list[str] = []

    for name, call, is_usable, cooldown_minutes in _providers():
        if not is_usable():
            problems.append(f"{name}: not available")
            continue
        if conn is not None:
            until = store.get_provider_cooldown_until(conn, name)
            if until is not None and now < until:
                problems.append(f"{name}: cooling down until {until.strftime('%H:%M')}Z")
                continue
        try:
            text = call(prompt)
        except Exception as exc:  # noqa: BLE001 -- any provider failure must degrade to the next one, never crash the poll cycle
            print(f"[llm_classify] WARNING: {name} call failed for {article.title!r}: {exc}")
            problems.append(f"{name}: {exc}")
            if conn is not None:
                store.set_provider_cooldown(conn, name, now + dt.timedelta(minutes=cooldown_minutes))
            continue
        try:
            category, severity, rationale = _parse_and_validate(text)
        except Exception as exc:  # noqa: BLE001
            print(f"[llm_classify] WARNING: {name} returned an unusable response for {article.title!r}: {exc}")
            problems.append(f"{name}: unusable response ({exc})")
            continue
        return ClassificationResult(category=category, severity=severity, rationale=rationale, provider=name)

    detail = "; ".join(problems)
    print(f"[llm_classify] WARNING: all providers failed for {article.title!r}: {detail}")
    return ClassificationResult(
        category=triage.category,
        severity="Medium",
        rationale=f"LLM classification failed ({detail}) -- falling back to rule-tier category at Medium for manual review.",
        classification_failed=True,
    )
