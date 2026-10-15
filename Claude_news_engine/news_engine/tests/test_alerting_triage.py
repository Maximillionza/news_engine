from __future__ import annotations

import datetime as dt

from alerting.triage import triage_article
from data_layer.news_feed import NewsArticle

UTC = dt.timezone.utc


def _article(title: str, summary: str = "") -> NewsArticle:
    return NewsArticle(
        title=title, summary=summary, source="test", source_type="rss_test",
        published_utc=dt.datetime(2026, 9, 14, tzinfo=UTC), url="https://example.com",
    )


def test_hard_rule_pattern_gives_rule_tier_hit():
    result = triage_article(_article("Iran says Strait of Hormuz closed after clash"))
    assert result.matched is True
    assert result.rule_tier_hit is True
    assert result.category == "energy"


def test_category_signal_keyword_gives_ambiguous_candidate():
    result = triage_article(_article("Oil prices tick higher on OPEC+ output chatter"))
    assert result.matched is True
    assert result.rule_tier_hit is False
    assert result.category == "energy"


def test_no_match_returns_matched_false():
    # Deliberately picked to have zero incidental substring overlap with
    # any CATEGORY_SIGNAL_KEYWORDS phrase word (see
    # test_partial_keyword_overlap_gets_positive_near_miss_score for why
    # that matters -- ordinary words like "award" or "wins" can
    # coincidentally contain a keyword's substring, e.g. "war" in "award", or "at" in "cat" once the phrase "blast at" existed).
    result = triage_article(_article("Puppy show draws big crowd today"))
    assert result.matched is False
    assert result.category is None
    assert result.rule_tier_hit is False
    assert result.near_miss_score == 0.0
    assert result.near_miss_category is None


def test_partial_keyword_overlap_gets_positive_near_miss_score():
    # Contains "hormuz" (one of the three words in the "strait of hormuz"
    # CATEGORY_SIGNAL_KEYWORDS phrase) but not "strait" or "of" alongside
    # it, so the full phrase never matches and this falls through to the
    # no-match branch -- but the partial overlap should still register.
    result = triage_article(_article("Tensions near Hormuz keep traders cautious"))
    assert result.matched is False
    assert result.category is None
    assert result.near_miss_score is not None
    assert result.near_miss_score > 0.0
    assert result.near_miss_category is not None


def test_matching_checks_title_and_summary():
    result = triage_article(_article("Markets steady", summary="Reports confirm: Strait of Hormuz closed overnight"))
    assert result.matched is True
    assert result.rule_tier_hit is True


import pytest


@pytest.mark.parametrize("headline", [
    "Explosions heard in Riyadh, Saudi capital",
    "Multiple explosions rock Riyadh as Houthis claim missile attack",
    "Drone attack on Riyadh airport",
    "Blast at Gulf oil terminal after drone strike",
    "Bombing reported near Saudi Aramco facility",
])
def test_attack_wording_without_the_exact_strike_phrases_still_triages_as_geopolitical(headline):
    # Regression: "explosions in Riyadh" matched no signal keyword (only "missile strike",
    # "airstrike", ... existed) and was never classified or pushed.
    result = triage_article(_article(headline))
    assert result.matched is True
    assert result.category == "geopolitical_conflict"


@pytest.mark.parametrize("headline", [
    "US sued over plan to blast Utah canyon inscribed by 19th century 'Buffalo Soldiers'",
    "Rep. Ilhan Omar blasts federal criminal raid on home: 'I will not be silenced'",
    "Analyst blasts central bank for ignoring the bond market",
])
def test_blast_as_a_verb_does_not_triage_as_geopolitical(headline):
    # Regression from the 2026-10-08 keyword addition: bare "blast" matched the verb ("blasts",
    # "to blast") and pushed two unrelated stories as geopolitical Medium alerts.
    assert triage_article(_article(headline)).matched is False


@pytest.mark.parametrize("headline", [
    "Loud blast at Riyadh airport as travellers evacuated and airlines cancel flights",
    "Multiple people wounded in blast at Riyadh airport, say eyewitnesses",
    "Blast rocks Saudi oil facility, fire reported",
    "Blast near Aramco site kills two",
])
def test_blast_as_an_explosion_still_triages(headline):
    assert triage_article(_article(headline)).category == "geopolitical_conflict"


# --- earthquake magnitude floor (impact audit 2026-10-15: 6 earthquake alerts, mostly M5-6, no measurable market effect) ---

@pytest.mark.parametrize("headline", [
    "Magnitude 5.7 earthquake strikes Mindanao, Philippines, GFZ says - Reuters",
    "Magnitude 5.3 earthquake hits Indonesia's Minahasa, EMSC says - Reuters",
    "Earthquake of magnitude 6.1 shakes northern Chile",
    "M4.9 earthquake rattles Tokyo",
])
def test_small_earthquakes_below_the_floor_are_not_alerts(headline):
    assert triage_article(_article(headline)).matched is False


@pytest.mark.parametrize("headline", [
    "Panama suffers over 200 aftershocks after Friday's 7.7-magnitude earthquake - Reuters",
    "Magnitude 6.8 earthquake strikes off Taiwan, chip plants evacuated",
    "Strong earthquake strikes Japan, tsunami warning issued",  # no magnitude stated: never filtered on a guess
])
def test_big_or_unquantified_earthquakes_still_alert(headline):
    assert triage_article(_article(headline)).category == "natural_disaster_supply_chain"


def test_a_small_quake_near_a_real_supply_chain_phrase_is_not_suppressed():
    result = triage_article(_article("Magnitude 5.2 earthquake forces port closed at Kaohsiung"))
    assert result.matched is True
