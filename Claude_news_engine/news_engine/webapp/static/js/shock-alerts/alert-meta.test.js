// webapp/static/js/shock-alerts/alert-meta.test.js
import test from "node:test";
import assert from "node:assert/strict";
import { freshnessText, contextTagsText, capBadgeHtml, incidentLabelText } from "./alert-meta.js";

const OLD_ROW = {
  first_published_utc: null, age_minutes: null, freshness_band: null,
  country: null, us_link: null, polarity: null,
  capped_no_us_link: null, original_severity: null, severity: "Medium",
};

test("freshness is shown in SAST with age and band", () => {
  const row = { first_published_utc: "2026-10-21T12:42:00+00:00", age_minutes: 2, freshness_band: "Fresh" };
  assert.equal(freshnessText(row), "Published 14:42 SAST · +2 min · Fresh");
});

test("old rows with null fields render nothing", () => {
  assert.equal(freshnessText(OLD_ROW), "");
  assert.equal(contextTagsText(OLD_ROW), "");
  assert.equal(capBadgeHtml(OLD_ROW), "");
});

test("context tags join known parts and turn underscores into spaces", () => {
  assert.equal(
    contextTagsText({ country: "RU", us_link: "none", polarity: "escalation" }),
    "Where: RU · US link: none · Polarity: escalation",
  );
  assert.equal(contextTagsText({ us_link: "global_supply" }), "US link: global supply");
});

test("cap badge mentions the classifier severity only when it differs", () => {
  const capped = { capped_no_us_link: true, original_severity: "High", severity: "Medium" };
  assert.match(capBadgeHtml(capped), /capped: no US or global-supply link/);
  assert.match(capBadgeHtml(capped), /\(classifier said High\)/);
  const same = { capped_no_us_link: true, original_severity: "Medium", severity: "Medium" };
  assert.ok(!capBadgeHtml(same).includes("classifier said"));
  assert.equal(capBadgeHtml({ capped_no_us_link: false, severity: "Medium" }), "");
});

test("injected markup in country is escaped", () => {
  const html = contextTagsText({ country: "<script>alert(1)</script>" });
  assert.ok(!html.includes("<script>"));
  assert.match(html, /&lt;script&gt;/);
});

test("incident labels name the incident, the rule and the push behaviour", () => {
  assert.equal(
    incidentLabelText({ id: 13, incident_id: 12, incident_role: "follow_up", incident_rule: "url" }),
    "Follow-up of incident #12 · same article URL · no push, no new lean");
  assert.equal(
    incidentLabelText({ id: 55, incident_id: 54, incident_role: "follow_up", incident_rule: "entity:saudi arabia" }),
    "Follow-up of incident #54 · shared: saudi arabia · no push, no new lean");
  assert.equal(
    incidentLabelText({ id: 39, incident_id: 33, incident_role: "update", incident_rule: "url" }),
    "Update to incident #33 · same article URL");
});

test("the first alert of an incident, and rows without the keys, get no label", () => {
  assert.equal(incidentLabelText({ id: 12, incident_id: 12, incident_role: null }), "");
  assert.equal(incidentLabelText({ id: 12 }), "");
});

test("incident label escapes the rule", () => {
  const out = incidentLabelText({ incident_id: 1, incident_role: "follow_up", incident_rule: "entity:<b>" });
  assert.ok(!out.includes("<b>"));
  assert.ok(out.includes("&lt;b&gt;"));
});
