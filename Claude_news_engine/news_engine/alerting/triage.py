"""Pure, no-I/O rule-based first pass over each fetched article."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from data_layer.news_feed import NewsArticle
from alerting.taxonomy import CATEGORY_SIGNAL_KEYWORDS, HARD_RULE_PATTERNS, NEAR_MISS_LOG_THRESHOLD
from alerting.us_link import rule_country_us_link
from config.settings import EARTHQUAKE_MIN_MAGNITUDE

# Why a hard-rule hit may not fire on its own (FIX C1), in checking order.
GUARD_REASONS: tuple[str, ...] = ("summary_only", "denial", "price_report", "commentary", "unknown_us_link")


@dataclass
class TriageResult:
    matched: bool
    category: Optional[str]
    rule_tier_hit: bool
    matched_keywords: list[str]
    near_miss_score: Optional[float]
    near_miss_category: Optional[str] = None
    guard_reason: Optional[str] = None  # GUARD_REASONS entry on a hard-rule hit sent to the classifier


def _searchable_text(article: NewsArticle) -> str:
    return f"{article.title} {article.summary}".lower()


def _partial_match_score(text: str) -> tuple[Optional[str], float]:
    """
    For every phrase across all of CATEGORY_SIGNAL_KEYWORDS's keyword
    lists, splits the phrase into words and computes what fraction of
    those words appear anywhere in `text`. Returns the category and
    fraction for the single highest-scoring phrase found -- a real
    partial-match signal for the shock_near_misses audit log (previously
    hardcoded to 0.0, so nothing could ever clear NEAR_MISS_LOG_THRESHOLD
    and the log never got a row).
    """
    best_category: Optional[str] = None
    best_score = 0.0
    for category, keywords in CATEGORY_SIGNAL_KEYWORDS.items():
        for phrase in keywords:
            words = phrase.split()
            if not words:
                continue
            hits = sum(1 for w in words if w in text)
            score = hits / len(words)
            if score > best_score:
                best_score = score
                best_category = category
    return best_category, best_score


_MAGNITUDE_PATTERNS = (
    re.compile(r"magnitude[\s-]*(\d+(?:\.\d+)?)"),
    re.compile(r"(\d+(?:\.\d+)?)[\s-]*magnitude"),
    re.compile(r"\bm\s?(\d+(?:\.\d+)?)\b"),
)


def _stated_magnitude(text: str) -> Optional[float]:
    for pattern in _MAGNITUDE_PATTERNS:
        match = pattern.search(text)
        if match:
            return float(match.group(1))
    return None


def _is_minor_earthquake_only(text: str, category: Optional[str], hits: list[str]) -> bool:
    """
    True when the ONLY reason an article matched is the word "earthquake" and it states a
    magnitude under EARTHQUAKE_MIN_MAGNITUDE. No stated magnitude -> never filtered.
    """
    if category != "natural_disaster_supply_chain" or hits != ["earthquake"]:
        return False
    magnitude = _stated_magnitude(text)
    return magnitude is not None and magnitude < EARTHQUAKE_MIN_MAGNITUDE


# "not" also covers has not / have not / will not.
_DENIAL_RE = re.compile(
    r"\b(?:den(?:y|ies|ied|ying)|rul(?:e|es|ed|ing) out|no plans? to|not|false reports?|unconfirmed|rumou?r(?:s|ed)?)\b"
    r"|\b\w+n't\b"
)

_PRICED_ASSET = r"\b(?:prices?|oil|crude|brent|wti|gold|stocks?|shares)\b"
# Wider, for the record/highest branch only: "record high" also describes tensions and ratings, so that branch
# needs something with a price beside it, and a dollar, a yield or an index has one as much as oil does.
_PRICED_SUBJECT = (
    r"\b(?:prices?|oil|crude|brent|wti|gold|silver|copper|platinum|palladium|bullion|stocks?|shares|equities"
    r"|dollar|greenback|yields?|bonds?|treasur(?:y|ies)|bitcoin|crypto\w*|ether|euro|yen|yuan|sterling|pound"
    r"|franc|rupee|peso|lira|wall st(?:reet)?|s&p(?: 500)?|nasdaq|dow|nikkei|ftse|dax|ind(?:ex|exes|ices)|markets?)\b"
)
# Reporting words allowed between an asset and a tight move word ("Oil edges up", "Stocks end sharply lower",
# "Gold is 2% down"). A closed list on purpose: any other word there is usually a noun, and then the sentence
# is about that noun ("Oil exports shut down", "Oil tanker attack lifts premiums higher").
_ASSET_TO_MOVE = (
    r"(?:\s+(?:prices?|markets?))?"
    r"(?:\s+(?:edg(?:e|es|ed|ing)|inch(?:es|ed|ing)?|tick(?:s|ed|ing)?|drift(?:s|ed|ing)?|trad(?:e|es|ed|ing)"
    r"|end(?:s|ed|ing)?|clos(?:e|es|ed|ing)|finish(?:es|ed|ing)?|open(?:s|ed|ing)?|turn(?:s|ed|ing)?"
    r"|head(?:s|ed|ing)?|mov(?:e|es|ed|ing)|push(?:es|ed|ing)?|stay(?:s|ed|ing)?|hold(?:s|ing)?|held"
    r"|hover(?:s|ed|ing)?|sit(?:s|ting)?|get(?:s|ting)?|set|post(?:s|ed|ing)?|remain(?:s|ed|ing)?"
    r"|is|are|was|were|ha[sd]"
    r"|sharply|slightly|briefly|mostly|largely|broadly|modestly|marginally|again|back|now|still"
    r"|\d+(?:\.\d+)?\s*%)){0,2}"
    r"\s+"
)
_LONG_RANGE = (
    r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|multi)"
    r"[- ](?:session|day|week|month|year|decade)"
)
_EXTREME = r"(?:record|all[- ]time|highest|lowest|" + _LONG_RANGE + r")"

# Verbs that read as a price move anywhere in a 30-character window after the asset, as they always did.
_WINDOW_MOVE = (
    r"(?:rises?|rose|rising|falls?|fell|falling|jump(?:s|ed|ing)?|slides?|slid|sliding|climb(?:s|ed|ing)?"
    r"|drop(?:s|ped|ping)?|dip(?:s|ped|ping)?|sinks?|sank|sinking|surg(?:e|es|ed|ing)|tumbl(?:e|es|ed|ing)"
    r"|gain(?:s|ed|ing)?|soar(?:s|ed|ing)?|spik(?:e|es|ed|ing)|rall(?:y|ies|ied|ying))"
)
# Words that also turn up in event headlines ("up", "down", "lower", "top", "pare"), so they count only right
# after the asset, or after _ASSET_TO_MOVE. "firm" alone is the noun in "Oil firms evacuate staff", so it needs
# what follows a verb. Bare "tanks" and "shed" are left out for the same reason ("Oil tanks ablaze").
_TIGHT_MOVE = (
    r"(?:up|down|higher|lower|mixed|flat|unchanged|(?:little|barely|largely|mostly)\s+changed"
    r"|steady|steadie[sd]|stable|stabili[sz](?:e|es|ed|ing)|top(?:s|ped|ping)|advanc(?:e|es|ed|ing)"
    r"|par(?:e|es|ed|ing)|plung(?:e|es|ed|ing)|slump(?:s|ed|ing)?|slip(?:s|ped|ping)?|rebound(?:s|ed|ing)?"
    r"|retreat(?:s|ed|ing)?|eas(?:e|es|ed|ing)|extend(?:s|ed|ing)?|trim(?:s|med|ming)?|recover(?:s|ed|ing)?"
    r"|firm(?:ed|ing|er)|firms?(?=\s+(?:as|on|after|amid|ahead|despite|while|near|above|below|at|up)\b|\s*[,;:-]|\s*$)"
    r"|weak(?:er|en(?:s|ed|ing)?)?|stronger|strengthen(?:s|ed|ing)?|soft(?:er|en(?:s|ed|ing)?)"
    r"|seesaw(?:s|ed|ing)?|div(?:e|es|ed|ing)|crash(?:es|ed|ing)?|bounc(?:e|es|ed|ing)"
    r"|sell(?:s|ing)?[- ]?off|sold[- ]off|pull(?:s|ed|ing)?\s+back|pop(?:s|ped|ping)?|declin(?:e|es|ed|ing)"
    r"|revers(?:e|es|ed|ing)|skid(?:s|ded|ding)?|sag(?:s|ged|ging)?|swing(?:s|ing)?|swung|sheds|shedding"
    r"|los(?:es|ing)|falter(?:s|ed|ing)?|wobbl(?:e|es|ed|ing)|hammered|rattled|rocked|crushed"
    r"|increas(?:e|es|ed|ing)|decreas(?:e|es|ed|ing)|tak(?:es|ing)\s+off|(?:break(?:s|ing)?|broke)\s+(?:higher|lower)"
    r"|(?:remain(?:s|ed|ing)?|stay(?:s|ed|ing)?)\s+(?:high|low|elevated)"
    r"|under\s+pressure|in\s+(?:the\s+)?(?:red|green))"
)
# A level word plus a dollar figure ("Brent crude near $112", "Oil past $120", "Brent breaks the $100 mark").
# A figure in billions is a sum of money, not a price: "Stocks of oil under $5 billion ransom" stays out.
_DOLLAR_LEVEL = (
    r"(?:above|below|over|under|top|near(?:s|ing)?|around|at|past|beyond|through"
    r"|touch(?:es|ed|ing)?|reach(?:es|ed|ing)?|breach(?:es|ed|ing)?|cross(?:es|ed|ing)?|break(?:s|ing)?|broke"
    r"|pass(?:es|ed|ing)?|surpass(?:es|ed|ing)?|exceed(?:s|ed|ing)?|test(?:s|ed|ing)?)"
    r"\s+(?:(?:the|about|around|nearly|almost|roughly)\s+)*"
    r"\$(?![\d,.]+\s*(?:billion|million|trillion|bn|mn)\b)\d"
)
# "Indian shares on track for muted open", "Oil set for weekly gain", "Intel stock heads for worst day".
_OUTLOOK = (
    r"(?:(?:set|poised|on\s+track|on\s+course|head(?:s|ed|ing)?|bound)\s+(?:to|for)\s+(?:[a-z0-9-]+\s+){0,3}?"
    r"(?:gains?|loss(?:es)?|drops?|rises?|falls?|declines?|opens?|closes?|rebounds?|jumps?|slides?|rall(?:y|ies))"
    r"|(?:for\s+)?(?:(?:its|their)\s+)?(?:worst|best)\s+(?:session|day|week|month|quarter|year))\b"
)
# The level a priced subject arrives at. "level", "peak" and "highest since" read as a price only with that
# subject and, for "records", a verb of arrival right before them: "highest level" also means an alert or a
# rank ("US raises alert to highest level"), and "Tensions at record high" has no price in it at all.
_ARRIVAL = (
    r"(?:hit(?:s|ting)?|at|near(?:s|ing)?|to|from|off|reach(?:es|ed|ing)?|touch(?:es|ed|ing)?"
    r"|set(?:s|ting)?|notch(?:es|ed|ing)?|scal(?:e|es|ed|ing)|test(?:s|ed|ing)?|mark(?:s|ed|ing)?"
    r"|ma(?:de|kes?|king)|s(?:aw|ees?|eeing))\s+"
)
_LEVEL_FILLER = r"(?:(?:its|their|a|an|the|new|fresh|another|near|nearly)\s+)*"
_LEVEL = (
    r"(?:" + _EXTREME + r"[- ](?:highs?|lows?|peaks?)"
    r"|" + _EXTREME + r"\s+(?:levels?|close|closing|prices?)"
    r"|(?:highest|lowest)\s+(?:since|in)"
    r"|(?:session|intraday|intra-day|fresh|new|day|week|month|year|decade|weekly|monthly|yearly|annual)"
    r"[- ](?:highs?|lows?|peaks?))\b"
)
_SUBJECT_AT_LEVEL = (
    _PRICED_SUBJECT + r"(?:'s)?" + _ASSET_TO_MOVE
    + r"(?:(?:" + _WINDOW_MOVE + r"|" + _TIGHT_MOVE + r")\s+)?"
    + r"(?:(?:" + _ARRIVAL + r")?" + _LEVEL_FILLER + _LEVEL + r"|" + _ARRIVAL + _LEVEL_FILLER + r"records?\b)"
)

# Bare "6-month high" reads as a price with no named asset. "top" and "pare" also take the plural-subject form
# ("Oil prices top $100", "Stocks pare losses"); bare "top" needs the dollar figure, since "Oil tanker seized,
# top general says" is an event.
_PRICE_REPORT_RE = re.compile(
    _PRICED_ASSET + r".{0,30}?\b" + _WINDOW_MOVE + r"\b"
    r"|" + _PRICED_ASSET + _ASSET_TO_MOVE + r"(?:" + _TIGHT_MOVE + r"\b|" + _DOLLAR_LEVEL + r"|" + _OUTLOOK + r")"
    r"|\bfutures\b"
    r"|\bsettle[sd]?\b"
    r"|\d+(?:\.\d+)?\s*%\s+(?:higher|lower)\b"
    r"|\b" + _LONG_RANGE + r"[- ](?:high|low)s?\b"
    r"|" + _SUBJECT_AT_LEVEL +
    r"|\b(?:record[- ]|all[- ]time[- ])(?:highs?|lows?)\s+(?:(?:for|in|on)\s+(?:the\s+)?)?" + _PRICED_SUBJECT +
    r"|\bhit(?:s|ting)? \$\d"
)

# "may" the month is stripped first, so only the modal reads as speculation.
_MONTH_MAY_RE = re.compile(r"\b(?:in|by|of|on|since|from|until|early|late|mid|next|last|this)[\s-]+may\b|\bmay\s+(?=\d)")

_COMMENTARY_RE = re.compile(
    r"\banalysts?\s+(?:says?|said|warn(?:s|ed)?|sees?|saw|expect(?:s|ed)?)\b"
    r"|\b(?:could|might|may|would|if)\b"
    r"|\bwarn(?:s|ed)?\s+(?:that|of)\b"
    r"|\bfear(?:s|ed)?\b"
)


def _guard_text(title: str) -> str:
    return title.lower().replace("\u2019", "'").replace("\u2018", "'")


def _title_hits(title: str, hits: list[str]) -> list[str]:
    text = _guard_text(title)
    return [hit for hit in hits if hit in text]


def rule_guard_reason(title: str, hits: list[str]) -> Optional[str]:
    """
    The first GUARD_REASONS entry that stops a hard-rule hit firing on its
    own; None = a clean rule hit. Reads the title only: a phrase found just
    in the summary (live alert 7) is "summary_only", and a denial or price
    word in a summary says nothing about the headline the owner reads.
    "unknown_us_link" comes last: the title's own phrases do not name a path
    into US prices, so the classifier must judge it (alerting/us_link.py). A
    summary phrase with a known link cannot vouch for them.
    """
    text = _guard_text(title)
    title_hits = _title_hits(title, hits)
    if not title_hits:
        return "summary_only"
    if _DENIAL_RE.search(text):
        return "denial"
    if _PRICE_REPORT_RE.search(text):
        return "price_report"
    if _COMMENTARY_RE.search(_MONTH_MAY_RE.sub(" ", text)):
        return "commentary"
    if rule_country_us_link(title_hits)[1] is None:
        return "unknown_us_link"
    return None


def triage_article(article: NewsArticle) -> TriageResult:
    """
    HARD_RULE_PATTERNS checked first. A clean hit -> rule_tier_hit=True,
    severity decided as High by the caller, no LLM call needed, and
    matched_keywords holds the title's phrases only, because the caller
    reads the link and polarity from them. A hit
    rule_guard_reason() stops -> rule_tier_hit=False with guard_reason set,
    returned here rather than falling through, because phrases such as
    "sovereign default" have no keyword entry and would otherwise vanish;
    the caller classifies it like any ambiguous candidate. Then
    CATEGORY_SIGNAL_KEYWORDS (plausible category, ambiguous severity ->
    caller escalates to llm_classify.py). No match at all -> matched=False,
    with near_miss_score/near_miss_category recording the single
    best-scoring CATEGORY_SIGNAL_KEYWORDS phrase's word-level overlap
    (see _partial_match_score), purely for the non-match audit log
    (alerting/store.py's record_near_miss()) -- never used to alert on
    its own.
    """
    text = _searchable_text(article)

    for category, patterns in HARD_RULE_PATTERNS.items():
        hits = [p for p in patterns if p in text]
        if hits:
            reason = rule_guard_reason(article.title, hits)
            return TriageResult(
                matched=True, category=category, rule_tier_hit=reason is None,
                matched_keywords=_title_hits(article.title, hits) if reason is None else hits,
                near_miss_score=None, guard_reason=reason,
            )

    best_category: Optional[str] = None
    best_hits: list[str] = []
    for category, keywords in CATEGORY_SIGNAL_KEYWORDS.items():
        hits = [k for k in keywords if k in text]
        if len(hits) > len(best_hits):
            best_category, best_hits = category, hits

    if best_hits and not _is_minor_earthquake_only(text, best_category, best_hits):
        return TriageResult(matched=True, category=best_category, rule_tier_hit=False, matched_keywords=best_hits, near_miss_score=None)

    # No match at all -- record a real partial-match score (word-level
    # overlap against every CATEGORY_SIGNAL_KEYWORDS phrase) purely for
    # the near-miss audit log. `category` stays None here -- this is a
    # genuine no-match -- the best-scoring phrase's category is threaded
    # through separately as near_miss_category instead.
    near_miss_category, near_miss_score = _partial_match_score(text)
    return TriageResult(
        matched=False, category=None, rule_tier_hit=False, matched_keywords=[],
        near_miss_score=near_miss_score, near_miss_category=near_miss_category,
    )
