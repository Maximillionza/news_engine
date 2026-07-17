# Clarifications for MiniMoney — supplied after direct user edits to BusinessCase_v5.md

> These are additional facts supplied by the user after directly hand-
> editing `BusinessCase_v5.md` (adding competitor references, a market-
> sizing statistic, concrete success-criteria figures, and a Freemium/
> paywall feature table, including a new "Fintech Advance" course for the
> 15-18 band). This clarification resolves one internal contradiction the
> Chief of Staff flagged in that hand-edited version and supplies rigorous,
> cited market research to replace the Incubator's own general-knowledge
> candidate content in Market & Competition. Not a pivot — the original
> premise is unchanged.

## Date
2026-07-06

## Important process note for the Incubator
`BusinessCase_v5.md` on disk was **hand-edited directly by the user**,
not produced or reconciled by the Incubator. It contains real, valuable
additions (competitor names, a market-sizing figure, concrete success-
criteria percentages, a Freemium/paywall feature table) alongside at
least one internal contradiction: the **Success Criteria** section (user-
edited) states the late-penalty caps at **7 Mbucks/week** (pilot cap: 3
Mbucks/week), while the **Operations** section (original Incubator v5
text, not touched by the user) still states the cap is **10 Mbucks/week**,
matching `Clarifications_v5.md`. This clarification resolves that
contradiction (see below) and should be reconciled consistently across
every section of the v6 Business Case that references the late-penalty
cap (Operations, Technology, Risks, Success Criteria, Outstanding
Questions, Assumptions).

## Raw clarification — market research (verbatim from user, with the
user's own confidence tags preserved as supplied)

Before we get to numbers: "how many minors have a device" is the wrong
first filter for a paid-adjacent app aimed at kids — the child isn't the
buyer. The gating variable is parent adoption and willingness-to-pay, and
that funnel is much narrower than device penetration.

**Population base (6-18):**
[Certain] Stats SA's mid-2025 estimate puts South Africa's total
population at 63.1 million, with children under 15 at 26.2% (≈16.5
million). [Guessing] Stats SA doesn't publish a clean 6-18 breakout, so
extrapolating from single-year cohort size (~1.1M/year under 15) and
adding the 15-18 band gives roughly 14-15 million people aged 6-18. This
is a modeled estimate, not a sourced figure.

**Device access:**
[Likely] A 2024 SA-specific study (five former Model C high schools,
Stellenbosch research) found 62% of learners Grade 4-11 own a personal
device by age 10, and 83% have a social media account by 12. That's
personal ownership, not household access — access (shared device,
parent's phone) is higher, plausibly 75-85% for the 6-18 band, but this
is a bounded guess, not a stat.

**OS split:**
[Certain] Android holds 76.74% of mobile OS share in South Africa as of
May 2026 (Statcounter), iOS 23.24%. This is traffic share, not
population share, and skews slightly toward higher-usage/urban devices,
but is a reasonable proxy for the reachable market building Android-
first.

**Parent financial-app engagement (the real gate):**
[Likely] SARB's Payments Study (SCPC/DCPC, 2023, adults 18+, national
population base 40.5M) found 50.3% of SA adults use banking apps
regularly — more than internet banking (27%) but well short of
universal. [Guessing] The "80%+ of SA adults use mobile banking" figure
seen on some aggregator sites (citing GSMA/Statista) is lower-confidence
— it conflates mobile money with banking apps; SARB's own survey data is
the more defensible number. [Guessing] Parents of school-age kids skew
toward the economically active 25-54 bracket, more banked/app-literate
than the national average — a reasonable adjustment is 55-65% banking-
app engagement for this specific parent cohort, not 50.3%.

**Rough funnel:** 14.5M kids × ~70% device access × ~60% parent digital-
financial engagement ≈ **6.1M kids in "reachable" households** (device
present, parent already comfortable transacting digitally). That is the
realistic SAM, not the 14.5M TAM.

**Adoption rate (least evidenced figure):**
[Guessing] No public SA benchmark exists for kids'-financial-education
app adoption specifically; this is inference from adjacent markets
(GoHenry/Greenlight UK/US), not data: a new entrant with no bank/school
distribution typically captures 0.3-1% of its reachable pool as installs
in year one. Free-to-paid conversion for freemium kids'-finance apps
benchmarks 2-6% globally; SA's lower discretionary income for a
"nice-to-have" app argues for the low end initially (1-3% for a pure
subscription model).

**Competition in South Africa specifically:** no direct incumbent does
what MiniMoney does (gamified, standalone consumer app). What exists:
**African Bank's MyWORLD Power Pocket** (kids' sub-accounts with debit
cards under a parent account — a banking feature, not education-led);
**MoneyAfrica Kids** (Nigerian-origin edtech app, courses/quizzes,
parent-subscribes-child, available but not built for South Africa);
**MoneyTime SA** (web-based financial literacy curriculum, ages 10-15,
sold B2B2C through schools, not a gamified mobile-first consumer app).
None combine gamification + mobile-native + direct-to-parent
distribution the way GoHenry/Greenlight do in the US/UK — a real gap,
but it also means there is no local comp data to validate willingness-
to-pay against.

**Advertising/ads-as-revenue-lever, reconsidered:**
[Certain] POPIA Section 34 requires consent from a "competent person"
(parent/guardian) before processing a child's personal information at
all — including data used for ad targeting. [Certain] The ARB's Code of
Advertising Practice, Clause 14, separately prohibits ads that exploit
children's credulity, inexperience, or lack of judgment, and requires
content aimed at children to avoid manipulative pressure tactics.
Combined, this rules out behavioral/programmatic ad targeting on the
child's own usage data — restricted to contextual, non-profiled
inventory, or ads served against the parent's consented profile. [Guessing]
No hard SA-specific eCPM figure for contextual mobile ad inventory is
available, but contextual-only inventory yields a fraction of targeted
eCPM globally, and African market CPMs already sit near the bottom of
global ad-rate tables — ad revenue per free user is plausibly a few
cents to low tens of cents per user per month, not a material revenue
line on its own. The ad layer should be treated as (a) a partial CAC
offset and (b) a psychological nudge toward the paid tier ("remove
ads"), not a standalone monetization pillar. Ad friction also tends to
push free-to-paid conversion slightly above a pure paywall's baseline —
a reasonable range for a hybrid freemium+ads kids'-finance app in a
lower-disposable-income market is **2-4% free-to-paid**, versus 1-3% for
subscription-only.

**Rerun funnel:** ≈6.1M reachable kids × 0.3-1% Year-1 install capture ≈
**18,000-61,000 free users**. Apply 2-4% conversion ≈ **360-2,440 paying
subscribers in Year 1**, plus marginal ad revenue mostly offsetting a
slice of infrastructure/CAC cost rather than adding a real second
revenue stream. Landing a distribution partnership (school, bank, telco
bundle) is the actual lever to move this materially, not organic install
rate.

**Consent-flow friction note (not a new modeling input, a design
implication):** POPIA's parental-consent requirement means onboarding
must gate through the parent before the child touches the app at all —
not optional friction to design around, a legal floor. A clumsy consent
flow at signup is a plausible reason actual install-to-activation lands
at the low end of the 0.3-1% band rather than the high end.

## Raw clarification — two decisions (verbatim from user)

1. I want it capped at 7 as 10 may be overkill

2. "Fintech Advance" only unlocks for the 15-18 sub group and is a non
negotiable requirement. Its core is to teach the concept not enable in
app. This is somethiong only the Parent will be allowed to enable based
on their comfort levels

## Relevant to which BusinessCase_v5.md gaps

- **Late-penalty cap contradiction (flagged by Chief of Staff)**:
  resolved. The correct figure is **7 Mbucks/week** (escalating from 5 →
  6 → capping at 7), not 10 as stated in the Incubator's original v5
  Operations/Technology/Risks text. The pilot-specific cap remains **3
  Mbucks/week** (per the user's prior hand-edit to Success Criteria).
  Every section referencing the 5/6/10 figure must be corrected to
  5/6/7 for v6.

- **Fintech Advance course (introduced by user's hand-edit to Value
  Proposition, previously unscoped)**: clarified. Restricted exclusively
  to the **15-18 age sub-band** — not available to younger bands. Its
  inclusion in the curriculum for that band is described as a "non-
  negotiable requirement," but **enabling/unlocking access to it for a
  specific minor is solely a parent decision**, made at the parent's
  discretion based on their own comfort level — it is not automatically
  available even within the 15-18 band once a family reaches that
  paywall tier. Its pedagogical scope is explicitly **conceptual/
  educational only** — it teaches the *concepts* of trending/entrepreneurial
  ventures (e.g. forex trading, dropshipping), and does **not** enable any
  actual trading execution, brokerage functionality, or real-money
  trading activity within the app. This materially narrows the risk the
  Chief of Staff flagged (teaching real trading concepts to minors
  alongside real-money mechanics) — there is no in-app trading capability
  at all, only conceptual instruction, gated by parent opt-in.

- **Market & Competition (Partial, previously Incubator-general-
  knowledge-only candidate content)**: this clarification supplies real,
  cited external research — Stats SA population data, a 2024 Stellenbosch
  device-ownership study, Statcounter OS-share data, SARB's Payments
  Study on banking-app usage, and named South African competitors
  (African Bank MyWORLD Power Pocket, MoneyAfrica Kids, MoneyTime SA) —
  each with the user's own honesty-calibrated confidence tag
  ([Certain]/[Likely]/[Guessing]) distinguishing sourced fact from
  extrapolation from bounded guesses. This should be treated by the
  Incubator as genuine **Supporting Evidence**, materially different in
  kind from its own previously-flagged "Incubator general knowledge,
  Evidence: Assumed" candidate content, and the Incubator should preserve
  the distinct confidence tags per claim rather than flattening them to a
  single section-level rating.

- **Revenue & Costs / Objectives / Success Criteria / Validation
  Strategy**: the rerun funnel model (6.1M reachable kids → 18,000-61,000
  Year-1 free users → 360-2,440 Year-1 paying subscribers) and the ad-
  revenue-as-CAC-offset framing supply the first real, cited quantitative
  basis for these sections, replacing several of the Incubator's own
  placeholder ranges. The user's own hand-edited concrete percentages in
  Success Criteria (30% curriculum engagement, 65% operational health,
  2% Freemium conversion) should be reconciled against this more rigorous
  2-4% conversion range — the Incubator should flag if the user's hand-
  edited 2% figure is intended as a candidate target within, at the low
  end of, or independent of this newly-supplied range, since neither
  document explicitly states which.

- **Legal & Compliance (Critical, Partial)**: new, more specific detail
  supplied on the advertising angle — POPIA Section 34 (competent-person
  consent, extending explicitly to ad-targeting data) and the ARB Code of
  Advertising Practice Clause 14 (prohibition on ads exploiting
  children's credulity/inexperience, no manipulative pressure tactics
  aimed at children) are both cited as [Certain]. This is directly
  relevant if any ad-supported free-tier monetization is pursued (raised
  as a candidate direction in this same research) and should be added to
  the Legal & Compliance section's open-items list if ads are adopted as
  part of the monetization strategy.
