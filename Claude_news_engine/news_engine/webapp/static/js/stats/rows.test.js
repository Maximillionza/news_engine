// webapp/static/js/stats/rows.test.js
import test from "node:test";
import assert from "node:assert/strict";
import {
  tier1RowHtml, combinedRowHtml, sentimentRowHtml, verdictChip, leanText,
  pickNextRow, briefCardHtml, scoreboardHtml, filterRows, yearsPresent, disclaimerHtml, componentFor, orderTier1,
  toSast, emptyRowHtml, tier1BodyHtml,
} from "./rows.js";

const base = { event_title: "CPI m/m", event_time_utc: "2026-10-14T12:30:00+00:00", forecast: 0.3, forecast_text: "0.3%",
  actual: 0.4, actual_text: "0.4%", status: "scored", tier1_tracked: true, nowcast_as_of_utc: "2026-10-12T06:06:00+00:00",
  pre_news_period: false, news: null, combined: null,
  tier1: { predicted: 0.4, verdict: "right", miss: 0, leans: { XAUUSD: "sell", US30: "sell" }, note: null, kind: "reconstructed" } };

const DISC = { pre_news: "PRE", reconstructed: "RECON", typical_reaction: "Typical reaction, not a trade signal." };

test("a tracked row shows the call, a Right chip and the reconstructed tag", () => {
  const html = tier1RowHtml(base);
  assert.ok(html.includes("Right") && html.includes("reconstructed"));
  assert.ok(html.includes("potential SELL-OFF"));
});

test("an untracked row is greyed with the not-tracked message", () => {
  const html = tier1RowHtml({ ...base, tier1_tracked: false, tier1: null });
  assert.ok(html.includes("row-off") && html.includes("Not tracked by Tier 1"));
});

test("a pending row shows pending and no verdict chip", () => {
  const html = tier1RowHtml({ ...base, status: "pending", actual_text: null, tier1: { ...base.tier1, verdict: null } });
  assert.ok(html.includes("pending") && !html.includes("chip-right"));
});

test("a not-scoreable row says so", () => {
  assert.ok(tier1RowHtml({ ...base, status: "not_scoreable", tier1: null, tier1_tracked: false }).includes("No forecast"));
});

test("verdictChip escapes unknown input and handles null", () => {
  assert.ok(verdictChip("right").includes("Right") && verdictChip("wrong").includes("Wrong"));
  assert.ok(verdictChip(null).includes("No call"));
  assert.ok(!verdictChip("<script>").includes("<script>"));
});

test("event text is escaped", () => {
  assert.ok(!tier1RowHtml({ ...base, event_title: "<script>x</script>" }).includes("<script>"));
});

test("leanText maps each lean and falls back to no clear lean", () => {
  assert.equal(leanText({ XAUUSD: "buy" }), "XAUUSD 🟢 potential BUY");
  assert.ok(leanText({ US30: "weird" }).includes("no clear lean"));
  assert.equal(leanText(null), "");
});

test("componentFor: CPI family and any row with a kind open the nowcast breakdown; untracked rows open nothing", () => {
  assert.equal(componentFor(base), "cleveland_nowcast");
  assert.equal(componentFor({ ...base, event_title: "Core CPI m/m", tier1: { ...base.tier1, kind: null } }), "cleveland_nowcast");
  assert.equal(componentFor({ ...base, event_title: "PPI m/m", tier1: { ...base.tier1, kind: null } }), null);
  assert.equal(componentFor({ ...base, event_title: "PPI m/m", tier1: { ...base.tier1, kind: "live" } }), "cleveland_nowcast");
  assert.equal(componentFor({ ...base, tier1_tracked: false, tier1: null }), null);
  assert.equal(componentFor({ ...base, tier1: null }), "cleveland_nowcast");   // tracked CPI with no stored call
});

test("a tracked row with no recorded call says so, is not greyed as untracked, and still opens the breakdown", () => {
  const html = tier1RowHtml({ ...base, tier1: null });
  assert.ok(html.includes("no call") && html.includes("No call") && !html.includes("Not tracked"));
  assert.ok(html.includes('data-component="cleveland_nowcast"'));
});

test("a clickable tier-1 row carries its metric; an untracked row is not clickable", () => {
  assert.ok(tier1RowHtml(base).includes('data-component="cleveland_nowcast"'));
  const off = tier1RowHtml({ ...base, tier1_tracked: false, tier1: null });
  assert.ok(!off.includes("data-component") && !off.includes("row-click"));
});

test("combined row shows all three calls, and flags Tier 1 only when news is missing", () => {
  const row = { ...base, news: null, combined: { predicted: 0.4, verdict: "right", note: "news_missing", leans: {}, kind: null } };
  const html = combinedRowHtml(row);
  assert.ok(html.includes("Tier 1 only") && html.includes("Right"));
  assert.ok(combinedRowHtml({ ...base, tier1_tracked: false, tier1: null }).includes("n/a"));
});

test("sentiment row: no news before the news start says so; a call shows its lean", () => {
  assert.ok(sentimentRowHtml({ ...base, pre_news_period: true }).includes("No articles before 12 Aug 2026"));
  assert.ok(sentimentRowHtml({ ...base }).includes("No news call"));
  const html = sentimentRowHtml({ ...base, news: { predicted: 0.35, verdict: "wrong", leans: { XAUUSD: "buy" }, note: null, kind: null } });
  assert.ok(html.includes("0.35") && html.includes("Wrong") && html.includes("potential BUY"));
});

// ---- next-release brief card -------------------------------------------------
const NOW = new Date("2026-10-15T08:00:00Z");
const pend = (title, time, extra = {}) => ({ ...base, event_title: title, event_time_utc: time, status: "pending", actual: null,
  actual_text: null, tier1: { predicted: 0.5, verdict: null, miss: null, leans: { XAUUSD: "sell" }, note: null, kind: "live" }, ...extra });

test("pickNextRow picks the soonest future pending row that has a call", () => {
  const rows = [
    pend("A", "2026-10-20T12:30:00+00:00"),
    pend("B", "2026-10-16T12:30:00+00:00"),
    pend("C", "2026-10-17T12:30:00+00:00"),
  ];
  assert.equal(pickNextRow(rows, NOW, "tier1").event_title, "B");
});

test("pickNextRow ignores past pending rows, scored rows and rows without a call", () => {
  const rows = [
    pend("past", "2026-10-14T12:30:00+00:00"),
    { ...base, event_time_utc: "2026-10-16T12:30:00+00:00" },                    // scored, not pending
    pend("nocall", "2026-10-16T13:30:00+00:00", { tier1: null }),
    pend("nopred", "2026-10-16T14:30:00+00:00", { tier1: { predicted: null, leans: {}, kind: null } }),
    pend("later", "2026-10-18T12:30:00+00:00"),
  ];
  assert.equal(pickNextRow(rows, NOW, "tier1").event_title, "later");
});

test("pickNextRow uses the sub-tab's own method and returns null when nothing qualifies", () => {
  assert.equal(pickNextRow([pend("A", "2026-10-20T12:30:00+00:00")], NOW, "news"), null);
  assert.equal(pickNextRow([], NOW, "combined"), null);
});

test("brief card shows name, SAST time, expected direction, number, lean and the disclaimer", () => {
  const html = briefCardHtml(pend("CPI m/m", "2026-10-16T12:30:00+00:00"), "tier1", DISC);
  assert.ok(html.includes("CPI m/m"));
  assert.ok(html.includes("2026-10-16 14:30 SAST"));                 // UTC+2
  assert.ok(html.includes("hotter than consensus"));                 // 0.5 vs 0.3
  assert.ok(html.includes("0.5") && html.includes("potential SELL-OFF"));
  assert.ok(html.includes("Typical reaction, not a trade signal."));
});

test("brief card: cooler, and in line within one published step of the forecast", () => {
  const cool = briefCardHtml(pend("CPI m/m", "2026-10-16T12:30:00+00:00", { tier1: { predicted: 0.1, leans: {}, kind: "live" } }), "tier1", DISC);
  assert.ok(cool.includes("cooler than consensus"));
  const flat = briefCardHtml(pend("CPI m/m", "2026-10-16T12:30:00+00:00", { tier1: { predicted: 0.34, leans: {}, kind: "live" } }), "tier1", DISC);
  assert.ok(flat.includes("in line with consensus"));
});

test("brief card with no row says there is no upcoming call, and escapes the title", () => {
  assert.ok(briefCardHtml(null, "combined", DISC).includes("No upcoming call yet."));
  assert.ok(!briefCardHtml(pend("<script>", "2026-10-16T12:30:00+00:00"), "tier1", DISC).includes("<script>"));
});

// ---- scoreboard, filters, disclaimers ---------------------------------------
const SB = { methods: {
  tier1: { scored: 8, right: 5, accuracy: 0.625, accuracy_shown: false, mean_miss: 0.123456 },
  news: { scored: 25, right: 15, accuracy: 0.6, accuracy_shown: true, mean_miss: null },
  combined: { scored: 0, right: 0, accuracy: null, accuracy_shown: false, mean_miss: null } },
  min_for_percent: 20, footnote: "Weights fixed at 70/30 until the 2027-01-15 review." };

test("scoreboard shows 'k of n', a percentage only when allowed, mean miss to 2dp with the unit, and the footnote", () => {
  const html = scoreboardHtml(SB, "%");
  assert.ok(html.includes("5 of 8") && !html.includes("63%"));
  assert.ok(html.includes("15 of 25 (60%)"));
  assert.ok(html.includes("0.12%") && !html.includes("0.123"));
  assert.ok(html.includes("Weights fixed at 70/30"));
  assert.ok(html.includes("0 of 0"));
});

test("filterRows and yearsPresent", () => {
  const rows = [base, { ...base, event_title: "NFP", event_time_utc: "2027-01-08T13:30:00+00:00" }];
  assert.deepEqual(yearsPresent(rows), [2026, 2027]);
  assert.equal(filterRows(rows, { year: 2027 }).length, 1);
  assert.equal(filterRows(rows, { month: 10 }).length, 1);
  assert.equal(filterRows(rows, { event: "CPI m/m" }).length, 1);
  assert.equal(filterRows(rows, {}).length, 2);
});

test("pre-news disclaimer shows on News/Combined only, when the range includes a pre-news row", () => {
  const rows = [{ ...base, pre_news_period: true }];
  assert.ok(disclaimerHtml(rows, "news", DISC).includes("PRE"));
  assert.ok(disclaimerHtml(rows, "combined", DISC).includes("PRE"));
  assert.ok(!disclaimerHtml(rows, "tier1", DISC).includes("PRE"));
  assert.ok(!disclaimerHtml([base], "news", DISC).includes("PRE"));
});

test("reconstructed disclaimer shows once under the Tier 1 table when a reconstructed row is present", () => {
  assert.equal((disclaimerHtml([base, base], "tier1", DISC).match(/RECON/g) || []).length, 1);
  assert.ok(!disclaimerHtml([{ ...base, tier1: { ...base.tier1, kind: "live" } }], "tier1", DISC).includes("RECON"));
});

test("orderTier1 puts tracked events first, newest first within each group", () => {
  const rows = [
    { ...base, event_title: "old tracked", event_time_utc: "2026-01-01T00:00:00+00:00" },
    { ...base, event_title: "new untracked", tier1_tracked: false, event_time_utc: "2026-10-01T00:00:00+00:00" },
    { ...base, event_title: "new tracked", event_time_utc: "2026-09-01T00:00:00+00:00" },
  ];
  assert.deepEqual(orderTier1(rows).map((r) => r.event_title), ["new tracked", "old tracked", "new untracked"]);
});

// ---- SAST display ------------------------------------------------------------
test("toSast adds two hours and rolls the date over after 22:00 UTC", () => {
  assert.deepEqual(toSast("2026-10-14T12:30:00+00:00"), { date: "2026-10-14", time: "14:30" });
  assert.deepEqual(toSast("2026-10-14T23:00:00+00:00"), { date: "2026-10-15", time: "01:00" });
});

test("table dates and the nowcast 'as of' text are shown in SAST", () => {
  const late = { ...base, event_time_utc: "2026-10-14T23:00:00+00:00", nowcast_as_of_utc: "2026-10-12T23:30:00+00:00" };
  const html = tier1RowHtml(late);
  assert.ok(html.includes("2026-10-15") && !html.includes("2026-10-14"));
  assert.ok(html.includes("nowcast as of 2026-10-13 01:30 SAST") && !html.includes("UTC"));
  assert.ok(combinedRowHtml(late).includes("2026-10-15"));
  assert.ok(sentimentRowHtml({ ...late, news: null }).includes("2026-10-15"));
});

test("brief card time still uses the same SAST conversion", () => {
  assert.ok(briefCardHtml(pend("CPI m/m", "2026-10-16T23:00:00+00:00"), "tier1", DISC).includes("2026-10-17 01:00 SAST"));
});

// ---- empty state and Tier 1 grouping ------------------------------------------
test("emptyRowHtml spans the table and says nothing matches", () => {
  const html = emptyRowHtml(7);
  assert.ok(html.includes('colspan="7"') && html.includes("No releases match this selection."));
});

test("tier1BodyHtml shows the empty message when there are no rows", () => {
  assert.ok(tier1BodyHtml([]).includes("No releases match this selection."));
});

test("tier1BodyHtml groups tracked first under captions, chronological newest first inside each", () => {
  const rows = [
    { ...base, event_title: "old tracked", event_time_utc: "2026-01-01T12:00:00+00:00" },
    { ...base, event_title: "new untracked", tier1_tracked: false, tier1: null, event_time_utc: "2026-10-01T12:00:00+00:00" },
    { ...base, event_title: "new tracked", event_time_utc: "2026-09-01T12:00:00+00:00" },
  ];
  const html = tier1BodyHtml(rows);
  const at = (t) => html.indexOf(t);
  assert.ok(at("Tracked by Tier 1") < at("new tracked") && at("new tracked") < at("old tracked"));
  assert.ok(at("old tracked") < at('Not tracked by Tier 1</th>') && at('Not tracked by Tier 1</th>') < at("new untracked"));
});

test("tier1BodyHtml omits a caption for an empty group", () => {
  const html = tier1BodyHtml([{ ...base }]);
  assert.ok(html.includes("Tracked by Tier 1") && !html.includes("Not tracked by Tier 1</th>"));
});
