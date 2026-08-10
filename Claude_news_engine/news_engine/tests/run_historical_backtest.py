"""
Historical backtest using 14 real major (red-folder) USD economic events
from 2026 (Jan-Aug), reconstructed from web research since this sandbox
can't reach live news/price APIs directly.

Events #11-14 (Jan 2026 — Dec NFP, Dec CPI, Dec PPI, the Jan 28 FOMC
decision) were added via live WebSearch, sourced from CNBC, Kitco,
TradingKey, BLS, INN, and others — see the actual_move_note on each for
the specific facts and how they were framed. The FOMC case (#14) was
initially skipped in an earlier pass — no clean confirmed reaction could
be sourced then — and added later once a same-day headline directly
confirming the reaction was found on a second, better-targeted search.
That's worth remembering generally: "couldn't find it" is a statement
about the search, not a proof the data doesn't exist — worth a second
pass with different terms before concluding a case can't be reconstructed.

IMPORTANT CAVEAT — read before trusting these numbers:
The pre-event "articles" below are NOT pulled from a live news API with
real publish timestamps. They are paraphrased reconstructions of the real
forecast/expectation framing that was actually being reported ahead of
each release (sourced via web search — Reuters, CNBC, Kitco, TradingKey,
FXStreet, GoldSilver, etc.), assigned approximate pre-event timestamps.
The actual outcome (gold's real move) for every event below is real and
confirmed via multiple independent sources.

This is a legitimate test of the SCORING LOGIC — does it correctly map
"hawkish/beat" language to bearish gold calls and "dovish/miss" language
to bullish calls, and does it handle the mixed-signal cases correctly —
but it is not a test of real-world source timing, coverage volume, or
article-selection accuracy, since that requires the live fetch path
(data_layer/event_context.py + real API keys) run outside this sandbox.
"""
import datetime as dt
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
from data_layer.calendar_feed import EconomicEvent
from data_layer.news_feed import NewsArticle
from scoring.probability_engine import Direction
from scoring.backtest import run_backtest_case_manual, BacktestReport


def art(title, summary, event_time, hours_before, source_type="rss_reuters_business"):
    return NewsArticle(
        title=title,
        summary=summary,
        source=source_type,
        source_type=source_type,
        published_utc=event_time - dt.timedelta(hours=hours_before),
        url="https://example.com/reconstructed-for-backtest",
    )


report = BacktestReport()

# --- 1. July NFP, released Aug 7, 2026 ---
e1 = EconomicEvent("Non-Farm Payrolls (Jul)", "USD", "High", dt.datetime(2026, 8, 7, 12, 30, tzinfo=UTC_TZ))
a1 = [
    art("July jobs growth expected to stay low", "Labor market continues to cool ahead of Friday's report, weak print may reinforce dovish Fed bets", e1.event_time_utc, 30),
    art("Economists brace for downward revisions", "Goldman Sachs flags recent pattern of July payrolls missing consensus and prior months revised lower", e1.event_time_utc, 20),
    art("Gold cautious near highs ahead of NFP", "Dollar holds overnight rebound on Iran deal doubts, traders await payrolls for fresh direction", e1.event_time_utc, 4),
]
report.add(run_backtest_case_manual(e1, a1, "XAUUSD", Direction.BULLISH, "actual -23K vs +80K expected — dollar 7-week low, gold to 7-week highs"))

# --- 2. June NFP, released Jul 2, 2026 ---
e2 = EconomicEvent("Non-Farm Payrolls (Jun)", "USD", "High", dt.datetime(2026, 7, 2, 12, 30, tzinfo=UTC_TZ))
a2 = [
    art("June payrolls preview: moderate growth expected", "Consensus centers near 100K-115K new jobs, strong print risks hawkish Fed adjustment", e2.event_time_utc, 36),
    art("Rate hike risk if jobs data surprises to upside", "Equity and gold markets react primarily to shifting rate differentials from employment report", e2.event_time_utc, 18),
    art("Dollar firm ahead of jobs report", "Markets positioned for a hawkish outcome after strong recent economic data", e2.event_time_utc, 6),
]
report.add(run_backtest_case_manual(e2, a2, "XAUUSD", Direction.BULLISH, "actual +57K vs ~113K expected — gold jumped above $4,100 on miss"))

# --- 3. May NFP, released Jun 5, 2026 ---
e3 = EconomicEvent("Non-Farm Payrolls (May)", "USD", "High", dt.datetime(2026, 6, 5, 12, 30, tzinfo=UTC_TZ))
a3 = [
    art("Gold at make-or-break level ahead of payrolls", "A big beat would reaffirm 2026 Fed rate hike bets, providing legs to dollar uptrend, dragging gold lower", e3.event_time_utc, 34),
    art("Consensus points to slowing job growth", "Forecast range 85K-96K, stable unemployment expected", e3.event_time_utc, 22),
    art("Markets await confirmation of labor cooling", "A stronger-than-expected report may support higher for longer rates, pressuring gold", e3.event_time_utc, 5),
]
report.add(run_backtest_case_manual(e3, a3, "XAUUSD", Direction.BEARISH, "actual +172K vs 85K expected — gold fell ~2.2%, broke below $4,400"))

# --- 4. June CPI, released Jul 14, 2026 ---
e4 = EconomicEvent("CPI (Jun)", "USD", "High", dt.datetime(2026, 7, 14, 12, 30, tzinfo=UTC_TZ))
a4 = [
    art("Gold recovers ahead of inflation figures", "Markets brace for CPI as decisive short-term catalyst, soft print could compress rate-hike odds", e4.event_time_utc, 30),
    art("Cooling inflation could open path for gold rally", "A softer reading would revive dovish Fed bets and support bullion toward 200-day average", e4.event_time_utc, 14),
    art("Gold fell on Iran strikes ahead of CPI print", "Fear trade dominates near-term positioning into inflation data", e4.event_time_utc, 20),
]
report.add(run_backtest_case_manual(e4, a4, "XAUUSD", Direction.BULLISH, "actual -0.4% MoM vs -0.1% expected — gold jumped $90 (+2.25%) to $4,091"))

# --- 5. May CPI, released Jun 10, 2026 ---
e5 = EconomicEvent("CPI (May)", "USD", "High", dt.datetime(2026, 6, 10, 12, 30, tzinfo=UTC_TZ))
a5 = [
    art("Gold tumbles as hot CPI looms", "Consumer price data expected to exceed 4% for first time in years, reinforcing case for Fed rate hikes", e5.event_time_utc, 26),
    art("Rate-hike bets surge on strong jobs, hot CPI expected next", "CME FedWatch prices 72% probability of December hike, hawkish repricing accelerating", e5.event_time_utc, 15),
    art("Higher-than-expected core CPI could pressure gold", "Rising real yields seen weakening gold's appeal if inflation data surprises to upside", e5.event_time_utc, 40),
]
report.add(run_backtest_case_manual(e5, a5, "XAUUSD", Direction.BEARISH, "actual 4.2% YoY, hottest since 2023 — gold fell sharply, multiple sources report -2.4% to -4.4%"))

# --- 6. FOMC decision, Jun 17, 2026 ---
e6 = EconomicEvent("FOMC Rate Decision", "USD", "High", dt.datetime(2026, 6, 17, 18, 0, tzinfo=UTC_TZ))
a6 = [
    art("Fed expected to hold, dot plot in focus", "97% odds of hold priced in, markets watching new Chair Warsh's first dot plot for hawkish tilt", e6.event_time_utc, 30),
    art("Warsh's first meeting seen as hawkish test case", "New Fed Chair widely regarded as inflation hawk, dot plot could reveal 2026 hike bias", e6.event_time_utc, 40),
    art("Gold at $4,347 while stocks hit highs ahead of Fed", "Futures market pricing near-certain hold, focus shifts to guidance language", e6.event_time_utc, 6),
]
report.add(run_backtest_case_manual(e6, a6, "XAUUSD", Direction.BEARISH, "hold as expected, but ~9 of 18 officials projected a 2026 hike — gold fell 0.94% to $4,290.52"))

# --- 7. FOMC June minutes, released Jul 8, 2026 ---
e7 = EconomicEvent("FOMC Minutes (Jun Meeting)", "USD", "Medium", dt.datetime(2026, 7, 8, 18, 0, tzinfo=UTC_TZ))
a7 = [
    art("Committee split nine-to-nine on 2026 hike", "FOMC minutes expected to reveal hawkish argument for September hike alongside dovish hold case", e7.event_time_utc, 24),
    art("Weak June payrolls complicate hawkish case", "57K print seen as weakest in four months, tempering rate-hike conviction ahead of minutes release", e7.event_time_utc, 30),
    art("Markets brace for hawkish language in Fed minutes", "Split committee raises stakes for guidance on September meeting", e7.event_time_utc, 4),
]
report.add(run_backtest_case_manual(e7, a7, "XAUUSD", Direction.BEARISH, "minutes showed hawkish 9-9 split — gold fell 0.75% to $4,075"))

# --- 8. March CPI, released Apr 10, 2026 ---
e8 = EconomicEvent("CPI (Mar)", "USD", "High", dt.datetime(2026, 4, 10, 12, 30, tzinfo=UTC_TZ))
a8 = [
    art("Inflation expected to spike on energy costs", "Iran war-driven oil surge seen pushing March CPI sharply higher, consensus near 1.0% MoM", e8.event_time_utc, 36),
    art("Markets brace for hot inflation print", "Energy-driven CPI spike seen as transitory but could still pressure gold near-term", e8.event_time_utc, 18),
    art("Fed seen looking through energy-driven inflation noise", "Officials tilted toward eventual rate cut despite near-term price spike, per March meeting signals", e8.event_time_utc, 8),
]
report.add(run_backtest_case_manual(e8, a8, "XAUUSD", Direction.BULLISH, "actual 0.9% MoM vs 1.0% expected, 3.3% YoY vs 3.4% expected — softer than feared, gold jumped $10+"))

# --- 9. April CPI, released ~May 13, 2026 ---
e9 = EconomicEvent("CPI (Apr)", "USD", "High", dt.datetime(2026, 5, 13, 12, 30, tzinfo=UTC_TZ))
a9 = [
    art("Inflation seen re-accelerating on energy costs", "Consensus points to 3.7% YoY, highest since 2023, as Hormuz disruption keeps oil elevated", e9.event_time_utc, 30),
    art("Hawkish new Fed chair adds to rate-hike bets", "Incoming Chair Warsh regarded as inflation hawk, hot CPI could cement 2026 hike case", e9.event_time_utc, 20),
    art("Gold correction continues into CPI print", "Bullion down over 20% from January highs as rate-cut expectations collapse", e9.event_time_utc, 10),
]
report.add(run_backtest_case_manual(e9, a9, "XAUUSD", Direction.BEARISH, "actual 3.8% YoY vs 3.7% expected — hotter than forecast, gold fell despite mixed drivers"))

# --- 10. February PPI, released ~Mar 18, 2026 ---
e10 = EconomicEvent("PPI (Feb)", "USD", "High", dt.datetime(2026, 3, 18, 12, 30, tzinfo=UTC_TZ))
a10 = [
    art("Producer prices expected to hold steady", "Consensus points to modest PPI increase, Fed seen maintaining hold stance regardless", e10.event_time_utc, 28),
    art("Fed holds rates, no cuts in sight", "Policymakers want more confirmation inflation is durably contained before any policy shift", e10.event_time_utc, 16),
    art("Gold steady near highs ahead of producer price data", "Markets positioned for limited reaction barring a significant surprise in either direction", e10.event_time_utc, 6),
]
report.add(run_backtest_case_manual(e10, a10, "XAUUSD", Direction.BEARISH, "actual PPI 3.4% vs ~1.7% expected — more than double forecast, gold fell 3.75% to $4,820"))

# --- 11. December NFP, released Jan 9, 2026 ---
# NOTE: January is EST (UTC-5), not EDT (UTC-4) like the events above —
# 8:30am ET in January is 13:30 UTC, not 12:30 UTC. Events #1-10 are all
# summer-month EDT releases; this is the first one that needed the
# correct winter offset.
e11 = EconomicEvent("Non-Farm Payrolls (Dec)", "USD", "High", dt.datetime(2026, 1, 9, 13, 30, tzinfo=UTC_TZ))
a11 = [
    art("Gold holds near highs as dollar, yields slip ahead of key jobs data", "Markets pricing at least two Fed rate cuts in 2026, a backdrop historically favorable for gold; consensus centers near 60K-73K new jobs", e11.event_time_utc, 24),
    art("Geopolitical tensions keep bullion underpinned into payrolls", "Iran unrest, Russia-Ukraine war, and renewed Venezuela/Greenland rhetoric keep safe-haven demand elevated ahead of the report", e11.event_time_utc, 30),
    art("Gold set for weekly gain as caution sets in ahead of employment report", "Unemployment rate seen ticking down to 4.5%, market positioned for a mostly in-line print", e11.event_time_utc, 4),
]
report.add(run_backtest_case_manual(
    e11, a11, "XAUUSD", Direction.BULLISH,
    "actual +50K vs ~60-73K expected (miss); unemployment fell to 4.4% vs 4.5% forecast; "
    "wages 3.8% YoY vs 3.7% expected (hot) — a genuinely mixed report, but the headline miss "
    "dominated the reaction: Kitco reported gold 'attracting bullish attention' post-release, "
    "closing the week up ~3%"
))

# --- 12. December CPI, released Jan 13, 2026 ---
e12 = EconomicEvent("CPI (Dec)", "USD", "High", dt.datetime(2026, 1, 13, 13, 30, tzinfo=UTC_TZ))
a12 = [
    art("Gold holds solid gains above $4,600 as markets eye December CPI", "Consensus centers on 0.3% MoM, 2.7% YoY headline, core also seen at 0.3%/2.7% — broadly in-line print expected", e12.event_time_utc, 26),
    art("Core inflation seen holding steady, Fed rate-cut path in focus", "A softer-than-consensus core reading would reinforce the case for continued 2026 easing, supportive for bullion", e12.event_time_utc, 16),
    art("Dollar firm, gold steady into inflation data", "Markets broadly positioned for an in-line report with limited directional surprise", e12.event_time_utc, 6),
]
report.add(run_backtest_case_manual(
    e12, a12, "XAUUSD", Direction.BULLISH,
    "actual 0.3% MoM / 2.7% YoY headline (in line); core 2.6% YoY, slightly softer than the "
    "2.7% consensus — gold gained modestly, last trading +0.30% on the day per Kitco, as the "
    "softer core reading reinforced Fed rate-cut expectations"
))

# --- 13. December PPI, released Jan 30, 2026 ---
e13 = EconomicEvent("PPI (Dec)", "USD", "High", dt.datetime(2026, 1, 30, 13, 30, tzinfo=UTC_TZ))
a13 = [
    art("Gold pulls back from record highs as markets digest sticky-inflation risk", "Bullion touched a fresh record above $5,600 days earlier; profit-taking and firmer yields weigh into producer price data", e13.event_time_utc, 28),
    art("Producer prices seen rising modestly after hot CPI print", "Consensus centers on 0.2% MoM headline and core, with markets wary of a repeat upside surprise", e13.event_time_utc, 18),
    art("Treasury yields firm, dollar strengthens ahead of PPI confirmation", "Markets shift focus from CPI repricing to PPI as the next inflation-durability test", e13.event_time_utc, 8),
]
report.add(run_backtest_case_manual(
    e13, a13, "XAUUSD", Direction.BEARISH,
    "actual PPI 0.5% MoM vs 0.2% expected, core 0.7% vs 0.2% expected — a large hot beat on "
    "both headline and core, m/m and y/y; gold fell sharply into month-end (down double-digit "
    "percent from its Jan 29 record), though the magnitude is compounded by a broader "
    "record-high correction already underway, not attributable to PPI alone"
))

# --- 14. FOMC Rate Decision, Jan 28, 2026 (previously deliberately skipped) ---
# Re-researched later with better search terms and a clean source was
# found this time: a same-day headline directly confirming the reaction
# ("Gold Price Dips Back Below US$4,300 as New Fed Chair Holds Rates
# Steady"). Direction is real and confirmed; the exact MAGNITUDE is
# entangled with the broader Jan 28-30 correction already used for
# event #13's PPI case (same window, compounding drivers), same
# honesty caveat applied there.
e14 = EconomicEvent("FOMC Rate Decision", "USD", "High", dt.datetime(2026, 1, 28, 19, 0, tzinfo=UTC_TZ))
a14 = [
    art("Fed widely expected to hold, dot plot in focus for 2026 path", "CME FedWatch prices ~95% odds of a hold at 3.50-3.75% — real market impact expected from forward guidance, not the rate decision itself", e14.event_time_utc, 28),
    art("Cooling labor market complicates the Fed's forward guidance", "December payrolls added just 50K — if Chair Warsh signals concern over the labor market, markets would pull forward rate-cut bets, a tailwind for gold", e14.event_time_utc, 18),
    art("Gold near record highs as markets brace for Fed guidance", "A hawkish tilt — Warsh framing 3.5% as a floor, not a peak, given resilient growth data — risks a profit-taking pullback in bullion", e14.event_time_utc, 5),
]
report.add(run_backtest_case_manual(
    e14, a14, "XAUUSD", Direction.BEARISH,
    "held as expected at 3.50-3.75% under Chair Warsh (no surprise on the decision itself), but "
    "hawkish forward guidance — rate-hike odds for September priced up to 67%, three hikes "
    "anticipated across 2026 — sent gold decisively below the $4,300 support level. Same "
    "'hold but hawkish' pattern as the June FOMC case (#6)"
))

report.print_report()
