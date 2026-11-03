from __future__ import annotations

import datetime as dt

from alerting import triage as triage_module
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
    # FIX C1: a phrase found only in the summary still matches, and goes to the classifier.
    result = triage_article(_article("Markets steady", summary="Reports confirm: Strait of Hormuz closed overnight"))
    assert result.matched is True
    assert result.rule_tier_hit is False
    assert result.guard_reason == "summary_only"


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


def test_gold_bar_tariff_headline_triages_as_trade_policy_without_a_hard_rule():
    result = triage_article(_article("US slaps tariffs on gold bars"))
    assert result.matched is True
    assert result.category == "trade_policy"
    assert result.rule_tier_hit is False


# --- FIX C1: guards in front of the rule tier. A guarded hit stays matched and goes to the classifier ---

_LIVE_ID_1 = "U.S. oil falls below $100 as Saudi Arabia reportedly offers more crude via Hormuz after pipeline attack"
_LIVE_ID_5 = "Aramco halts October crude deliveries to some European refiners after pipeline attack, Bloomberg reports - reuters.com"
_LIVE_ID_7 = "U.S. urges Americans to reconsider Middle East travel as Iran tensions rise"


def _assert_guarded(result, reason: str) -> None:
    assert result.matched is True
    assert result.rule_tier_hit is False
    assert result.guard_reason == reason


def test_guard_reasons_are_the_five_in_priority_order():
    assert triage_module.GUARD_REASONS == ("summary_only", "denial", "price_report", "commentary", "unknown_us_link")


def test_live_commentary_alerts_leave_the_rule_tier():
    _assert_guarded(triage_article(_article(_LIVE_ID_1)), "price_report")
    _assert_guarded(triage_article(_article(_LIVE_ID_5)), "unknown_us_link")
    _assert_guarded(triage_article(_article(_LIVE_ID_7, summary="strait of hormuz closed, officials said")), "summary_only")


@pytest.mark.parametrize("headline", [
    "Iran denies strait of hormuz closed",
    "Saudi Arabia rules out oil export ban",
    "False report says Fed chair resigns",
    "Strait of Hormuz closed rumour unconfirmed",
    "OPEC+ agrees to cut? Delegates say it has not",
    "Iran denied strait of hormuz closed",
    "Saudi Arabia ruled out oil export ban",
    "Riyadh has no plans to impose oil export ban",
    "Fed chair resigns story is rumoured",
    "Iran won't see strait of hormuz closed",
    "Iran won\u2019t see strait of hormuz closed",
    "Claim of strait of hormuz closed isn\u2019t true",
])
def test_denials_fall_through(headline):
    _assert_guarded(triage_article(_article(headline)), "denial")


@pytest.mark.parametrize("headline", [
    "Oil prices jump as strait of hormuz blocked",
    "Brent settles higher after strait of hormuz shut",
    "Gold 2% higher after Fed chair resigns",
    "Oil hits 6-month high as strait of hormuz closed",
    "Stocks tumbled after Fed chair resigns",
    "Crude futures up after strait of hormuz shut",
    "Gold 1.5 % lower after Fed chair fired",
    "Brent dropped after strait of hormuz shut",
    "Oil sank as strait of hormuz closed",
])
def test_price_reports_fall_through(headline):
    _assert_guarded(triage_article(_article(headline)), "price_report")


@pytest.mark.parametrize("headline", [
    "Analysts say OPEC+ agrees to cut soon",
    "Strait of Hormuz closed could send oil to $150",
    "Traders fear strait of hormuz shut",
    "Iran may see strait of hormuz closed",
    "Analyst warns strait of hormuz closed",
    "Strait of Hormuz closed might last weeks",
    "Tehran warns of strait of hormuz closed",
])
def test_commentary_falls_through(headline):
    _assert_guarded(triage_article(_article(headline)), "commentary")


@pytest.mark.parametrize("headline", [
    "OPEC+ agrees to cut output from May",
    "OPEC+ agrees to cut output in May 2026",
    "OPEC+ agrees to cut output starting May 1",
    "OPEC+ agrees to cut output since mid-May",
])
def test_may_the_month_is_not_commentary(headline):
    result = triage_article(_article(headline))
    assert result.rule_tier_hit is True
    assert result.guard_reason is None


@pytest.mark.parametrize("headline", [
    "Strait of Hormuz closed after Iranian strike",
    "OPEC+ agrees to cut output by 2 million barrels",
    "Fed chair resigns",
])
def test_genuine_events_stay_on_the_rule_tier(headline):
    result = triage_article(_article(headline))
    assert result.rule_tier_hit is True
    assert result.guard_reason is None


@pytest.mark.parametrize("headline", ["Notable day: Fed chair resigns", "Goldman says Fed chair resigns"])
def test_guard_words_inside_longer_words_do_not_fire(headline):
    # "not" in "Notable" and "gold" in "Goldman" are whole-word guards, so neither trips here.
    assert triage_article(_article(headline)).rule_tier_hit is True


@pytest.mark.parametrize("headline", ["OPEC+ agrees output cut", "Explosion hits Riyadh oil facility"])
def test_spec_event_headlines_still_reach_the_classifier(headline):
    result = triage_article(_article(headline))
    assert result.matched is True
    assert result.rule_tier_hit is False
    assert result.guard_reason is None


def test_guarded_hit_stays_matched_for_the_classifier():
    # "sovereign default" has no CATEGORY_SIGNAL_KEYWORDS entry: falling through to the keyword tier would lose it.
    result = triage_article(_article("Moody's says sovereign default could follow"))
    assert result.matched is True
    assert result.rule_tier_hit is False
    assert result.category == "sovereign_fiscal"
    assert result.matched_keywords == ["sovereign default"]
    assert result.guard_reason == "commentary"


def test_guards_read_the_title_not_the_summary():
    # A commentary-shaped summary does not guard a clean title.
    result = triage_article(_article("Strait of Hormuz closed after naval clash", summary="Analysts say it could last"))
    assert result.rule_tier_hit is True


def test_rule_guard_reason_returns_the_first_reason_in_order():
    # A title that is both a denial and a price report, on an unknown-link phrase, reads as a denial.
    assert triage_module.rule_guard_reason("Oil prices jump, Iran denies tanker attacked", ["tanker attacked"]) == "denial"
    assert triage_module.rule_guard_reason("Tanker attacked in the Gulf", ["tanker attacked"]) == "unknown_us_link"
    assert triage_module.rule_guard_reason("Markets steady", ["tanker attacked"]) == "summary_only"
    assert triage_module.rule_guard_reason("Fed chair fired", ["fed chair fired"]) is None
