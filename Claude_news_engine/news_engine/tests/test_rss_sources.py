# tests/test_rss_sources.py
from __future__ import annotations

import datetime as dt
from unittest.mock import MagicMock, patch

import pytest

from data_layer.rss_sources import RSSNewsSource, RSSParseError

UTC = dt.timezone.utc


def test_parse_error_raises_only_when_asked():
    source = RSSNewsSource("broken_feed", "https://example.com/feed")
    resp = MagicMock(content=b"<rss><channel><item>")
    since = dt.datetime(2026, 10, 21, tzinfo=UTC)
    with patch("data_layer.rss_sources.requests.get", return_value=resp):
        # Default: today's print-and-empty behaviour (the accumulator relies on it).
        assert source.fetch("", since) == []
        with pytest.raises(RSSParseError, match="broken_feed"):
            source.fetch("", since, raise_on_parse_error=True)
