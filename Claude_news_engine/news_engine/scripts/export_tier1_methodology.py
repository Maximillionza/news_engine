"""
Exports the Causation Matrix workbook's POC sheets to docs/tier1-methodology.md (B3 T3), so the Tier 1
research task reads plain text instead of the .xlsx and a reviewer can diff methodology changes.

    python scripts/export_tier1_methodology.py            # regenerate the doc
    python scripts/export_tier1_methodology.py --check    # exit 1 when the committed doc is out of date

Per POC sheet the doc carries the covered titles with their tier (data_layer.tier1_events.TIER1_EVENTS), the
hand-written rule / rejected / confidence summary in SECTIONS (taken from the sheet and the research task's
prompt), then every data row of the sheet verbatim and its closing note. The workbook is read-only
(openpyxl read_only=True, data_only=True). A POC sheet added to or removed from the workbook without a
matching SECTIONS entry is an error, so the doc can never silently skip one.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

# Allow `python scripts/export_tier1_methodology.py` (script dir, not the app root, is on sys.path).
APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))
from data_layer.tier1_events import (  # noqa: E402
    TIER1_EVENTS, TIER1_FORMULA_CONFIDENCE, TIER1_FORMULA_SOURCE, TIER1_MARKET_IMPLIED_CONFIDENCE,
    TIER1_MARKET_IMPLIED_SOURCE,
)

WORKBOOK_PATH = APP_DIR / "docs" / "News_Engine_Causation_Matrix_v2.xlsx"
DOC_PATH = APP_DIR / "docs" / "tier1-methodology.md"
POC_PREFIX = "POC_"

# Workbook column header -> short label in the "(Lag: ...; Confidence: ...; Evidence: ...)" tail.
_FIELD_LABELS = {"Lag/frequency": "Lag", "Confidence": "Confidence", "Evidence / source": "Evidence"}

# Hand-written per sheet: which titles it covers, the rule the research task applies, what was rejected or is
# not verified, and how confidence is set. Keys must equal the workbook's POC_* sheets.
SECTIONS: dict[str, dict] = {
    "POC_CPI_Leading_Indicators": {
        "titles": ["CPI m/m", "Core CPI m/m", "CPI y/y", "Core CPI y/y"],
        "rule": (
            "Formula tier, not researched. The Cleveland Fed inflation nowcast (this sheet's Tier 1 \"published "
            "nowcast figure\" row) is compared with the release's forecast by the formula rule in the introduction "
            "and written per instrument by the Windows tasks NewsEngine_Tier1Weekly and NewsEngine_Tier1Daily. "
            "The m/m titles read nowcast_month.json (month-over-month, seasonally adjusted); the y/y titles read "
            "nowcast_year.json (year-over-year, based on not seasonally adjusted CPI and core CPI data, the same "
            "basis BLS publishes y/y on). The research task never logs these titles. The sheet's operating rule "
            "still frames the result: the nowcast is unreliable in the first 1-2 weeks of the month it covers and "
            "strong in the final 1-2 weeks before release."
        ),
        "rejected": [
            "ISM Manufacturing/Services Prices Paid as a CPI input: checked and rejected (Cleveland Fed Economic "
            "Commentary: predictive for producer prices, not consumer prices).",
            "PPI and Average Hourly Earnings as CPI leads: Tier 2, not verified against a primary source; not usable "
            "as live inputs.",
            "A nowcast number copied from an earlier research pass: only the live value is used (the sheet flags a "
            "6.59% figure as a scraping artifact).",
        ],
        "confidence": (
            f"Always \"{TIER1_FORMULA_CONFIDENCE}\" for formula rows: a published model output is primary-sourced "
            "but still a model, so never \"Certain\". In line with the forecast is a neutral call; no readable "
            "forecast writes no call at all."
        ),
    },
    "POC_PPI_Leading_Indicators": {
        "titles": ["PPI m/m"],
        "rule": (
            "Market-implied tier, not researched. The call is the Kalshi KXUSPPI ladder (ticketed by the release "
            "date, +/-1 day; strikes in the print's own unit) read by the market-implied rule in the introduction "
            "and written per instrument by the Windows tasks. The workbook's method below (BLS's own most recent "
            "prior PPI release read through the Final Demand-Intermediate Demand stages, plus the most recent ISM "
            "Manufacturing Prices Paid reading and the 5-district regional Fed prices-paid average one notch below "
            "it) is context for reading a miss, not an input to the call. The research task never logs this title."
        ),
        "rejected": [
            "PPI as a lead for CPI: the release-timing lead is certain, but the strength and lag of the pass-through "
            "rest on a secondary source only (Tier 2).",
            "A single region's prices-paid print on its own: noisy; only the 5-district average is used.",
        ],
        "confidence": (
            f"Always \"{TIER1_MARKET_IMPLIED_CONFIDENCE}\" for market-implied rows: a traded price is a crowd's "
            "bet, not a certainty. No 50% crossing among liquid strikes, a units mismatch or no readable forecast "
            "writes no call at all."
        ),
    },
    "POC_NFP_Leading_Indicators": {
        "titles": ["Non-Farm Employment Change"],
        "rule": (
            "Market-implied tier, not researched. The call is the Kalshi KXPAYROLLS ladder, ticketed by the "
            "reference month (the month before the release: KXPAYROLLS-26OCT settles on the October report "
            "released in November); its strikes are listed in jobs and divided by 1000 to match the forecast's "
            "\"K\". The market-implied rule in the introduction turns it into the call. The workbook's method below "
            "(initial jobless claims read against their own recent trend, turning roughly 2-4 months ahead of the "
            "unemployment-rate cycle) is context for reading a miss, not an input. The research task never logs "
            "this title."
        ),
        "rejected": [
            "ADP National Employment Report as an \"NFP preview\": REJECTED (City Index 2007-2024 backtest: 47.7% "
            "directional hit rate, worse than a coin flip; ADP counts a different construct from BLS payrolls).",
            "Continuing claims, JOLTS job openings, Challenger job cuts: Tier 2, not verified; not usable as live "
            "inputs.",
            "Large corporate layoff waves: no real in-window instance identified yet.",
        ],
        "confidence": (
            f"Always \"{TIER1_MARKET_IMPLIED_CONFIDENCE}\" for market-implied rows. The claims evidence below "
            "never raises or lowers it; it explains a miss after the print."
        ),
    },
    "POC_FOMC_Rate_Decision": {
        "titles": ["FOMC Meeting Minutes", "FOMC Statement", "Federal Funds Rate"],
        "rule": (
            "Federal Funds Rate is market-implied, not researched: the Kalshi KXFED ladder (ticketed by the meeting "
            "month, KXFED-26DEC is the December decision; strikes are the upper bound of the target range), read "
            "with the discrete median (the first strike at or below 50%) and compared with the forecast. FOMC "
            "Meeting Minutes and FOMC Statement have no numeric market and stay judgment: CME 30-Day Fed Funds "
            "futures-implied probability (FedWatch methodology: implied rate = 100 - futures price; probability of "
            "a 25bp move = (implied rate - EFFR) / 0.25, day-weighted in the meeting month) against the current "
            "Effective Federal Funds Rate published daily by the NY Fed, cross-checked against the other covered "
            "releases (NFP, CPI, PCE, PPI, GDP), which are what move the futures. A judgment call that rests on "
            "FedWatch starts its source or value with \"CME FedWatch\" and displays as market-implied."
        ),
        "rejected": [
            "Emergency / off-cycle Fed actions: the futures method cannot price them (a stated limitation of the "
            "method).",
            "Fed Chair transition effects on the reaction function: not quantified.",
        ],
        "confidence": (
            f"Federal Funds Rate: always \"{TIER1_MARKET_IMPLIED_CONFIDENCE}\" (market-implied). Statement and "
            "Minutes: Certain when a clear futures-implied probability exists (a live, transparent market price, "
            "not a forecast that needs validating); lower it to Likely or Guessing when the implied probability is "
            "not clear-cut."
        ),
    },
    "POC_GDP_Nowcast": {
        "titles": ["Prelim GDP q/q", "Advance GDP q/q", "Final GDP q/q", "GDP q/q"],
        "rule": (
            "Advance GDP q/q is market-implied, not researched: the Kalshi KXGDP ladder (ticketed by the release "
            "date, +/-1 day; KXGDP settles on the BEA Advance estimate only) read by the market-implied rule in the "
            "introduction. Prelim GDP q/q, Final GDP q/q and GDP q/q have no matching market and stay judgment: the "
            "Atlanta Fed's GDPNow nowcast and the Cleveland Fed's yield-curve-slope growth model (10-year minus "
            "3-month Treasury spread); both are verified Tier 1 sources. GDPNow is unreliable early in the quarter "
            "and its accuracy plateaus in roughly the last 25 days before release."
        ),
        "rejected": [
            "NY Fed Staff Nowcast, St. Louis Fed Economic News Index, Philadelphia Fed PRISM: named alternatives, "
            "not individually verified; cross-checks only.",
            "Tariff effects on the net-exports subcomponent: the GDP-specific magnitude is not measured.",
        ],
        "confidence": (
            f"Advance GDP q/q: always \"{TIER1_MARKET_IMPLIED_CONFIDENCE}\" (market-implied). Judgment titles: "
            "Certain when GDPNow and the yield-curve model agree; Likely when only one gives a clear read; Guessing "
            "with a neutral call when they disagree."
        ),
    },
    "POC_Core_PCE": {
        "titles": ["Core PCE Price Index m/m"],
        "rule": (
            "Formula tier, not researched. The Cleveland Fed inflation nowcast's own Core PCE series (\"Core PCE "
            "Inflation\" in nowcast_month.json: month-over-month, seasonally adjusted) is compared with the "
            "release's forecast by the formula rule in the introduction and written per instrument by the Windows "
            "tasks. The workbook's quantified CPI-to-PCE weighting adjustment (shelter is about 15% of PCE vs about "
            "33% of CPI, and PCE includes employer/government-paid healthcare and \"free\" financial services that "
            "CPI excludes, the confirmed driver of the July 2026 miss) is context for reading a miss, not an input "
            "to the call. The research task never logs this title."
        ),
        "rejected": [
            "The same-month CPI print used unadjusted as a direct predictor of PCE: downgraded to Tier 2 after the "
            "July 2026 test failed (PCE came in above CPI, the opposite of the standard rule).",
            "The 2016 Dallas Fed finding that healthcare depresses PCE: reversed in July 2026; check each time, "
            "never assume it.",
        ],
        "confidence": (
            "Certain only when the nowcast and the adjusted CPI read are primary-sourced and agree; the dilution "
            "size for any one shock is Guessing (not quantified); Guessing with a neutral call when the two "
            "disagree."
        ),
    },
    "POC_ISM_Manufacturing_PMI": {
        "titles": ["ISM Manufacturing PMI"],
        "rule": (
            "Market-implied tier, not researched. The call is the Kalshi KXISMPMI ladder, ticketed by the reference "
            "month (the month before the release); its markets are \"greater or equal\" and are read as \"above\" "
            "(outcomes step 0.1, so the difference is immaterial). The workbook's method below (the regional Federal "
            "Reserve manufacturing survey average that Yardeni Research says closely tracks the national PMI) is "
            "context for reading a miss, not an input. The research task never logs this title."
        ),
        "rejected": [
            "New Orders as the leading sub-component: practitioner consensus only, not tested; not weighted like a "
            "verified input.",
            "The composite's current weighting (equal vs New-Orders-weighted 30/25/20/15/10): not confirmed against "
            "ISM's own methodology document.",
        ],
        "confidence": (
            f"Always \"{TIER1_MARKET_IMPLIED_CONFIDENCE}\" for market-implied rows. The regional average alone "
            "would support at most Likely (a research house's tracking claim, not an academic correlation study)."
        ),
    },
    "POC_ISM_Services_PMI": {
        "titles": ["ISM Services PMI"],
        "rule": (
            "No verified Tier 1 leading indicator. Regional Fed services surveys (NY Fed Business Leaders Survey, "
            "Richmond Fed Services Revenues Index) are second tier: several pointing the same way corroborate, a "
            "single print does not. The Manufacturing method is never reused by analogy."
        ),
        "rejected": [
            "Manufacturing's regional-average finding applied to Services: deliberately not extended (no equivalent "
            "tracking claim exists).",
            "A single regional services print as a standalone signal: marginal.",
            "New Orders / Business Activity as leading sub-components: not verified.",
        ],
        "confidence": (
            "Expected default: Guessing, neutral, value \"NO VERIFIED TIER 1 INDICATOR FOR THIS EVENT TYPE YET\", "
            "unless another real Tier 1 signal is found and sourced; several regional surveys agreeing support at "
            "most Likely."
        ),
    },
    "POC_Retail_Sales": {
        "titles": ["Retail Sales m/m", "Core Retail Sales m/m"],
        "rule": (
            "Retail Sales m/m is market-implied, not researched: the Kalshi KXUSRETAIL ladder (ticketed by the "
            "release date, +/-1 day) read by the market-implied rule in the introduction. Core Retail Sales m/m has "
            "no Kalshi market and stays judgment: real-time card spending trackers (Bank of America's monthly "
            "tracker, JPMorgan Chase Institute's near-real-time tracker): actual transaction data with a 0.86 "
            "correlation to Census retail sales (0.93 after revisions) vs 0.69 for the consensus forecast. Core (ex "
            "autos, gasoline, building materials, food services) is read separately from headline; tariffs can "
            "raise nominal sales while volume falls. Headline/core splits: see POC_Sub_Event_Consolidation."
        ),
        "rejected": [
            "Consumer confidence indexes (Conference Board, University of Michigan): REJECTED (Croushore, University "
            "of Richmond: no significant value in forecasting consumer spending in real time, sometimes worse).",
            "The 10-120 day ISM-to-hard-data lag figure: removed; its source measured Michigan Sentiment, not ISM.",
        ],
        "confidence": (
            f"Retail Sales m/m: always \"{TIER1_MARKET_IMPLIED_CONFIDENCE}\" (market-implied). Core Retail Sales "
            "m/m: Certain when the card trackers are current and agree; Likely when only one is available; Guessing "
            "with a neutral call when they disagree or the tariff nominal/volume effect makes the direction "
            "ambiguous."
        ),
    },
    "POC_Sub_Event_Consolidation": {
        "titles": [],
        "rule": (
            "Applies when sub-readings (headline vs core) point different ways for the one judgment title it still "
            "covers, Core Retail Sales m/m (read against headline Retail Sales m/m): the net direction follows the "
            "sub-reading with the larger surprise relative to its own typical volatility / forecast-distribution "
            "tightness, judged from real data, never computed. Not assumed to transfer to NFP. The formula-tier "
            "titles (CPI and Core CPI m/m and y/y, Core PCE m/m) and the market-implied titles (PPI m/m, Retail "
            "Sales m/m) each get their own rule call; the CPI cases below remain the evidence for the hypothesis."
        ),
        "rejected": [
            "A fixed sub-component hierarchy (\"core always wins\") or a vote across sub-readings.",
            "Treating the hypothesis as validated: no genuine discriminating third case has been found.",
        ],
        "confidence": (
            "A working hypothesis (two real cases), not a settled rule: it decides the direction of a split, it "
            "never raises confidence; a split that cannot be judged from real data is logged Guessing with a "
            "neutral call."
        ),
    },
}

_INTRO = [
    "# Tier 1 methodology",
    "",
    "Plain-text export of the POC sheets in `docs/News_Engine_Causation_Matrix_v2.xlsx` (the source of truth "
    "for the research evidence). Do not hand-edit: change the workbook or `SECTIONS` in "
    "`scripts/export_tier1_methodology.py`, then regenerate with `python scripts/export_tier1_methodology.py` "
    "(`--check` exits 1 when this file is out of date). Which titles are covered, and their tier, comes from "
    "`TIER1_EVENTS` in `data_layer/tier1_events.py`. The workbook rows below are the sheet's own words, "
    "unedited.",
    "",
    "Tiers: **formula** = a deterministic rule on a published model output, captured by the Windows tasks "
    "(CPI m/m, Core CPI m/m, CPI y/y, Core CPI y/y, Core PCE Price Index m/m); "
    "**judgment** = researched by hand before each release by the Tier 1 research task "
    "(`scripts/tier1_research.py`), where the first pre-release call stands and a later re-check is only "
    "logged as a late check; **market-implied** = a fixed rule on a traded market's prices, captured by the "
    "same Windows tasks (Kalshi: PPI m/m, Non-Farm Employment Change, Federal Funds Rate, Advance GDP q/q, ISM "
    "Manufacturing PMI, Retail Sales m/m). One producer per title: the research task refuses formula and "
    "market-implied titles. A judgment row whose source mentions FedWatch, or whose value opens with a "
    "FedWatch citation, also displays as market-implied (its call is the futures-implied rate path, not a "
    "researcher's view); a mere mid-text mention of FedWatch stays judgment.",
    "",
    "Formula rule (the five formula titles): `scripts/capture_nowcast_from_cleveland.py` compares the "
    "Cleveland Fed nowcast with the release's forecast. The m/m titles read `nowcast_month.json` "
    "(month-over-month, seasonally adjusted); CPI y/y and Core CPI y/y read `nowcast_year.json` "
    "(year-over-year, based on not seasonally adjusted CPI and core CPI data, the basis BLS publishes y/y on). Within one rounding step of the forecast's own "
    "published precision is in line (neutral call); above is hotter, below is cooler. Each tracked instrument's "
    "direction comes from `webapp.stats_methods.market_lean` (buy -> bullish, sell -> bearish, mixed -> "
    f"neutral). Confidence is always \"{TIER1_FORMULA_CONFIDENCE}\" and the source is "
    f"\"{TIER1_FORMULA_SOURCE}\". At most one row is written per release and instrument per distinct (nowcast, "
    "forecast text), so a revised forecast writes a new row, and no readable forecast writes nothing (never a "
    "guessed neutral).",
    "",
    "Market-implied rule (the six Kalshi titles): `scripts/capture_tier1.py` reads the open \"above strike\" "
    "ladder of the Kalshi event that resolves on the release (public read-only API; KXPAYROLLS, KXUSRETAIL, "
    "KXUSPPI, KXISMPMI, KXGDP, KXFED) and applies `webapp/tier1_market.py`. Only liquid strikes count: open "
    "interest >= 10, a quoted ask, and ask - bid <= 0.25. Each strike's yes midpoint is P(print above the "
    "strike), made non-increasing in the strike by a running minimum. The implied median is where that curve "
    "crosses 50%: linear between the two strikes around the crossing, or the first strike at or below 50% for "
    "the discrete Fed Funds ladder (KXFED; rates move in 25 bp steps, so interpolating a priced hike would land "
    "between two possible outcomes). The median is compared with the forecast with the same one-rounding-step "
    "tolerance as the formula rule (hotter / in line / cooler), and each tracked instrument's direction comes "
    "from `market_lean` with the series' own surprise sign (higher = USD-bullish for all six). Confidence is "
    f"always \"{TIER1_MARKET_IMPLIED_CONFIDENCE}\" and the source is \"{TIER1_MARKET_IMPLIED_SOURCE}\". At "
    "most one row is written per release and instrument per distinct (implied median, forecast text), so a "
    "revised forecast writes a new row. No row (reported, never a guessed neutral) when the curve has no 50% "
    "crossing among liquid strikes, the forecast sits far outside the event's listed strikes (a units mismatch), "
    "there is no readable forecast, or no open event matches the release. The Stats tab scores a Kalshi row with "
    "the same series sign it was written with, so Federal Funds Rate and Advance GDP q/q are scored although the "
    "shared surprise map (and so the News method) leaves them out.",
    "",
]


def _title_line(titles: list[str]) -> str:
    if not titles:
        return "No event titles: this sheet is guidance shared across events (see the rule)."
    return "Covered titles: " + ", ".join(f"`{title}` ({TIER1_EVENTS[title]})" for title in titles)


def _cell(value: object) -> Optional[str]:
    """Cell -> stripped text, None for an empty cell."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _row_line(headers: list[str], cells: list[Optional[str]]) -> str:
    """One data row: **Tier** — Indicator: Mechanism (Lag: ...; Confidence: ...; Evidence: ...)."""
    tier, indicator, mechanism = (cells + [None, None, None])[:3]
    line = f"- **{tier}** — {indicator}: {mechanism}"
    extras = [
        f"{_FIELD_LABELS.get(header, header)}: {cell}"
        for header, cell in zip(headers[3:], cells[3:]) if cell is not None
    ]
    if extras:
        line += " (" + "; ".join(extras) + ")"
    return line


def _sheet_lines(sheet_name: str, rows: list[tuple]) -> list[str]:
    spec = SECTIONS[sheet_name]
    lines = [f"## {sheet_name}", "", _title_line(spec["titles"]), "", f"**Rule:** {spec['rule']}", "",
             "**Rejected or not verified:**", ""]
    lines += [f"- {item}" for item in spec["rejected"]]
    lines += ["", f"**Confidence rules:** {spec['confidence']}", "", "**Workbook rows** (verbatim):", ""]
    headers = [_cell(value) or "" for value in rows[0]]
    notes: list[str] = []
    for row in rows[1:]:
        cells = [_cell(value) for value in row]
        if not any(cells):
            continue
        if all(cell is None for cell in cells[1:]):
            notes.append(cells[0])   # a first-column-only row is the sheet's closing note
        else:
            lines.append(_row_line(headers, cells))
    for note in notes:
        lines += ["", note]
    lines.append("")
    return lines


def render(workbook_path: Path) -> str:
    """The full markdown export of the workbook's POC sheets (deterministic; reads the workbook only)."""
    import openpyxl

    workbook = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)
    try:
        sheet_names = [name for name in workbook.sheetnames if name.startswith(POC_PREFIX)]
        if set(sheet_names) != set(SECTIONS):
            missing = sorted(set(sheet_names) - set(SECTIONS))
            stale = sorted(set(SECTIONS) - set(sheet_names))
            raise ValueError(f"POC sheets and SECTIONS differ: no SECTIONS entry for {missing}, no sheet for {stale}")
        lines = list(_INTRO)
        for name in sheet_names:
            lines += _sheet_lines(name, list(workbook[name].iter_rows(values_only=True)))
    finally:
        workbook.close()
    return "\n".join(lines).rstrip("\n") + "\n"


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export the workbook's POC sheets to docs/tier1-methodology.md")
    parser.add_argument("--check", action="store_true", help="exit 1 when the doc differs from a fresh render; write nothing")
    parser.add_argument("--workbook", type=Path, default=WORKBOOK_PATH, help="source workbook (read-only)")
    parser.add_argument("--out", type=Path, default=DOC_PATH, help="markdown file to write or check")
    args = parser.parse_args(argv)

    text = render(args.workbook)
    if args.check:
        current = args.out.read_text(encoding="utf-8") if args.out.exists() else None
        if current != text:
            print(f"{args.out} is out of date: run python scripts/export_tier1_methodology.py", file=sys.stderr)
            return 1
        print(f"{args.out} is current")
        return 0
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
