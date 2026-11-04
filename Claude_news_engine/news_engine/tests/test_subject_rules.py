"""
Tests for data_layer/subject_rules.py -- pure functions, no network, no DB.

B6 (2026-10-22), audit AUD-P0-1 / AS-04: foreign central-bank headlines
(ECB, BoE, BoJ, RBA, ...) were scored as US-dollar news for FOMC and CPI
events, and off-subject titles (a gold-led headline that merely mentions
the dollar) voted on FOMC. These tests pin the rules in order:
foreign_cb (every event title) -> no_fed_coterm (FOMC family) ->
other_asset_lead (every event title, FIX 2026-11-03) -> off_subject (FOMC
and CPI families, title only) -> no_us_subject (every other family, FIX).
"""
import sys
import os
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import CPI_FAMILY_TITLES, EVENT_RELEVANCE_KEYWORDS_BY_TITLE, FOMC_FAMILY_TITLES
from data_layer.subject_rules import (
    b6_exclusion_reason,
    foreign_cb_match,
    keyword_pattern,
    leads_with_other_asset,
    names_us_marker,
    names_us_subject,
    news_low_trust,
    passes_subject_rule,
    title_family,
)

_MODULE_PATH = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "data_layer" / "subject_rules.py"

# Probe 1 headlines, copied literally from scripts/archive/audit_fa_probes.py's FOREIGN_CB_HEADLINES.
_PROBE1_FOMC = [
    ("ECB signals faster rate cuts as euro zone stalls", "Lagarde said the central bank is ready to ease further."),
    ("Bank of England delivers surprise rate cut", "The BoE cut rates by 50bp citing weak growth."),
    ("Bank of Japan hawkish, signals rate hike in December", "Ueda said the central bank could raise rates."),
    ("RBA holds, warns rate hike possible", "Australia's central bank kept rates on hold."),
]
# CPI-relevant variants of the same four central banks.
_PROBE1_CPI = [
    ("ECB's Schnabel says inflation risks mean rates must rise", ""),
    ("Bank of England's Pill warns inflation is sticky", ""),
    ("Bank of Japan's Ueda sees inflation near target", ""),
    ("RBA warns inflation still too high", ""),
]

# Real titles from the live backtest_log.db's top_contributions_json (audit AUD-P0-1).
_LIVE_OFFENDERS = [
    "Interest rates must rise further on inflation risks, ECB's Schnabel tells Bloomberg - Reuters",
    "BoE's Pill says a rate hike need not be start of long series - Reuters",
    "Bank of England's Breeden says cost-cutting by firms helping central bank - Reuters",
    "'Godzilla El Niño' is wreaking havoc with Philippine central bank's inflation forecasts",
    "China's slower loan growth is the new normal, central bank governor says - reuters.com",
    "Dollar languishes as inflation awaited; Euro edges up on Lagarde warning",
]


def test_family_sets_are_exact():
    assert FOMC_FAMILY_TITLES == {
        "FOMC Meeting Minutes", "FOMC Statement", "Federal Funds Rate",
        "FOMC Press Conference", "FOMC Economic Projections", "Fed Chairman Warsh Speaks",
    }
    assert CPI_FAMILY_TITLES == {"CPI m/m", "CPI y/y", "Core CPI m/m", "Core CPI y/y"}
    assert title_family("Core PCE Price Index m/m") == "other"
    assert title_family("PPI m/m") == "ppi"


@pytest.mark.parametrize(
    "event_title,title,summary",
    [("FOMC Statement", t, s) for t, s in _PROBE1_FOMC] + [("CPI m/m", t, s) for t, s in _PROBE1_CPI],
)
def test_probe1_foreign_cb_dropped(event_title, title, summary):
    assert b6_exclusion_reason(title, summary, event_title) == "foreign_cb"


@pytest.mark.parametrize(
    "event_title,title,summary",
    [
        ("FOMC Statement", "Fed signals faster rate cuts as US growth slows", "Federal Reserve officials see easing ahead"),
        ("FOMC Statement", "Warsh says inflation fight is not over", ""),
        ("CPI m/m", "US CPI rises 0.4% in September, hotter than forecast", ""),
        ("CPI m/m", "Fed's Waller says inflation still too high", ""),
    ],
)
def test_fed_headlines_kept(event_title, title, summary):
    assert b6_exclusion_reason(title, summary, event_title) is None


@pytest.mark.parametrize("event_title", ["FOMC Statement", "CPI m/m"])
@pytest.mark.parametrize("title", _LIVE_OFFENDERS)
def test_live_offender_titles_excluded(event_title, title):
    assert b6_exclusion_reason(title, "", event_title) == "foreign_cb"


def test_foreign_cb_ignores_us_lookalikes():
    for title in (
        "Bank of America CEO sees at least 10% drop in Q3 investment banking fees",
        "Federal Reserve Bank of New York survey shows inflation expectations rise",
        "New York Fed's Williams says policy is well positioned",
        "Novo's weight-loss pill sales jump",
    ):
        assert foreign_cb_match(title) is None, title
    assert foreign_cb_match("Reserve Bank of India holds rates") is not None


def test_generic_fomc_term_needs_fed_coterm():
    assert b6_exclusion_reason(
        "Gold retains key reserve status despite surging bond yields, central bankers say", "", "FOMC Statement"
    ) == "no_fed_coterm"
    # The co-term is found in the summary, so the article reaches the title rule (and fails it there).
    assert b6_exclusion_reason(
        "Rate cut bets rise", "Traders price a Federal Reserve cut in December", "FOMC Statement"
    ) == "off_subject"


def test_gold_led_dollar_title_not_scored_for_fomc():
    title = "Gold edges up as October rate hike bets ease, stronger dollar cap gains"
    assert b6_exclusion_reason(title, "Traders trimmed bets on a Federal Reserve hike", "FOMC Meeting Minutes") == "other_asset_lead"
    assert b6_exclusion_reason(title, "", "FOMC Meeting Minutes") == "no_fed_coterm"


def test_subject_rule_accepts_us_subjects():
    fomc_ok = [
        "Dollar firms as Fed officials push back on cuts",
        "Treasury yields climb after hot jobs data",
        "US 10-year yields hit two-month high",
        "Greenback slips ahead of Warsh testimony",
    ]
    cpi_only_ok = [
        "U.S. consumer prices rise 0.4% in September",
        "American inflation expectations climb",
        "Inflation data due Wednesday, CPI expected to ease",
        "BLS delays September report",
    ]
    for title in fomc_ok:
        assert passes_subject_rule(title, "fomc"), title
        assert passes_subject_rule(title, "cpi"), title
    for title in cpi_only_ok:
        assert passes_subject_rule(title, "cpi"), title


def test_subject_rule_rejects_off_subject():
    for title in ("Americans' incomes rose and poverty fell, Census Bureau says", "AI chip stocks slump"):
        assert not passes_subject_rule(title, "fomc"), title
    for title in ("Inflation worries weigh on us all", "Japan CPI rises 2.9%", "Euro zone inflation eases to 2.1%"):
        assert not passes_subject_rule(title, "cpi"), title


def test_bare_cpi_rejects_foreign_currency_and_city_leads():
    # Live title from scoring/backtest_log.db, plus nickname variants: since FIX the lead rule takes them first.
    for title in (
        "Aussie dollar eyes longest weekly winning streak since 2021 on hot CPI",
        "Loonie firms as CPI beats",
        "Yen slips after CPI miss",
        "Sterling jumps on CPI surprise",
        "Rupee steady ahead of CPI data",
    ):
        assert b6_exclusion_reason(title, "", "CPI m/m") == "other_asset_lead", title
    assert b6_exclusion_reason("Tokyo CPI accelerates in October", "", "CPI m/m") == "off_subject"
    # FIX: a US marker no longer rescues a currency-led title; a dollar-led title with a currency later stays.
    assert b6_exclusion_reason("Yen slides as US CPI runs hot", "", "CPI m/m") == "other_asset_lead"
    assert b6_exclusion_reason("Dollar firms vs yen after CPI beat", "", "CPI m/m") is None
    assert b6_exclusion_reason("CPI preview: core seen at 0.3%", "", "CPI m/m") is None


def test_currency_nicknames_do_not_change_foreign_cb():
    # The CPI guard markers are not foreign places for the central-bank rule.
    assert foreign_cb_match("Yen traders eye central bank minutes") is None
    assert b6_exclusion_reason("Yen traders eye central bank minutes", "", "Retail Sales m/m") == "other_asset_lead"


def test_us_marker_is_case_sensitive():
    assert names_us_marker("tells us nothing") is False
    for text in ("US", "U.S.", "USA", "American"):
        assert names_us_marker(text) is True, text
    assert names_us_marker("USD rallies") is False


def test_foreign_dollar_is_not_the_dollar():
    assert not passes_subject_rule("Canadian dollar firms after inflation data", "cpi")
    assert not passes_subject_rule("Australian dollar jumps as rate hike bets build", "fomc")


def test_other_titles_skip_the_tuned_title_rule():
    assert b6_exclusion_reason("US payrolls jump 250,000; rate cut bets fade", "", "Non-Farm Employment Change") is None
    assert b6_exclusion_reason("BoE's Bailey says UK hiring slows", "", "Non-Farm Employment Change") == "foreign_cb"
    assert passes_subject_rule("AI chip stocks slump", "jobs") is True


def test_summary_foreign_cb_only_without_us_title():
    assert b6_exclusion_reason("Markets steady", "The ECB held rates", "Retail Sales m/m") == "foreign_cb"
    assert b6_exclusion_reason("US retail sales jump 0.6%", "Elsewhere the ECB held rates", "Retail Sales m/m") is None


def test_source_has_no_backspace_bytes():
    assert b"\x08" not in _MODULE_PATH.read_bytes()


def test_audit_probe1_now_drops_all():
    from scripts.archive.audit_fa_probes import probe_foreign_cb_sign
    lines = probe_foreign_cb_sign()
    assert len(lines) == 4
    for line in lines:
        assert line.startswith("DROP"), line


# --- FIX (2026-11-03), audit B3 / B4 / B1 stopgap: US-subject rule for every family, other-asset lead on every path. ---

def test_us_subject_real_cases():
    westpac = "Westpac's latest job cuts not AI-driven, spokesperson says - Reuters"
    assert b6_exclusion_reason(westpac, "", "Unemployment Claims") == "no_us_subject"
    assert b6_exclusion_reason("Venezuela oilfield hiring picks up", "", "Unemployment Claims") == "no_us_subject"
    assert b6_exclusion_reason("US jobless claims fall to 194,000", "", "Unemployment Claims") is None
    philippine = "'Godzilla El Ni\u00f1o' is wreaking havoc with Philippine central bank's inflation forecasts"
    assert b6_exclusion_reason(philippine, "", "PPI m/m") == "foreign_cb"


def test_soft_marker_needs_no_foreign_place():
    assert b6_exclusion_reason("Canada jobless claims rise", "", "Unemployment Claims") == "no_us_subject"
    assert b6_exclusion_reason("Jobless claims rise to 230,000", "", "Unemployment Claims") is None
    assert b6_exclusion_reason("UK consumer confidence falls", "", "Prelim UoM Consumer Sentiment") == "no_us_subject"
    assert b6_exclusion_reason("University of Michigan sentiment slips", "", "Prelim UoM Consumer Sentiment") is None
    assert b6_exclusion_reason("PCE inflation eases", "", "Core PCE Price Index m/m") is None


@pytest.mark.parametrize(
    "title",
    [
        "Gold edges up as rate hike bets ease",
        "Pound edges up as dollar softens",
        "Gold miners rally as Fed signals rate cut",
        "U.S. crude falls below $80 as oil prices sink",
        "Wall Street ends higher as tech rebounds",
        "Indian rupee weakens as dollar strengthens after hot CPI",
        "British pound falls as dollar rises",
        "Swiss franc gains as dollar softens",
        "Mexican peso slips as dollar firms on Fed bets",
        "Australian dollar slides as US CPI runs hot",
        "Canadian dollar firms as US jobs data disappoints",
        "New Zealand dollar slips as Fed holds",
        "Bullion climbs as Fed signals rate cut",
        "Emerging market stocks fall after US CPI",
        "SNAPSHOT US stock futures edge lower after economic data - Reuters",
        "Colombian peso slips as dollar firms on Fed bets",
        "Argentine peso slips as dollar firms on Fed bets",
        "Chilean peso slips as dollar firms on Fed bets",
        "Philippine peso slips as dollar firms on Fed bets",
        "Mexico's peso slips as dollar firms on Fed bets",
        "Mexico’s peso slips as dollar firms on Fed bets",
        "Pakistani rupee weakens as dollar strengthens after hot CPI",
        "Sri Lankan rupee weakens as dollar strengthens after hot CPI",
        "India's rupee weakens as dollar strengthens after hot CPI",
        "Egyptian pound falls as dollar rises",
        "Thai baht weakens as dollar firms after US CPI",
        "Korean stocks fall after US CPI",
        "German stocks fall after US CPI",
        "French stocks fall after US CPI",
        "Japan stocks fall after US CPI",
        "China stocks fall after US CPI",
        "Hong Kong stocks fall after US CPI",
        "Saudi stocks fall after US CPI",
        "South Korea stocks fall after US CPI",
        "Indonesian rupiah slides as dollar firms after US CPI",
        "Malaysian ringgit slides as dollar firms after US CPI",
        "Russian rouble slides as dollar firms after US CPI",
        "Russian ruble slides as dollar firms after US CPI",
        "Polish zloty slides as dollar firms after US CPI",
        "Hungarian forint slides as dollar firms after US CPI",
        "Swedish krona slides as dollar firms after US CPI",
        "Norwegian krone slides as dollar firms after US CPI",
        "Czech crown slides as dollar firms after US CPI",
        "Israeli shekel slides as dollar firms after US CPI",
        "Nigerian naira slides as dollar firms after US CPI",
        "South Africa's rand slides after US CPI",
        "S.Africa's rand slides after US CPI",
        "Brazil's real slides as dollar firms on Fed bets",
        "Brazil\u2019s real slides as dollar firms on Fed bets",
        "South Korea's won falls after US CPI",
        "Korea's won falls after US CPI",
        "S.Korea's won falls after US CPI",
        "Sweden's crown falls after Fed",
        "Norway's crown falls after Fed",
        "Denmark's crown falls after Fed",
        "Czech Republic's crown falls after Fed",
        "Iceland's crown falls after Fed",
        "Iran's oil exports fall as dollar firms after US CPI",
        "Pakistan's rupee falls after US CPI",
        "Tokyo stocks close lower on U.S. inflation",
        "Seoul shares open lower on U.S. inflation",
        "Sydney shares slide after US CPI",
        "Paris stocks fall after US CPI",
        "Frankfurt stocks fall after US CPI",
        "Beijing stocks fall after US CPI",
        "Mumbai stocks fall after US CPI",
        "Shanghai stocks fall after US CPI",
        "Moscow stocks fall after US CPI",
        "Sao Paulo stocks fall after US CPI",
        "Gulf stocks fall as dollar firms after US CPI",
        "Most Gulf shares close lower after US CPI",
        "Most Gulf stocks in red after US CPI",
        "Mideast stocks fall after US CPI",
        "Nordic stocks fall after US CPI",
        "World stocks fall after hot US CPI",
        "Asia-Pacific stocks fall after US CPI",
        "Asia Pacific stocks fall after US CPI",
        "Offshore yuan slips after US CPI",
        "Onshore yuan slips after US CPI",
        "Turkiye's lira slides after US CPI",
        "New Delhi stocks fall after US CPI",
        "Sudan's oil output falls after US CPI",
    ],
)
def test_other_asset_lead_on_every_path(title):
    assert b6_exclusion_reason(title, "", "CPI m/m") == "other_asset_lead"
    assert b6_exclusion_reason(title, "", "PPI m/m") == "other_asset_lead"
    assert b6_exclusion_reason(title, "", "Unemployment Claims") == "other_asset_lead"
    assert b6_exclusion_reason(title, "Fed officials meet next week", "FOMC Statement") == "other_asset_lead"
    # The empty-summary case stops one rule earlier unless the title names the Fed; either way it is out.
    assert b6_exclusion_reason(title, "", "FOMC Statement") in ("no_fed_coterm", "other_asset_lead")


@pytest.mark.parametrize(
    "title",
    [
        "Spot gold slips", "US stocks fall", "U.S. stocks fall", "Asian shares rise", "European equities drop",
        "Global stocks slide", "Japanese yen weakens", "Chinese yuan firms", "London copper rises",
        "Silver climbs", "Platinum drops", "Brent settles lower", "WTI gains", "Natural gas surges", "Natgas slides",
        "Bitcoin jumps", "Crypto rally fades", "Cryptocurrencies slump", "Wall St opens lower", "S&P 500 record",
        "S&P slips", "Nasdaq jumps", "Dow drops", "Nikkei jumps", "FTSE 100 falls", "DAX rises", "Sterling slips",
        "Euro firms", "Yuan steadies", "Aussie gains", "Loonie weakens", "Kiwi rises", "Franc firms", "Rupee falls",
        "Peso slides", "Lira hits low", "Asia FX weak", "Asian currencies fall", "\u2018Gold rush\u2019 continues",
        "British pound falls", "Indian shares slip", "Mexican peso slips", "Swiss franc gains", "Turkish lira slides",
        "Australian shares rise", "Canadian stocks fall", "New Zealand dollar slips", "Hong Kong dollar steadies",
        "Aussie dollar eyes CPI", "South Korean won weakens", "Korean won falls", "Brazilian real slides",
        "South African rand firms", "Bullion climbs", "Emerging market stocks fall", "Emerging-market shares drop",
        "Emerging markets FX slides", "Emerging market currencies slide", "SNAPSHOT-US stock futures edge lower",
    ],
)
def test_lead_pattern_covers_each_asset(title):
    assert leads_with_other_asset(title) is True


@pytest.mark.parametrize(
    "title",
    [
        "Dollar rises after hot CPI", "Treasury yields climb", "US CPI rises", "Golden Week trade slows",
        "Oilfield hiring picks up", "Downtown retail sales slip", "Shareholders revolt", "Europe stumbles",
        "Fed lifts gold outlook", "Dollar firms vs yen after CPI beat", "Real wages fall as CPI runs hot",
        "Rand Paul criticises Fed", "Won't cut, Fed says", "Canadian jobs data disappoints", "Snapshot of US inflation",
        "Fed's real rate rises", "Fed’s real rate rises", "Real wages rise as inflation cools", "Dollar vs peso",
        "Fed's gold holdings unchanged", "America's stocks rally on CPI", "Treasury's oil reserve sale lifts dollar",
        "US Treasury's gold audit", "Federal Reserve's gold holdings", "Trump's oil tariff lifts dollar",
        "Powell's oil remarks lift dollar", "White House's oil plan lifts dollar", "Fed watch gold outlook",
        "Dollar Mexican peso pair slips", "Saudi crown prince says oil output steady", "Crown Prince resigns",
        "Swedish crown princess visits", "Fed's won't cut", "Korean jobs data disappoints",
        # A possessive qualifies only for a foreign place, so no US office, state or company does.
        "Trump administration's oil plan lifts US inflation fears", "Energy Department's oil reserve release to cool US CPI",
        "Supreme Court's oil ruling lifts dollar", "SEC's crypto rule lifts dollar", "Pentagon's oil purchase lifts dollar",
        "Vance's oil remarks lift dollar", "Lutnick's gold tariff lifts dollar", "Nation's oil output rises as US CPI cools",
        "Country's oil output rises as US CPI cools", "Texas's oil output rises as US inflation cools",
        "President's oil plan lifts dollar", "Secretary's oil remarks lift dollar", "Alaska's oil output rises as US CPI cools",
        "New Mexico's oil output rises as US CPI cools", "New England's oil demand rises as US CPI cools",
        "Georgia's oil refinery lifts US inflation", "Goldman's gold call lifts dollar", "Morgan's gold forecast lifts dollar",
        # Words the demonym shape fits that are no nationality; "shares" is often the verb.
        "Kashkari shares rate view after CPI", "Logan shares inflation concerns", "Miran shares dovish view on rates",
        "Governor Bowman shares rate view", "President Logan shares rate view", "Altman shares AI plan after Fed",
        "Republican oil bill lifts dollar", "Michigan shares fall as Fed holds", "Trump plan oil tariff lifts dollar",
        "Biden plan oil tariff lifts dollar", "Senate plan oil tariff lifts dollar", "Congress plan oil tariff lifts dollar",
        "Energy plan oil tariff lifts dollar", "These stocks could soar after US CPI", "Which stocks could rally after US CPI",
        "Why these stocks could rally after CPI", "Can gold rally as US CPI cools?", "Bullish oil bets lift dollar",
        "Bearish gold bets lift dollar", "Ban oil exports, Trump says", "Goldman gold forecast lifts dollar",
        "JPMorgan oil call lifts dollar", "Citi gold call lifts dollar", "CPI gold rally fades",
        "Tech stocks plunge as Fed rate hike fears, AI funding worries mount", "AI stocks plunge after hot US CPI",
        # The explicit won, real, rand and crown forms stop at the English word.
        "Brazil's real estate boom lifts dollar", "Brazilian real estate slump lifts dollar", "South Korea's won't cut",
        "Sweden's crown princess visits US", "Norway's crown prince visits Fed", "Denmark's crown jewels on show",
        # A place word with no asset straight after it.
        "Gulf of Mexico output slips", "Gulf Coast refiners lift dollar", "World Bank warns on US inflation",
        # The country's own adjective and hyphenated English words.
        "American oil output lifts dollar", "American shares rise after US CPI", "Texan oil output lifts US CPI",
        "Kaplan shares rate view after CPI", "Sluggish oil demand lifts dollar",
        "Brazil's real-estate boom lifts dollar", "Sweden's crown-prince visits US",
    ],
)
def test_lead_pattern_leaves_other_leads(title):
    assert leads_with_other_asset(title) is False


@pytest.mark.parametrize(
    ("keyword", "listed_for", "headline"),
    [
        ("fed chairman", "FOMC Statement", "Fed chairman signals patience"),
        ("central bankers", "FOMC Statement", "Central bankers gather at Jackson Hole"),
        ("inflationary", "CPI m/m", "Inflationary pressure builds"),
        ("recessionary", "Advance GDP q/q", "Recessionary signals grow"),
    ],
)
def test_longer_keyword_forms_match_on_their_own(keyword, listed_for, headline):
    # Whole-word matching stops "fed chair" reaching "fed chairman", so each longer form is listed itself.
    keywords = EVENT_RELEVANCE_KEYWORDS_BY_TITLE[listed_for]
    assert keyword in keywords
    assert keyword_pattern(tuple(keywords)).search(headline.lower())
    assert keyword_pattern(tuple(k for k in keywords if k != keyword)).search(headline.lower()) is None


@pytest.mark.parametrize(
    "title",
    [
        "Trump administration's oil plan lifts US inflation fears", "Energy Department's oil reserve release to cool US CPI",
        "Nation's oil output rises as US CPI cools", "Texas's oil output rises as US inflation cools",
        "Kashkari shares rate view after CPI",
    ],
)
def test_us_titles_the_lead_rule_leaves_alone_are_kept_on_cpi(title):
    assert b6_exclusion_reason(title, "", "CPI m/m") is None


def test_dollar_headline_kept_in_every_family():
    assert b6_exclusion_reason("Dollar rises after hot CPI", "", "CPI m/m") is None
    assert b6_exclusion_reason("Dollar rises after hot PPI", "", "PPI m/m") is None
    assert b6_exclusion_reason("Greenback rises after hot PPI", "", "PPI m/m") is None
    assert b6_exclusion_reason("Aussie dollar rises on hot CPI", "", "CPI m/m") is not None
    # A leading foreign dollar is another asset; later in the title it is still not the dollar for the soft marker.
    assert b6_exclusion_reason("Canadian dollar firms on hot PPI", "", "PPI m/m") == "other_asset_lead"
    assert b6_exclusion_reason("Hot PPI lifts Canadian dollar", "", "PPI m/m") == "no_us_subject"


def test_wall_street_marker_only_when_not_leading():
    assert b6_exclusion_reason("Jobs report lifts Wall Street", "", "Non-Farm Employment Change") is None
    assert b6_exclusion_reason("Wall Street cheers jobs report", "", "Non-Farm Employment Change") == "other_asset_lead"


def test_own_asset_title_keeps_its_headlines():
    assert b6_exclusion_reason("Oil jumps as EIA reports crude draw", "", "Crude Oil Inventories") is None
    assert b6_exclusion_reason("Oil jumps as EIA reports crude draw", "", "CPI m/m") == "other_asset_lead"
    assert b6_exclusion_reason("Natural gas prices fall after storage build", "", "Natural Gas Storage") is None
    # The exemption is per asset: a gold headline is still another asset for the crude title,
    # and a foreign central bank still goes first.
    assert b6_exclusion_reason("Gold rises as dollar slips", "", "Crude Oil Inventories") == "other_asset_lead"
    assert b6_exclusion_reason("ECB warns on oil prices", "", "Crude Oil Inventories") == "foreign_cb"


@pytest.mark.parametrize(
    "title",
    [
        "U.S. factory orders rise", "US data due", "USA jobs plan", "America adds jobs", "American shoppers pull back",
        "United States hiring slows", "Fed sees slower hiring", "FOMC minutes due", "Warsh speaks on jobs",
        "BLS delays report", "Bureau of Labor Statistics delays report", "Labor Department says layoffs rose",
        "Labor Dept says layoffs rose", "Commerce Department revises figures", "BEA revises figures",
        "Bureau of Economic Analysis revises figures", "Census Bureau delays data",
        "Hiring slows, Wall Street fears",
    ],
)
def test_hard_markers_pass_even_with_a_foreign_name(title):
    assert names_us_subject(title) is True
    assert names_us_subject(f"{title} as Canada watches") is True


@pytest.mark.parametrize(
    "title",
    [
        "Treasury sells bills", "Treasuries slip", "Census shows growth", "Dollar slips", "Greenback slips",
        "Payrolls jump", "Non-farm payrolls jump", "Nonfarm payrolls jump", "Jobless claims fall", "Initial claims fall",
        "Unemployment claims fall", "ADP report beats", "JOLTS openings fall", "PCE cools",
        "Personal consumption expenditures cool", "ISM slips", "Institute for Supply Management survey slips",
        "University of Michigan survey slips", "UMich survey slips", "UoM survey slips",
    ],
)
def test_soft_markers_pass_until_a_foreign_place_is_named(title):
    assert names_us_subject(title) is True
    assert names_us_subject(f"{title} in Canada") is False


def test_us_subject_ignores_lookalikes():
    for title in (
        "Earthquake jolts Japanese coast",     # lower-case "jolts" is a verb, not the JOLTS survey
        "Inflation Jolts Markets",
        "Layoffs tell us nothing new",         # the pronoun
        "Bea Arthur tribute sale lifts store sales",
        "Optimism grows on hiring",
        "Australian dollar firms",
    ):
        assert names_us_subject(title) is False, title


def test_curly_apostrophe_reaches_the_new_rules():
    assert b6_exclusion_reason("Westpac\u2019s job cuts widen", "", "Unemployment Claims") == "no_us_subject"
    assert b6_exclusion_reason("America\u2019s job cuts widen", "", "Unemployment Claims") is None


def test_news_low_trust_is_fomc_and_cpi_only():
    assert news_low_trust("FOMC Statement") is True
    assert news_low_trust("Core CPI m/m") is True
    assert news_low_trust("PPI m/m") is False
    assert news_low_trust("Core PCE Price Index m/m") is False


def test_keyword_pattern_edges():
    pattern = keyword_pattern(("rate", "rate hike", "m/m", "u.s."))
    assert pattern is keyword_pattern(("rate", "rate hike", "m/m", "u.s."))   # lru_cache
    assert pattern.search("a rate hike's cost").group(0) == "rate hike's"     # longest alternative first
    assert pattern.search("the u.s. data") is not None
    assert pattern.search("corporate news") is None
    assert pattern.search("rate2 table") is None
    assert keyword_pattern(()).search("anything at all") is None              # an empty list matches nothing
