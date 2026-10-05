from __future__ import annotations

import datetime as dt
from unittest.mock import MagicMock, patch

import pytest

from alerting import llm_classify, store
from alerting.llm_classify import classify_candidate
from alerting.triage import TriageResult
from data_layer.news_feed import NewsArticle

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 10, 5, 12, 0, tzinfo=UTC)

_GOOD = '{"category": "energy", "severity": "Medium", "rationale": "Routine OPEC+ commentary, not a supply disruption."}'


def _article() -> NewsArticle:
    return NewsArticle(
        title="Oil prices tick higher on OPEC+ output chatter", summary="",
        source="test", source_type="rss_test",
        published_utc=dt.datetime(2026, 9, 14, tzinfo=UTC), url="https://example.com",
    )


def _triage() -> TriageResult:
    return TriageResult(matched=True, category="energy", rule_tier_hit=False, matched_keywords=["opec+"], near_miss_score=None)


def test_claude_success_is_used_and_ollama_never_called():
    with patch("alerting.llm_classify._call_claude", return_value=_GOOD), \
         patch("alerting.llm_classify._call_ollama") as ollama:
        result = classify_candidate(_article(), _triage())
    assert result.category == "energy"
    assert result.severity == "Medium"
    assert result.classification_failed is False
    assert result.provider == "claude"
    ollama.assert_not_called()


def test_claude_failure_falls_through_to_ollama():
    with patch("alerting.llm_classify._call_claude", side_effect=RuntimeError("credit balance is too low")), \
         patch("alerting.llm_classify._call_ollama", return_value=_GOOD):
        result = classify_candidate(_article(), _triage())
    assert result.classification_failed is False
    assert result.provider == "ollama"
    assert result.severity == "Medium"


def test_unusable_claude_response_falls_through_to_ollama_without_cooldown():
    conn = store.get_connection(":memory:")
    with patch("alerting.llm_classify._call_claude", return_value="not json at all"), \
         patch("alerting.llm_classify._call_ollama", return_value=_GOOD):
        result = classify_candidate(_article(), _triage(), conn=conn, now=NOW)
    assert result.provider == "ollama"
    # Claude answered (just badly) -- the provider is up, so it must not be put on cooldown.
    assert store.get_provider_cooldown_until(conn, "claude") is None


def test_claude_call_failure_sets_cooldown_and_next_call_skips_claude():
    conn = store.get_connection(":memory:")
    claude = MagicMock(side_effect=RuntimeError("credit balance is too low"))
    with patch("alerting.llm_classify._call_claude", claude), \
         patch("alerting.llm_classify._call_ollama", return_value=_GOOD):
        classify_candidate(_article(), _triage(), conn=conn, now=NOW)
        assert claude.call_count == 1
        assert store.get_provider_cooldown_until(conn, "claude") > NOW

        # Two minutes later: still cooling down, so Claude is not even attempted.
        later = NOW + dt.timedelta(minutes=2)
        result = classify_candidate(_article(), _triage(), conn=conn, now=later)
    assert claude.call_count == 1
    assert result.provider == "ollama"


def test_claude_is_retried_after_its_cooldown_expires():
    conn = store.get_connection(":memory:")
    claude = MagicMock(side_effect=[RuntimeError("down"), _GOOD])
    with patch("alerting.llm_classify._call_claude", claude), \
         patch("alerting.llm_classify._call_ollama", return_value=_GOOD):
        classify_candidate(_article(), _triage(), conn=conn, now=NOW)
        after_cooldown = NOW + dt.timedelta(minutes=llm_classify.CLAUDE_COOLDOWN_MINUTES + 1)
        result = classify_candidate(_article(), _triage(), conn=conn, now=after_cooldown)
    assert claude.call_count == 2
    assert result.provider == "claude"


def test_all_providers_failing_falls_back_to_unclassified_medium():
    with patch("alerting.llm_classify._call_claude", side_effect=RuntimeError("claude down")), \
         patch("alerting.llm_classify._call_ollama", side_effect=RuntimeError("ollama down")):
        result = classify_candidate(_article(), _triage())
    assert result.classification_failed is True
    assert result.severity == "Medium"
    assert result.category == "energy"  # falls back to triage's own category
    assert result.provider is None
    assert "claude down" in result.rationale and "ollama down" in result.rationale


def test_invalid_category_from_every_provider_falls_back():
    bad = '{"category": "not_a_real_category", "severity": "High", "rationale": "x"}'
    with patch("alerting.llm_classify._call_claude", return_value=bad), \
         patch("alerting.llm_classify._call_ollama", return_value=bad):
        result = classify_candidate(_article(), _triage())
    assert result.classification_failed is True
    assert result.severity == "Medium"


def test_sdk_unavailable_skips_claude_and_uses_ollama():
    with patch("alerting.llm_classify.is_available", return_value=False), \
         patch("alerting.llm_classify._call_claude") as claude, \
         patch("alerting.llm_classify._call_ollama", return_value=_GOOD):
        result = classify_candidate(_article(), _triage())
    claude.assert_not_called()
    assert result.provider == "ollama"
    assert result.classification_failed is False


def test_sdk_unavailable_and_ollama_down_falls_back_without_calling_claude():
    with patch("alerting.llm_classify.is_available", return_value=False), \
         patch("alerting.llm_classify._call_claude") as claude, \
         patch("alerting.llm_classify._call_ollama", side_effect=RuntimeError("connection refused")):
        result = classify_candidate(_article(), _triage())
    claude.assert_not_called()
    assert result.classification_failed is True
    assert result.severity == "Medium"
    assert result.category == "energy"


@pytest.mark.parametrize("raw_category,raw_severity", [
    ("Energy", "medium"), (" energy ", "MEDIUM"), ("energy", "Medium"),
])
def test_surface_form_of_category_and_severity_is_normalized(raw_category, raw_severity):
    response = f'{{"category": "{raw_category}", "severity": "{raw_severity}", "rationale": "ok"}}'
    with patch("alerting.llm_classify._call_claude", side_effect=RuntimeError("x")), \
         patch("alerting.llm_classify._call_ollama", return_value=response):
        result = classify_candidate(_article(), _triage())
    assert (result.category, result.severity) == ("energy", "Medium")
    assert result.classification_failed is False


def test_space_separated_multiword_category_is_normalized():
    response = '{"category": "geopolitical conflict", "severity": "High", "rationale": "ok"}'
    with patch("alerting.llm_classify._call_claude", side_effect=RuntimeError("x")), \
         patch("alerting.llm_classify._call_ollama", return_value=response):
        result = classify_candidate(_article(), _triage())
    assert result.category == "geopolitical_conflict"


def test_missing_rationale_from_small_model_is_tolerated():
    response = '{"category": "energy", "severity": "Low"}'
    with patch("alerting.llm_classify._call_claude", side_effect=RuntimeError("x")), \
         patch("alerting.llm_classify._call_ollama", return_value=response):
        result = classify_candidate(_article(), _triage())
    assert result.classification_failed is False
    assert result.rationale == ""


def test_ollama_request_uses_json_mode_low_temperature_and_keep_alive():
    fake_response = MagicMock()
    fake_response.json.return_value = {"message": {"content": _GOOD}}
    with patch("alerting.llm_classify.requests.post", return_value=fake_response) as post:
        text = llm_classify._call_ollama("the prompt")
    assert text == _GOOD
    body = post.call_args.kwargs["json"]
    assert body["format"] == "json"
    assert body["stream"] is False
    assert body["options"]["temperature"] == 0
    # Without an explicit context Ollama loads this model with a 131072-token window (~18 GB).
    assert body["options"]["num_ctx"] == llm_classify.OLLAMA_NUM_CTX <= 8192
    assert body["keep_alive"] == llm_classify.OLLAMA_KEEP_ALIVE
    assert body["model"] == llm_classify.OLLAMA_CLASSIFY_MODEL
    assert body["messages"][0]["content"] == "the prompt"
    assert post.call_args.kwargs["timeout"] == llm_classify.OLLAMA_TIMEOUT_SECONDS
    fake_response.raise_for_status.assert_called_once()


def test_claude_client_is_built_with_a_short_timeout_and_no_retries():
    sdk = MagicMock()
    sdk.Anthropic.return_value.messages.create.return_value.content = [MagicMock(type="text", text=_GOOD)]
    with patch.object(llm_classify, "anthropic", sdk, create=True):
        text = llm_classify._call_claude("the prompt")
    assert text == _GOOD
    sdk.Anthropic.assert_called_once_with(timeout=llm_classify.CLAUDE_TIMEOUT_SECONDS, max_retries=0)


# --- polarity: which way the headline pushes things (alerting/direction.py) ---

def _classify_with(response: str):
    with patch("alerting.llm_classify._call_claude", return_value=response):
        return classify_candidate(_article(), _triage())


def test_polarity_is_parsed_and_normalized():
    result = _classify_with('{"category": "energy", "severity": "High", "polarity": "De-escalation", "rationale": "x"}')
    assert result.polarity == "relief"
    assert result.classification_failed is False


@pytest.mark.parametrize("body", [
    '{"category": "energy", "severity": "Low", "rationale": "x"}',
    '{"category": "energy", "severity": "Low", "polarity": "sideways", "rationale": "x"}',
    '{"category": "energy", "severity": "Low", "polarity": null, "rationale": "x"}',
])
def test_missing_or_garbled_polarity_is_unclear_and_does_not_fail_the_classification(body):
    result = _classify_with(body)
    assert result.polarity == "unclear"
    assert result.classification_failed is False
    assert (result.category, result.severity) == ("energy", "Low")


def test_prompt_asks_for_polarity_with_the_full_vocabulary():
    prompt = llm_classify._build_prompt(_article(), _triage())
    assert '"polarity"' in prompt
    for word in ("escalation", "relief", "hawkish", "dovish", "unclear"):
        assert word in prompt


def test_failed_classification_has_unclear_polarity():
    with patch("alerting.llm_classify._call_claude", side_effect=RuntimeError("down")), \
         patch("alerting.llm_classify._call_ollama", side_effect=RuntimeError("down")):
        result = classify_candidate(_article(), _triage())
    assert result.classification_failed is True
    assert result.polarity == "unclear"
