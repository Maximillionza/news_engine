"""
Title registry and fill rule for official-publisher actuals (ACT Task 2).

`OFFICIAL_SPECS` maps an exact Forex Factory title to the official series
that produces its headline number: source, series, transform, FF formatting,
New York release time and the period rule. FF stays the calendar (titles,
times, forecasts); this module only says where the published number lives.

Period rule, not "latest value": a row's reference period is computed from
its release date (`expected_period`), and `decide_fill` writes only when the
official data holds that exact period. An API still showing last month, a
delayed release or a two-period release therefore never produces a write.

Older rows: official APIs serve today's revised numbers, so a row that has a
later release of the same series is filled only for series that are never
revised (Fed, Treasury, EIA weekly stocks), and only when the value also
equals FF's `previous` on that next release. Older rows of revised series are
left to the FRED/ALFRED first-print backfill where the title has one
(fred_history.FRED_HISTORY_SPECS); GDP, GDP Price Index, Productivity, Unit
Labor Costs and ECI have none, so such rows stay empty and are reported.

Re-estimates (Prelim/Final GDP, Revised Productivity / Unit Labor Costs)
publish a later estimate of a period the API already holds, so the period rule
alone cannot tell the new print from the stale one. `decide_fill` writes one
only with proof that the re-estimate is out (`ReestimateEvidence`: BEA's
table note "LastRevised: <date>" on or after the release date; for BLS, a
"R" (revised) footnote on the period in any series of the same release),
so an unchanged re-estimate is written too.

Census codes were resolved in Task 1 (see census.py); the three unresolved
Census titles (Final / Prelim Wholesale Inventories m/m, Goods Trade Balance)
are deliberately absent, so coverage reports them as not mapped and they keep
their FRED backfill. Every twin below exists on FRED (checked 2026-10-28,
including the plan's "(verify)" ones: PRS85006092, PRS85006112,
A191RI1Q225SBEA); the plan's crude twin WCESTUS1 does not, so crude has none.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, replace
from typing import Any, Iterable, Mapping, Optional
from zoneinfo import ZoneInfo

from data_layer.calendar_feed import _parse_numeric
from data_layer.fred_history import values_match

# New source labels written to event_history.source; 'fred' already exists (claims use it).
PUBLISHER_SOURCES = ("bls", "bea", "census", "eia", "fed", "treasury")
_NY = ZoneInfo("America/New_York")
_SUFFIXES = ("%", "K", "M", "B")
# Bid-to-cover decimals when an auction row has no template (FF prints "4.83|2.7").
_AUCTION_COVER_DECIMALS = 1


@dataclass(frozen=True)
class OfficialSpec:
    source: str                  # one of PUBLISHER_SOURCES or "fred"
    series: str                  # adapter key, e.g. "CUSR0000SA0", "T20807:M:DPCCRGM", "marts:44X72:MPCSM",
                                 # "petroleum/stoc/wstk:WCESTUS1", "fomc_upper", "Note:10-Year", "ICSA"
    field: str                   # "level" | "pct1" | "pct12" (BLS calculations); "level" elsewhere
    transform: str               # "lin" | "chg" | "pch" | "pc1" | "auction"
    frequency: str               # "monthly" | "quarterly" | "weekly" | "event"
    unit_scale: float            # source units -> FF suffix units
    suffix: str                  # "%", "K", "M", "B", "" when the FF row has no template
    decimals: int                # used only when the FF row has no template
    release_time_et: dt.time
    min_lag_days: int = 7
    week_end_weekday: Optional[int] = None    # 5 = Saturday (claims), 4 = Friday (EIA)
    revises: bool = True
    fred_twin: Optional[tuple[str, str]] = None   # (FRED series id, transform) for the gate
    # A later estimate of a period that is ALREADY published (Prelim/Final GDP, Revised Productivity):
    # FF's `previous` is the earlier estimate of the same period, and the API holds the period before
    # this release, so the period rule alone cannot tell the new print from the stale one (see decide_fill).
    # Outside the plan's interface: added in T2 without prior sign-off, flagged to the owner in the review fix.
    reestimate: bool = False
    # BLS only: other series of the same release, fetched in the same POST, whose "R" (revised) footnote
    # on the period proves a re-estimate is out even when this series' own value did not change.
    revision_family: tuple[str, ...] = ()


_T0830 = dt.time(8, 30)
_T1000 = dt.time(10, 0)
_T1030 = dt.time(10, 30)


def _bls(series: str, field: str, transform: str, twin: Optional[tuple[str, str]], *, lag: int = 7,
         frequency: str = "monthly", scale: float = 1.0, suffix: str = "%", decimals: int = 1,
         time: dt.time = _T0830) -> OfficialSpec:
    return OfficialSpec("bls", series, field, transform, frequency, scale, suffix, decimals, time,
                        min_lag_days=lag, fred_twin=twin)


def _pct(source: str, series: str, transform: str, twin: Optional[tuple[str, str]], *, lag: int = 7,
         frequency: str = "monthly", time: dt.time = _T0830) -> OfficialSpec:
    """A one-decimal percent headline (most m/m and q/q titles)."""
    return OfficialSpec(source, series, "level", transform, frequency, 1.0, "%", 1, time,
                        min_lag_days=lag, fred_twin=twin)


_GDP = _pct("bea", "T10101:Q:A191RL", "lin", ("A191RL1Q225SBEA", "lin"), frequency="quarterly")
_GDP_PRICE = _pct("bea", "T10107:Q:A191RV", "lin", ("A191RI1Q225SBEA", "lin"), frequency="quarterly")
# Productivity and Costs (nonfarm business, q/q annual rate): productivity, unit labor costs, output,
# hours, hourly compensation, real hourly compensation. BLS footnotes a value "R" only when the revision
# changed it (live 2026-10-28: Q2 productivity unchanged at 1.4 has none, ULC / compensation have "R"),
# so any series of the release is proof that a Revised estimate is out.
_PRODUCTIVITY_FAMILY = ("PRS85006092", "PRS85006112", "PRS85006042", "PRS85006032", "PRS85006102", "PRS85006152")
_PRODUCTIVITY = replace(_bls("PRS85006092", "level", "lin", ("PRS85006092", "lin"), frequency="quarterly"),
                        revision_family=_PRODUCTIVITY_FAMILY)
_UNIT_LABOR = replace(_bls("PRS85006112", "level", "lin", ("PRS85006112", "lin"), frequency="quarterly"),
                      revision_family=_PRODUCTIVITY_FAMILY)

# Exact FF titles (live USD title list, 2026-10-28) -> official series.
OFFICIAL_SPECS: dict[str, OfficialSpec] = {
    # BLS (Employment Situation lag 0: the 1st-Friday release can follow its month by a day or two).
    "Non-Farm Employment Change": _bls("CES0000000001", "level", "chg", ("PAYEMS", "chg"), lag=0, suffix="K", decimals=0),
    "Unemployment Rate": _bls("LNS14000000", "level", "lin", ("UNRATE", "lin"), lag=0),
    "Average Hourly Earnings m/m": _bls("CES0500000003", "pct1", "lin", ("CES0500000003", "pch"), lag=0),
    "CPI m/m": _bls("CUSR0000SA0", "pct1", "lin", ("CPIAUCSL", "pch")),
    "Core CPI m/m": _bls("CUSR0000SA0L1E", "pct1", "lin", ("CPILFESL", "pch")),
    "CPI y/y": _bls("CUUR0000SA0", "pct12", "lin", ("CPIAUCNS", "pc1")),
    "Core CPI y/y": _bls("CUUR0000SA0L1E", "pct12", "lin", ("CPILFENS", "pc1")),
    "PPI m/m": _bls("WPSFD4", "pct1", "lin", ("PPIFIS", "pch")),
    "Core PPI m/m": _bls("WPSFD49104", "pct1", "lin", ("PPIFES", "pch")),
    "Import Prices m/m": _bls("EIUIR", "pct1", "lin", ("IR", "pch")),
    "JOLTS Job Openings": _bls("JTS000000000000000JOL", "level", "lin", ("JTSJOL", "lin"),
                               scale=0.001, suffix="M", decimals=2, time=_T1000),
    "Employment Cost Index q/q": _bls("CIS1010000000000Q", "level", "lin", None, frequency="quarterly"),
    # Prelim = first estimate of the quarter; Revised = second estimate of the same quarter.
    "Prelim Nonfarm Productivity q/q": _PRODUCTIVITY,
    "Revised Nonfarm Productivity q/q": replace(_PRODUCTIVITY, reestimate=True),
    "Prelim Unit Labor Costs q/q": _UNIT_LABOR,
    "Revised Unit Labor Costs q/q": replace(_UNIT_LABOR, reestimate=True),
    # BEA NIPA. Advance = first estimate; Prelim and Final re-estimate the same quarter.
    "Advance GDP q/q": _GDP,
    "Prelim GDP q/q": replace(_GDP, reestimate=True),
    "Final GDP q/q": replace(_GDP, reestimate=True),
    "Advance GDP Price Index q/q": _GDP_PRICE,
    "Prelim GDP Price Index q/q": replace(_GDP_PRICE, reestimate=True),
    "Final GDP Price Index q/q": replace(_GDP_PRICE, reestimate=True),
    "Core PCE Price Index m/m": _pct("bea", "T20807:M:DPCCRGM", "lin", ("PCEPILFE", "pch")),
    "Personal Income m/m": _pct("bea", "T20600:M:A065RC", "pch", ("PI", "pch")),
    "Personal Spending m/m": _pct("bea", "T20600:M:DPCERC", "pch", ("PCE", "pch")),
    # Census EITS (codes resolved in Task 1, see census.py).
    "Retail Sales m/m": _pct("census", "marts:44X72:MPCSM", "lin", ("RSAFS", "pch")),
    "Core Retail Sales m/m": _pct("census", "marts:44Y72:MPCSM", "lin", ("RSFSXMV", "pch")),
    "Durable Goods Orders m/m": _pct("census", "advm3:MDM:MPCNO", "lin", ("DGORDER", "pch")),
    "Core Durable Goods Orders m/m": _pct("census", "advm3:DXT:MPCNO", "lin", ("ADXTNO", "pch")),
    "Housing Starts": OfficialSpec("census", "resconst:ASTARTS:TOTAL", "level", "lin", "monthly", 0.001, "M", 2,
                                   _T0830, fred_twin=("HOUST", "lin")),
    "Building Permits": OfficialSpec("census", "resconst:APERMITS:TOTAL", "level", "lin", "monthly", 0.001, "M", 2,
                                     _T0830, fred_twin=("PERMIT", "lin")),
    "New Home Sales": OfficialSpec("census", "ressales:ASOLD:TOTAL", "level", "lin", "monthly", 1.0, "K", 0,
                                   _T1000, fred_twin=("HSN1F", "lin")),
    "Construction Spending m/m": _pct("census", "vip:XXXX:MPCT", "lin", ("TTLCONS", "pch"), time=_T1000),
    "Business Inventories m/m": _pct("census", "mtis:TOTBUS:MPCIM", "lin", ("BUSINV", "pch"), lag=20, time=_T1000),
    "Trade Balance": OfficialSpec("census", "ftd:BOPGS:BAL", "level", "lin", "monthly", 0.001, "B", 1,
                                  _T0830, min_lag_days=20, fred_twin=("BOPGSTB", "lin")),
    "Factory Orders m/m": _pct("census", "m3:MTM:MPCNO", "lin", ("AMTMNO", "pch"), lag=20, time=_T1000),
    # EIA weekly stocks: levels by week-ending Friday; FF prints the weekly change. Never revised.
    # No twin: FRED has no WCESTUS1 (HTTP 400, checked 2026-10-28), and an unrevised series needs none.
    "Crude Oil Inventories": OfficialSpec("eia", "petroleum/stoc/wstk:WCESTUS1", "level", "chg", "weekly", 0.001,
                                          "M", 1, _T1030, min_lag_days=0, week_end_weekday=4, revises=False),
    "Natural Gas Storage": OfficialSpec("eia", "natural-gas/stor/wkly:NW2_EPG0_SWO_R48_BCF", "level", "chg", "weekly",
                                        1.0, "B", 0, _T1030, min_lag_days=0, week_end_weekday=4, revises=False),
    # Fed: upper bound of the target range from the FOMC statement. No twin: DFEDTARU changes the
    # day AFTER the statement (it would never match on the statement date), and the number is never revised.
    "Federal Funds Rate": OfficialSpec("fed", "fomc_upper", "level", "lin", "event", 1.0, "%", 2,
                                       dt.time(14, 0), min_lag_days=0, revises=False),
    # TreasuryDirect: "high yield|bid-to-cover", reopenings included, TIPS excluded.
    "10-y Bond Auction": OfficialSpec("treasury", "Note:10-Year", "level", "auction", "event", 1.0, "", 2,
                                      dt.time(13, 0), min_lag_days=0, revises=False),
    "30-y Bond Auction": OfficialSpec("treasury", "Bond:30-Year", "level", "auction", "event", 1.0, "", 2,
                                      dt.time(13, 0), min_lag_days=0, revises=False),
    # Weekly claims via FRED ICSA (DOL's machine-readable data lags by weeks); week ends Saturday.
    "Unemployment Claims": OfficialSpec("fred", "ICSA", "level", "lin", "weekly", 0.001, "K", 0, _T0830,
                                        min_lag_days=0, week_end_weekday=5, fred_twin=("ICSA", "lin")),
}


# ---------------------------------------------------------------- periods

def _month_start(day: dt.date) -> dt.date:
    return day.replace(day=1)


def _add_months(period: dt.date, months: int) -> dt.date:
    index = period.year * 12 + (period.month - 1) + months
    return dt.date(index // 12, index % 12 + 1, 1)


def expected_period(spec: OfficialSpec, release_et: dt.date) -> dt.date:
    """
    The reference period a release on `release_et` (New York date) publishes:
    monthly/quarterly = the latest period whose last day is on or before
    `release_et - min_lag_days`; weekly = the latest `week_end_weekday` on or
    before that day; event = the release date itself.
    """
    if spec.frequency == "event":
        return release_et
    cutoff = release_et - dt.timedelta(days=spec.min_lag_days)
    if spec.frequency == "weekly":
        if spec.week_end_weekday is None:
            raise ValueError("weekly spec needs week_end_weekday")
        return cutoff - dt.timedelta(days=(cutoff.weekday() - spec.week_end_weekday) % 7)
    if spec.frequency == "monthly":
        # The month containing cutoff+1 day is complete only if cutoff is its last day.
        return _add_months(_month_start(cutoff + dt.timedelta(days=1)), -1)
    if spec.frequency == "quarterly":
        after = cutoff + dt.timedelta(days=1)
        quarter_start = dt.date(after.year, 3 * ((after.month - 1) // 3) + 1, 1)
        return _add_months(quarter_start, -3)
    raise ValueError(f"unknown frequency {spec.frequency!r}")


def prior_period(spec: OfficialSpec, period: dt.date, known: Iterable[dt.date]) -> Optional[dt.date]:
    """
    The period before `period`: one month / quarter / week back (None when the
    data does not hold it), or for events the latest known date before it.
    """
    known_set = set(known)
    if spec.frequency == "event":
        earlier = [d for d in known_set if d < period]
        return max(earlier) if earlier else None
    if spec.frequency == "monthly":
        prior = _add_months(period, -1)
    elif spec.frequency == "quarterly":
        prior = _add_months(period, -3)
    elif spec.frequency == "weekly":
        prior = period - dt.timedelta(days=7)
    else:
        raise ValueError(f"unknown frequency {spec.frequency!r}")
    return prior if prior in known_set else None


def value_for(spec: OfficialSpec, series: Mapping[dt.date, Any], period: dt.date) -> Optional[float | tuple[float, float]]:
    """The headline value for `period` in source units (before `unit_scale`); None if a needed point is missing."""
    current = series.get(period)
    if current is None:
        return None
    if spec.transform in ("lin", "auction"):
        return current
    if spec.transform == "pc1":
        base = series.get(period.replace(year=period.year - 1))
        return None if not base else (current / base - 1.0) * 100.0
    prior = prior_period(spec, period, series.keys())
    base = series.get(prior) if prior is not None else None
    if base is None:
        return None
    if spec.transform == "chg":
        return current - base
    if spec.transform == "pch":
        return None if not base else (current / base - 1.0) * 100.0
    raise ValueError(f"unknown transform {spec.transform!r}")


# ---------------------------------------------------------------- formatting

def _template_shape(template: Optional[str]) -> Optional[tuple[str, int]]:
    """(suffix, decimals) of an FF number string ("7.23M" -> ("M", 2)), None if it does not parse."""
    if template is None or _parse_numeric(template) is None:
        return None
    text = template.strip().replace(",", "")
    suffix = ""
    if text and text[-1].upper() in _SUFFIXES:
        suffix, text = text[-1].upper(), text[:-1]
    return suffix, (len(text.split(".", 1)[1]) if "." in text else 0)


def _fixed(value: float, decimals: int) -> str:
    """Fixed-point text; a value that rounds to zero carries no minus sign (as fred_history.format_value)."""
    text = f"{value:.{decimals}f}"
    return f"{0.0:.{decimals}f}" if float(text) == 0.0 else text


def _pair(text: Optional[str]) -> Optional[tuple[str, str]]:
    """An auction string "4.83|2.7" split into its two parts when both parse."""
    if not text or text.count("|") != 1:
        return None
    left, right = (part.strip() for part in text.split("|"))
    if _parse_numeric(left) is None or _parse_numeric(right) is None:
        return None
    return left, right


def format_like(value: float | tuple[float, float], template: Optional[str], spec: OfficialSpec) -> str:
    """
    Scale, then print with the template's decimals and suffix when its suffix
    equals `spec.suffix` (else the spec's defaults). Auctions print
    "yield|cover", each part with its template part's decimals.
    """
    if spec.transform == "auction":
        high_yield, cover = value  # type: ignore[misc]
        parts = _pair(template)
        d1, d2 = spec.decimals, _AUCTION_COVER_DECIMALS
        if parts is not None:
            d1, d2 = _template_shape(parts[0])[1], _template_shape(parts[1])[1]
        return f"{_fixed(high_yield, d1)}|{_fixed(cover, d2)}"
    scaled = float(value) * spec.unit_scale  # type: ignore[arg-type]
    shape = _template_shape(template)
    decimals = shape[1] if shape is not None and shape[0] == spec.suffix else spec.decimals
    return _fixed(scaled, decimals) + spec.suffix


def is_ff_number(text: Optional[str]) -> bool:
    """True for a numeric FF string, auction pairs included ("0.3%", "-23K", "4.83|2.7")."""
    return _parse_numeric(text) is not None or _pair(text) is not None


def ff_values_match(stored: Optional[str], candidate: Optional[str]) -> bool:
    """fred_history.values_match (half the stored rounding step), part by part for auction pairs."""
    stored_pair, candidate_pair = _pair(stored), _pair(candidate)
    if stored_pair is not None or candidate_pair is not None:
        if stored_pair is None or candidate_pair is None:
            return False
        return all(values_match(s, c) for s, c in zip(stored_pair, candidate_pair))
    return values_match(stored, candidate)


# ---------------------------------------------------------------- fill rule

@dataclass(frozen=True)
class FillDecision:
    actual: Optional[str]
    reason: str                  # "fill" or why not


@dataclass(frozen=True)
class ReestimateEvidence:
    """
    What a publisher answer says about re-estimates (fetch.fetch_for_specs
    builds one per BEA table and per BLS series): BEA's table note
    "LastRevised: <date>", and the BLS periods footnoted "R" in the series or
    its `revision_family`.
    """
    last_revised: Optional[dt.date] = None
    revised_periods: frozenset[dt.date] = frozenset()

    def proves(self, period: dt.date, release_et: dt.date) -> bool:
        """True when the answer shows a re-estimate of `period` published on or after `release_et`."""
        if self.last_revised is not None and self.last_revised >= release_et:
            return True
        return period in self.revised_periods


def release_date_et(event_time_utc: dt.datetime) -> dt.date:
    """The New York calendar date of a release (the period rule's reference day)."""
    return event_time_utc.astimezone(_NY).date()


def decide_fill(spec: OfficialSpec, event_time_utc: dt.datetime, forecast: Optional[str], previous: Optional[str],
                series: Mapping[dt.date, Any], later_release: bool, later_previous: Optional[str],
                reestimate_evidence: Optional[ReestimateEvidence] = None) -> FillDecision:
    """
    Whether (and what) to write for one row. Order: the expected period is not
    in the data -> wait; the row has a later release and the series revises ->
    never (today's value is a revision, not the first print); a re-estimate
    (`spec.reestimate`) without proof that it is published -> wait; FF's
    `previous` on the next release disagrees -> never; else the value,
    formatted like the row's forecast (then previous).

    Re-estimate proof is `reestimate_evidence` (from the same fetch; see
    ReestimateEvidence), which also lets an unchanged re-estimate be written.
    Without evidence (a BEA answer with no LastRevised note) the only proof
    is a value that differs from the earlier estimate in `previous`.
    """
    release_et = release_date_et(event_time_utc)
    period = expected_period(spec, release_et)
    value = value_for(spec, series, period)
    if value is None:
        return FillDecision(None, "awaiting publication")
    if later_release and spec.revises:
        return FillDecision(None, f"revised since release (first print not available from {spec.source})")
    template = next((t for t in (forecast, previous) if is_ff_number(t)), None)
    actual = format_like(value, template, spec)
    if spec.reestimate:
        # Before publication the API still holds the earlier estimate (FF's `previous`) for this period.
        if reestimate_evidence is not None:
            if not reestimate_evidence.proves(period, release_et):
                return FillDecision(None, "awaiting publication")
        elif not (is_ff_number(previous) and not ff_values_match(previous, actual)):
            return FillDecision(None, f"re-estimate not distinguishable (no revision evidence from {spec.source})")
    if is_ff_number(later_previous) and not ff_values_match(later_previous, actual):
        return FillDecision(None, "disagrees with FF previous on the next release")
    return FillDecision(actual, "fill")
