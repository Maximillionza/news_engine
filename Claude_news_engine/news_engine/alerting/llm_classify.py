"""
Severity/category classification for ambiguous shock candidates -- one
plain API call per candidate (NOT a Claude Code session, no fixed
per-poll-cycle cost). Called only for candidates triage.py couldn't
resolve with a hard rule (see
docs/superpowers/specs/2026-09-14-realtime-news-shock-alerting-design.md).

Providers are tried in config.settings.CLASSIFIER_PROVIDER_ORDER: a local
Ollama model first, then Claude Haiku as the fallback (owner decision
2026-10-21, B2 K8 -- Anthropic credits are exhausted; until then it was
Claude first).
2026-10 change: Anthropic credits ran out and every classification
silently degraded to a Medium fallback that was never pushed to Telegram.
Notification latency is the constraint, so each provider is bounded by a
short timeout and, after any call failure, put on a persisted cooldown
(alerting/store.py's provider_cooldown) so a dead provider costs one
failed call per cooldown window instead of one per headline.

Besides category/severity the model is asked for polarity, country and US
link (alerting/us_link.py). Those three are best-effort: a missing or
garbled answer reads as unknown and never fails the classification.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

try:
    import anthropic
    _SDK_AVAILABLE = True
except ImportError:
    _SDK_AVAILABLE = False

from alerting import store
from alerting.direction import normalize_polarity
from alerting.taxonomy import SHOCK_CATEGORIES
from alerting.triage import TriageResult
from alerting.us_link import normalize_country, normalize_us_link, reconcile
from config.settings import (
    CLASSIFIER_PROVIDER_ORDER, CLAUDE_CLASSIFY_MODEL, CLAUDE_COOLDOWN_MINUTES, CLAUDE_TIMEOUT_SECONDS,
    OLLAMA_BASE_URL, OLLAMA_CLASSIFY_MODEL, OLLAMA_COOLDOWN_MINUTES, OLLAMA_EXECUTABLE,
    OLLAMA_KEEP_ALIVE, OLLAMA_NUM_CTX, OLLAMA_STARTUP_WAIT_SECONDS, OLLAMA_TIMEOUT_SECONDS,
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
    polarity: str = "unclear"       # alerting/direction.py POLARITIES; "unclear" also when the model omitted/garbled it
    country: Optional[str] = None   # ISO-2 or "XX" (global / several); None = unknown
    us_link: Optional[str] = None   # alerting/us_link.py US_LINKS; None = unknown
    all_providers_failed: bool = False  # every provider failed/was skipped -- the outage signal; NOT set by poll_once's budget-spent fallback


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
        "Polarity guide -- which way does THIS headline push things?\n"
        '- "escalation": the situation gets worse (attack, closure, embargo, sanctions or tariffs imposed, '
        "default, supply cut, threat of any of these).\n"
        '- "relief": the situation eases (ceasefire, reopening, deal, tariffs suspended, supply increase, '
        "a denial that a feared measure will happen).\n"
        '- "hawkish" or "dovish": ONLY for central-bank news -- tighter or looser policy.\n'
        '- "unclear": none of these clearly applies, or it is only commentary.\n\n'
        "Polarity examples (headline -> polarity):\n"
        "- Gunmen attack oil terminal, exports halted -> escalation\n"
        "- Rival factions sign ceasefire, shipping lanes reopen -> relief\n"
        "- Central bank signals more rate hikes -> hawkish\n"
        "- Analysts debate outlook for oil next year -> unclear\n"
        # Real-feed phrasings a small model got backwards (B2 K4): a price FALL on peace talk and a
        # sanctions WAIVER are relief; a price spike on attacks is escalation.
        "- Oil prices fall as traders watch ceasefire talks -> relief\n"
        "- Trump waives broad new Russia sanctions -> relief\n"
        "- Brent oil touches $110 as Iran escalates Hormuz attacks -> escalation\n\n"
        'Country: the ISO 3166-1 alpha-2 code of where it happens or of the main actor (e.g. "US", "RU", '
        '"FR"); "XX" if it is global or involves several countries.\n\n'
        "US link guide -- how does this reach US prices?\n"
        '- "direct": it happens in the US or a US actor does it (the Fed, the US government or Treasury, '
        "US companies or markets).\n"
        '- "global_supply": it happens elsewhere but changes a supply the whole world prices '
        "(oil or gas output or exports, OPEC+ decisions, a shipping chokepoint such as Hormuz, "
        "Bab el-Mandeb or Suez).\n"
        '- "none": a local event outside the US with neither link (domestic unrest, a strike on a local site, '
        "a local company's outage).\n"
        'If us_link is "none", severity is at most "Medium".\n\n'
        "US link examples (headline -> country, us_link):\n"
        "- Fed chair signals emergency cut -> US, direct\n"
        "- Tanker struck near Strait of Hormuz -> XX, global_supply\n"
        "- Protesters clash with police in Lima -> PE, none\n\n"
        "Respond with ONLY a JSON object, no other text, in exactly this shape:\n"
        '{"category": "<one of the valid categories>", "severity": "High"|"Medium"|"Low", '
        '"polarity": "escalation"|"relief"|"hawkish"|"dovish"|"unclear", '
        '"country": "<ISO-2 code or XX>", "us_link": "direct"|"global_supply"|"none", '
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


def _start_ollama() -> bool:
    """
    Starts `ollama serve` detached from this process and waits (bounded) for
    it to answer. Ollama's Windows app is a tray program, not a service, and
    its auto-updater shuts the server down (2026-10-11 22:40) without
    bringing it back, so a refused connection is a recoverable state, not a
    dead fallback. Returns True once the server responds.
    """
    exe = Path(os.path.expandvars(OLLAMA_EXECUTABLE))
    if not exe.exists():
        print(f"[llm_classify] WARNING: cannot start Ollama -- {exe} not found")
        return False
    print("[llm_classify] Ollama is not running -- starting it")
    flags = 0
    breakaway = getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0)
    if os.name == "nt":  # survive this short-lived poll process; no console window
        flags = (subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                 | subprocess.CREATE_NO_WINDOW | breakaway)
    quiet = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        subprocess.Popen([str(exe), "serve"], creationflags=flags, **quiet)
    except OSError:  # breakaway not permitted by the parent job -- retry without it
        subprocess.Popen([str(exe), "serve"], creationflags=flags & ~breakaway, **quiet)
    deadline = time.monotonic() + OLLAMA_STARTUP_WAIT_SECONDS
    while time.monotonic() < deadline:
        try:
            requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
            return True
        except requests.ConnectionError:
            time.sleep(1)
    print("[llm_classify] WARNING: Ollama did not come up in time")
    return False


def _post_ollama(prompt: str) -> str:
    resp = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json={
            "model": OLLAMA_CLASSIFY_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json",
            "keep_alive": OLLAMA_KEEP_ALIVE,
            "options": {"temperature": 0, "num_predict": 200, "num_ctx": OLLAMA_NUM_CTX},
        },
        timeout=OLLAMA_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def _call_ollama(prompt: str) -> str:
    """
    Local Ollama model (default llama3.2:3b). format="json" constrains the
    output to valid JSON, which matters most for small models;
    temperature 0 keeps classifications repeatable; keep_alive holds the
    model in RAM so the first call after a quiet spell isn't a cold load.
    A refused connection means the server is down: start it and retry once.
    """
    try:
        return _post_ollama(prompt)
    except requests.ConnectionError:
        if not _start_ollama():
            raise
        return _post_ollama(prompt)


def _providers() -> list[tuple]:
    """
    (name, call, is_usable, cooldown_minutes), in CLASSIFIER_PROVIDER_ORDER
    order; a name with no provider behind it is skipped. Built at call time
    (not module scope) so tests can monkeypatch the call functions,
    is_available() and the order.
    """
    known = {
        "claude": ("claude", _call_claude, is_available, CLAUDE_COOLDOWN_MINUTES),
        "ollama": ("ollama", _call_ollama, lambda: True, OLLAMA_COOLDOWN_MINUTES),
    }
    return [known[name] for name in CLASSIFIER_PROVIDER_ORDER if name in known]


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


def _extract_polarity(text: str) -> str:
    """
    Polarity is best-effort: a small model that omits or garbles it still gave
    a valid category/severity, so that must not fail the whole classification.
    The alert just reads "no clear lean" instead of guessing a direction.
    """
    try:
        return normalize_polarity(json.loads(text).get("polarity"))
    except Exception:  # noqa: BLE001 -- _parse_and_validate already accepted this text; never let polarity break it
        return "unclear"


def _extract_country_and_us_link(text: str) -> tuple[Optional[str], Optional[str]]:
    """
    Best-effort like _extract_polarity: an omitted or garbled country / US
    link reads as unknown (None), which keeps today's behaviour (no cap),
    and never fails the classification. reconcile() makes a US event
    "direct" whatever the model said.
    """
    try:
        data = json.loads(text)
        country = normalize_country(data.get("country"))
        return country, reconcile(country, normalize_us_link(data.get("us_link")))
    except Exception:  # noqa: BLE001 -- _parse_and_validate already accepted this text; never let these break it
        return None, None


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
        country, us_link = _extract_country_and_us_link(text)
        return ClassificationResult(
            category=category, severity=severity, rationale=rationale, provider=name,
            polarity=_extract_polarity(text), country=country, us_link=us_link,
        )

    detail = "; ".join(problems)
    print(f"[llm_classify] WARNING: all providers failed for {article.title!r}: {detail}")
    return ClassificationResult(
        category=triage.category,
        severity="Medium",
        rationale=f"LLM classification failed ({detail}) -- falling back to rule-tier category at Medium for manual review.",
        classification_failed=True,
        all_providers_failed=True,
    )
