"""A10: the unused forexfactory_calendar trust weight is gone; the rest are unchanged."""
from config.settings import SOURCE_TRUST_WEIGHTS


def test_no_forexfactory_calendar_weight():
    assert "forexfactory_calendar" not in SOURCE_TRUST_WEIGHTS
    assert SOURCE_TRUST_WEIGHTS == {
        "alpha_vantage_news": 0.7,
        "apitube_news": 0.7,
        "rss_reuters_business": 0.85,
        "rss_cnbc_top_news": 0.6,
        "rss_cnbc_economy": 0.65,
        "rss_investing_com_forex": 0.55,
    }
