// webapp/static/js/stats/reaction.test.js
import test from "node:test";
import assert from "node:assert/strict";
import {
  CREDIT_LABELS, leaderboardRowsHtml, leaderboardHeadHtml, releasesHtml, clusterNoteHtml, reactionDisclaimersHtml,
  reactionEmptyHtml, instrumentOptionsHtml,
} from "./reaction.js";

const rate = (k, n, percent = null, interval = [0.4385, 1.0]) => ({ k, n, percent, interval, few: n < 8 });
const ROW = {
  event_title: "CPI m/m", impact_effective: "High", impact_inferred: false, releases: 9, solo: 3, shared: 1, in_conflict: 3,
  reaction: rate(7, 9), hit: rate(5, 7), avg_move_pct: 0.2, engine: { k: 1, n: 2 }, few: false,
};

// ---- leaderboard ------------------------------------------------------------------

test("a row shows 'k of n' and no percent when the service gives none", () => {
  const html = leaderboardRowsHtml([ROW]);
  assert.ok(html.includes("7 of 9"));
  assert.ok(!html.includes("7 of 9 ("));
  assert.ok(!/\d%\)/.test(html));
});

test("a row shows the percent and the Wilson interval as a hover title when the service gives a percent", () => {
  const row = { ...ROW, releases: 40, reaction: rate(30, 40, 75, [0.5, 0.9]) };
  const html = leaderboardRowsHtml([row]);
  assert.ok(html.includes("30 of 40 (75%)"));
  assert.ok(html.includes('title="95% interval 50%-90%"'));
});

test("the interval title is also on a rate whose percent is hidden", () => {
  assert.ok(leaderboardRowsHtml([ROW]).includes('title="95% interval 44%-100%"'));
});

test("the sub-line carries the exact 'of the N that moved' wording with solo / shared / in conflict", () => {
  const html = leaderboardRowsHtml([ROW]);
  assert.ok(html.includes("of the 7 that moved: 5 went the implied way (solo 3, shared 1, in conflict 3)"));
});

test("the hit-rate percent appears only when the service gives one, with its interval as a title", () => {
  assert.ok(!leaderboardRowsHtml([ROW]).includes("hit-rate"));
  const row = { ...ROW, hit: rate(18, 25, 72, [0.52, 0.86]) };
  const html = leaderboardRowsHtml([row]);
  assert.ok(/<span class="hit-rate" title="95% interval 52%-86%">72%<\/span>/.test(html));
});

test("'few releases' tag only when few is true", () => {
  assert.ok(leaderboardRowsHtml([{ ...ROW, few: true }]).includes("few releases"));
  assert.ok(!leaderboardRowsHtml([ROW]).includes("few releases"));
});

test("Impact shows the effective level, with ' (inferred)' only when inferred", () => {
  assert.ok(leaderboardRowsHtml([ROW]).includes("<td>High</td>"));
  assert.ok(leaderboardRowsHtml([{ ...ROW, impact_inferred: true }]).includes("<td>High (inferred)</td>"));
});

test("average move is a signed percent with 2 decimals, or '-' when null", () => {
  assert.ok(leaderboardRowsHtml([ROW]).includes("+0.20%"));
  assert.ok(leaderboardRowsHtml([{ ...ROW, avg_move_pct: -0.254 }]).includes("-0.25%"));
  assert.ok(leaderboardRowsHtml([{ ...ROW, avg_move_pct: null }]).includes(">-</td>"));
});

test("engine call right is 'k of n' or 'n/a'", () => {
  assert.ok(leaderboardRowsHtml([ROW]).includes("<td>1 of 2</td>"));
  assert.ok(leaderboardRowsHtml([{ ...ROW, engine: null }]).includes("<td>n/a</td>"));
});

test("rows are clickable and keyboard accessible", () => {
  const html = leaderboardRowsHtml([ROW]);
  assert.ok(html.includes('class="row-click"') && html.includes('tabindex="0"'));
  assert.ok(html.includes('data-reaction-event="CPI m/m"'));
});

test("event titles are escaped in the leaderboard", () => {
  const html = leaderboardRowsHtml([{ ...ROW, event_title: '<img src=x onerror="a">' }]);
  assert.ok(!html.includes("<img") && html.includes("&lt;img"));
  assert.ok(!html.includes('onerror="a"'));
});

test("no rows gives the empty-state row", () => {
  assert.ok(leaderboardRowsHtml([]).includes("No releases match this selection."));
  assert.ok(reactionEmptyHtml().includes("No releases match this selection."));
});

test("the header carries the chance-level note (25% for the 75th percentile baseline)", () => {
  const head = leaderboardHeadHtml(0.75);
  for (const col of ["Event", "Impact", "Releases", "Moved the market", "Avg 5-min move", "Engine call right"]) {
    assert.ok(head.includes(col), col);
  }
  assert.ok(head.includes("Chance level for an ordinary window is 25%"));
  assert.ok(leaderboardHeadHtml(undefined).includes("Chance level for an ordinary window is 25%"));
});

test("both exact disclaimers are shown, escaped", () => {
  const html = reactionDisclaimersHtml({ association: "A <b>one</b>", cluster: "Credit in a cluster is shared or matched, never exclusive." });
  assert.ok(html.includes("Credit in a cluster is shared or matched, never exclusive.") && html.includes("A &lt;b&gt;one&lt;/b&gt;"));
  assert.equal(reactionDisclaimersHtml(null), "");
});

test("instrument options are selected by value, not by index", () => {
  const html = instrumentOptionsHtml(["US30", "XAUUSD"], "XAUUSD");
  assert.ok(/<option value="XAUUSD" selected>/.test(html));
  assert.ok(!/<option value="US30" selected>/.test(html));
  assert.ok(!instrumentOptionsHtml(["<x>"], "<x>").includes("<x>"));
});

// ---- drill-down -------------------------------------------------------------------

const REL = {
  event_time_utc: "2026-03-03T12:30:00+00:00", move: -4.0, move_pct: -0.2, threshold: 1.0, reaction: "sell", lean: "sell",
  credit: "matched", cluster_size: 2, hidden_in_cluster: 0,
  cluster: [
    { event_title: "CPI m/m", lean: "sell", credit: "matched", impact_effective: "High" },
    { event_title: "Unemployment Claims", lean: "buy", credit: "overruled", impact_effective: "Low" },
  ],
  engine_call: null, note: null,
};
const DATA = { event_title: "CPI m/m", instrument: "XAUUSD", releases: [REL] };

test("every credit label", () => {
  assert.deepEqual(CREDIT_LABELS, {
    solo_hit: "Solo hit", solo_miss: "Solo miss", shared_hit: "Shared driver", shared_miss: "Shared miss",
    matched: "Matched the move", overruled: "Overruled", no_reaction: "No reaction", no_signal: "No signal", no_data: "No data",
  });
  for (const [key, label] of Object.entries(CREDIT_LABELS)) {
    assert.ok(releasesHtml({ ...DATA, releases: [{ ...REL, credit: key, cluster: [] }] }).includes(label), key);
  }
});

test("the drill-down shows the move, the typical threshold, the reaction and the implied lean", () => {
  const html = releasesHtml(DATA);
  assert.ok(html.includes("-0.20%") && html.includes("-4.00") && html.includes("typical 1.00"));
  assert.ok(html.includes("<td>Sell</td>"));
  assert.ok(html.includes("potential SELL-OFF"));
});

test("reaction wording: Buy / Sell / No reaction / No data, and a missing move shows '-'", () => {
  const cell = (over) => releasesHtml({ ...DATA, releases: [{ ...REL, cluster: [], credit: "solo_hit", ...over }] });
  assert.ok(cell({ reaction: "buy", move: 5, move_pct: 0.25 }).includes("<td>Buy</td>"));
  assert.ok(cell({ reaction: "none", credit: "no_reaction" }).includes("<td>No reaction</td>"));
  const nodata = cell({ reaction: null, move: null, move_pct: null, threshold: null, credit: "no_data" });
  assert.ok(nodata.includes("<td>No data</td>") && !nodata.includes("typical"));
});

test("implied lean wording: BUY / SELL-OFF / no clear lean", () => {
  const lean = (l) => releasesHtml({ ...DATA, releases: [{ ...REL, lean: l, cluster: [] }] });
  assert.ok(lean("buy").includes("potential BUY") && lean("sell").includes("potential SELL-OFF"));
  assert.ok(lean("mixed").includes("no clear lean"));
});

test("the date is SAST: 23:00Z rolls over to the next day", () => {
  const html = releasesHtml({ ...DATA, releases: [{ ...REL, event_time_utc: "2026-03-03T23:00:00+00:00", cluster: [] }] });
  assert.ok(html.includes("2026-03-04 01:00"));
  assert.ok(!html.includes("2026-03-03"));
});

test("the cluster lists the other events with their lean and credit", () => {
  const html = releasesHtml(DATA);
  assert.ok(html.includes("Unemployment Claims") && html.includes("Overruled"));
  assert.ok(html.includes("potential BUY"));
});

test("clusterNoteHtml: other events only when an own title is given, and the hidden-in-cluster note", () => {
  const all = clusterNoteHtml(REL);
  assert.ok(all.includes("CPI m/m") && all.includes("Unemployment Claims"));
  const others = clusterNoteHtml(REL, "CPI m/m");
  assert.ok(!others.includes("CPI m/m") && others.includes("Unemployment Claims"));
  const hidden = clusterNoteHtml({ ...REL, hidden_in_cluster: 3 }, "CPI m/m");
  assert.ok(hidden.includes("+3 lower-impact events at the same time"));
  assert.ok(!clusterNoteHtml(REL, "CPI m/m").includes("lower-impact"));
});

test("a lone release has no cluster text", () => {
  assert.equal(clusterNoteHtml({ ...REL, cluster: [REL.cluster[0]], cluster_size: 1 }, "CPI m/m"), "");
});

test("the overlap note is shown", () => {
  assert.ok(clusterNoteHtml({ ...REL, cluster: [], note: "another release 4 min later" }, "CPI m/m").includes("another release 4 min later"));
});

test("engine call shows the method and a Right/Wrong chip, or '-'", () => {
  const eng = (engine_call) => releasesHtml({ ...DATA, releases: [{ ...REL, cluster: [], engine_call }] });
  const right = eng({ method: "combined", verdict: "right" });
  assert.ok(right.includes("Combined") && right.includes("chip-right") && right.includes("Right"));
  assert.ok(eng({ method: "tier1", verdict: "wrong" }).includes("chip-wrong"));
  assert.ok(eng(null).includes("<td>-</td>"));
});

test("titles in the drill-down and in the cluster are escaped", () => {
  const evil = "<script>alert(1)</script>";
  const html = releasesHtml({
    event_title: evil, instrument: "XAUUSD",
    releases: [{ ...REL, cluster: [{ event_title: evil, lean: "buy", credit: "overruled", impact_effective: "<b>" }] }],
  });
  assert.ok(!html.includes("<script>") && !html.includes("<b>"));
  assert.ok(html.includes("&lt;script&gt;"));
});

test("a drill-down with no releases shows the empty state", () => {
  assert.ok(releasesHtml({ ...DATA, releases: [] }).includes("No releases match this selection."));
});

test("releases are listed in the order given (the service sends newest first)", () => {
  const a = { ...REL, event_time_utc: "2026-04-07T12:30:00+00:00", cluster: [] };
  const b = { ...REL, event_time_utc: "2026-03-03T12:30:00+00:00", cluster: [] };
  const html = releasesHtml({ ...DATA, releases: [a, b] });
  assert.ok(html.indexOf("2026-04-07") < html.indexOf("2026-03-03"));
});
