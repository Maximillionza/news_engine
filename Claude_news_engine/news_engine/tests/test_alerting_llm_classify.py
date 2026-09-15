from __future__ import annotations

import datetime as dt
from unittest.mock import patch

from alerting.llm_classify import classify_candidate
from alerting.triage import TriageResult
from data_layer.news_feed import NewsArticle

UTC = dt.timezone.utc


def _article() -> NewsArticle:
    return NewsArticle(
        title="Oil prices tick higher on OPEC+ output chatter", summary="",
        source="test", source_type="rss_test",
        published_utc=dt.datetime(2026, 9, 14, tzinfo=UTC), url="https://example.com",
    )


def _triage() -> TriageResult:
    return TriageResult(matched=True, category="energy", rule_tier_hit=False, matched_keywords=["opec+"], near_miss_score=None)


def test_valid_model_response_parses_into_result():
    with patch("alerting.llm_classify._call_model", return_value='{"category": "energy", "severity": "Medium", "rationale": "Routine OPEC+ commentary, not a supply disruption."}'):
        result = classify_candidate(_article(), _triage())
    assert result.category == "energy"
    assert result.severity == "Medium"
    assert result.classification_failed is False


def test_malformed_json_falls_back_to_medium():
    with patch("alerting.llm_classify._call_model", return_value="not json at all"):
        result = classify_candidate(_article(), _triage())
    assert result.severity == "Medium"
    assert result.classification_failed is True
    assert result.category == "energy"  # falls back to triage's own category


def test_invalid_category_in_response_falls_back():
    with patch("alerting.llm_classify._call_model", return_value='{"category": "not_a_real_category", "severity": "High", "rationale": "x"}'):
        result = classify_candidate(_article(), _triage())
    assert result.classification_failed is True
    assert result.severity == "Medium"


def test_api_call_raising_falls_back():
    with patch("alerting.llm_classify._call_model", side_effect=RuntimeError("network down")):
        result = classify_candidate(_article(), _triage())
    assert result.classification_failed is True
    assert result.severity == "Medium"


def test_sdk_unavailable_falls_back_without_calling_model():
    with patch("alerting.llm_classify.is_available", return_value=False), \
         patch("alerting.llm_classify._call_model") as mock_call:
        result = classify_candidate(_article(), _triage())
    mock_call.assert_not_called()
    assert result.classification_failed is True
    assert result.severity == "Medium"
    assert result.category == "energy"  # falls back to triage's own category
