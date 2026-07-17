# Research House — Engagement Log — MiniMoney

This log tracks Research House's own prior engagements on the MiniMoney
case study only. It is append-only. Nothing from any other case study is
ever referenced here, and this log is never shared with or informed by
any other case's engagement history.

---

## Engagement 1 — 2026-07-07

**Task order received:** `TaskOrder_ResearchHouse_v1.md` — 10 flagged
items compiled from BusinessCase_v6.md's Critical Gaps and Outstanding
Questions sections: (1) SA-specific kids-app install-conversion
benchmarks, (2) local competitor pricing benchmark, (3) SA-specific
mobile ad eCPM data, (4) which Freemium conversion benchmark applies
(ads-hybrid vs subscription-only), (5) published demand signals for SA
kids'-financial-education apps, (6) app-store child-category policy
specifics for a cosmetic rewards store, (7) POPIA data retention/deletion
norms for child-directed apps, (8) ARB/NCR precedent on payslip/invoice/
arrears terminology applied to minors, (9) cost-range scoping for a
POPIA/ARB legal opinion, (10) cost-range scoping for the technical build.

**Delivered:** `ResearchFindings_v1.md` with findings for all 10 items.
8 items produced genuine supporting evidence (Supported tier) — including
one directly confirmed local pricing anchor (MoneyTime SA, R995/year),
one SA-specific eCPM figure ($0.80 AdMob blended average, Medium
confidence), confirmed app-store policy language for both Apple Kids
Category and Google Play Families Policy bearing on non-monetary rewards
stores, and confirmed POPIA statutory retention principles (Section 14).
Item 4 was identified as not a research question at all — an internal
product-decision dependency — and flagged as such rather than forced.
Item 9 was scoped (firm shortlist + rough cost-range inference) per the
task order's explicit instruction not to attempt the legal opinion
itself.

**Could not resolve / flagged as genuine gaps:** No SA-specific kids-app
install-conversion or adoption-rate figure exists publicly (Item 1) —
this is the weakest link and stays weak; closing it requires either a
commissioned survey (~R80,000-R250,000, 3-6 weeks, scoped but not
commissioned) or a live pilot. MoneyAfrica Kids' actual premium price
point could not be found publicly (Item 2, partial gap). No ARB ruling,
National Credit Regulator guidance, or comparable precedent was found
addressing payslip/invoice/arrears terminology applied to minors
specifically (Item 8) — confirmed absent, not merely hard to find;
requires a licensed attorney's interpretation, not desk research.
POPIA's adequacy relative to child-specific frameworks like COPPA/GDPR-K
also remains a legal-adequacy question outside desk-research scope
(Item 7, partial).

(Longer entry — first engagement on this case, covers 10 distinct items
across quantitative, competitive, regulatory, and cost-scoping
categories; flagging here so a future engagement or the Incubator can
see at a glance which sub-items within each numbered item still have
open threads, e.g. the MoneyAfrica Kids pricing walkthrough and the
Statista eCPM cross-check noted as concrete next steps inside
ResearchFindings_v1.md itself.)

---

## Engagement 2 — 2026-07-08

**Task order received:** `TaskOrder_ResearchHouse_v2.md` — a follow-on,
self-contained task order (no Business Case read) about the parent-side
late-payment penalty's lack of an enforcement mechanism. 4 flagged items:
(1) South African read-only account-linking/open-banking services (Stitch,
Mono, aggregators) that could verify an external payment without
MiniMoney holding funds, including rough pricing/licensing and incremental
data-privacy obligations; (2) practical landscape only (not a legal
conclusion) on whether the in-app arrears/penalty balance has real
contractual/legal enforceability in SA family/consumer context; (3) how
comparable kids'-allowance apps (local/international) handle verifying an
unintegrated external payment — is honor-system self-report standard
practice; (4) rough cost/complexity scoping for the account-linking option
for a solopreneur AI-assisted build — early-build feasible or later-stage.

**Delivered:** `ResearchFindings_v2.md` with findings for all 4 items, all
Supported tier. Item 1: confirmed Stitch and Mono both exist with South
African footprint and read-only account-data products, but no SA-specific
public pricing for either; confirmed SA's Open Finance framework is not
yet mandated (effective date cited Jan 2026, full compliance 2028);
flagged two lower-cost alternative mechanisms worth evaluating — PayShap
Request's native bank confirmation/reference flow, and general
proof-of-payment document-fraud-detection APIs — as design ideas, not
validated solutions. Item 2: surfaced general SA contract-law doctrines
relevant to the question (domestic-agreement/Balfour v Balfour
"intention to create legal relations" presumption, minors' limited
contractual capacity, National Credit Act's likely non-application to
informal family arrangements) but explicitly declined to draw a
conclusion, deferring to the planned legal opinion as instructed. Item 3:
strong finding — the category splits into "become the money-mover"
(GoHenry, Greenlight — different regulatory model entirely) versus
"track-only honor-system" (FamZoo's IOU accounts, Bomad) — confirming
MiniMoney's honor-system design matches an established sub-category
rather than being unprecedented; this is a genuine negative finding (no
app found that verifies unintegrated payments without doing one of those
two things) rather than a stretched result. Item 4: concluded, with Medium
confidence, that account-linking is realistically a later-stage feature
given regulatory immaturity, Stitch's enterprise-sales-only access model,
and unconfirmed bank-by-bank coverage for Mono in South Africa.

**Could not resolve / flagged as genuine gaps:** No South Africa-specific
vendor pricing for Stitch's or Mono's account-linking product (needs a
direct sales inquiry to both). No reliable, non-tracker-site figure for
how many South African banks are actually reachable via account-data
aggregators — the only figure found came from a third-party directory
site of uncertain reliability and was flagged as directional only, not
fact. No South African case law or regulator guidance found addressing a
family allowance/penalty arrangement specifically (Item 2) — confirmed
absent, consistent with the same style of regulatory-precedent gap
already flagged in Engagement 1, Item 8. No local (South African)
comparable app found for Item 3 — same underlying local-market visibility
gap already flagged in Engagement 1, Item 1; this is a recurring pattern
across both engagements, not a new one.

(Medium-length entry — four items, most resolved cleanly with converging
multi-source evidence, but two open threads carried forward for whoever
engages next: the direct Stitch/Mono pricing calls, and the recurring
absence of South Africa-specific comparables/precedent that has now shown
up in both engagements on this case.)

---

## Engagement 3 — 2026-07-09

**Task order received:** `TaskOrder_ResearchHouse_v3.md` — a follow-on,
self-contained task order (no Business Case read), issued after both
Critical sections dropped to Confidence: Low in BusinessCase_v12.md.
2 flagged items tied to two new design decisions this cycle: (1) whether
mere minor account registration (before any parent link, capturing
name/age/email to gate access to a practice-only hypothetical budgeting
tool) itself constitutes "processing" under POPIA requiring
competent-person consent before registration, not just before financial
feature use, and whether the hypothetical/practice nature of later data
bears on that question; (2) whether the NCR (or another SA regulator)
actually treats read-only, non-custodial account-linking/verification
services (Stitch/Mono-style) as regulated "payment facilitation" — the
stated reason the product avoids integrating one — by examining what NCR
registration categories actually cover.

**Delivered:** `ResearchFindings_v3.md` with findings for both items, both
Supported tier. Item 1: POPIA's Section 1 "processing" definition is
broad and explicitly includes collection/storage, and Section 34's
general prohibition on processing a child's personal information (subject
to Section 35 exceptions, chiefly competent-person consent) is not
qualified by feature access — supporting the reading that registration
itself (collecting name/DOB/email) triggers the consent requirement, not
just later financial-feature use. No source distinguishes hypothetical
from real data as a POPIA-relevant category — treated as a likely
separate, secondary question (whether practice-budgeting data is
"personal information" at all) rather than a reason to treat registration
differently. Item 2: NCR registration covers four defined categories
(credit providers, credit bureaus, debt counsellors, Payment Distribution
Agents) all built around extending credit, credit information, debt
counselling, or custodial receipt/distribution of consumer funds under
debt review specifically — none of which matches a read-only,
non-custodial verification service. Cross-checked against sourced
commentary confirming South Africa has no PSD2-equivalent regime and that
Open Finance oversight (still not fully mandated) sits with SARB/FSCA, not
NCR. Findings plausibly undermine the stated NCR-avoidance rationale for
excluding account-linking, but this is a reasoned inference from what NCR
registration covers, not a direct regulator statement addressing this
service type by name.

**Could not resolve / flagged as genuine gaps:** No Information Regulator
guidance note, enforcement action, or ruling addresses the specific
scenario of minor-initiated registration gated ahead of parent-linking
(Item 1) — the statutory reading is sound but unconfirmed by direct
precedent on this exact product pattern. No NCR, FSCA, or SARB document
found that names account-information/read-only verification services
explicitly as inside or outside any regulator's scope (Item 2) — the
conclusion is inferential from what the four NCR categories actually
cover, not a direct exemption or ruling. Both items were explicitly
scoped by the task order as informing, not replacing, the planned
specialist legal opinion, and both findings are presented that way rather
than as conclusions.

(Medium-length entry — two narrow, well-defined legal/regulatory
questions, both resolved with a clear statutory/primary-source reading
and consistent secondary commentary, but both stop short of precedent
directly on point for MiniMoney's specific product pattern; this is the
same class of gap already flagged in Engagements 1 and 2 — South African
precedent specific to novel product designs remains thin across all three
engagements on this case — and is exactly the reason the legal opinion
remains necessary rather than optional.)

---

## Engagement 4 — 2026-07-13

**Task order received:** `TaskOrder_ResearchHouse_v4.md` — a follow-on,
self-contained task order (no Business Case read), shifting away from
legal/regulatory/market-sizing questions into funding structure: identify
concrete non-dilutive funding options (grants, accelerators,
competitions) available to a South African solo-founder, pre-revenue-
proven, fintech-adjacent/edtech mobile-app venture, as a fallback if the
stated R20,000 self-fund ceiling is reached before the venture is
self-sustaining. 4 flagged items: (1) named SA-accessible grant/
non-dilutive programs, (2) realistic timelines (application window,
decision, disbursement) given a tight 6-month runway, (3) eligibility fit
— flag exclusions plainly rather than listing programs unqualified, (4)
rough typical award size so the founder can judge proportionality.

**Delivered:** `ResearchFindings_v4.md` with findings for all 4 items, all
Supported tier. Identified 8 named candidate programs (NYDA, SEDA
Technology Programme, TIA's various instruments, SAB Foundation, Injini's
earlier-stage cohort, Mastercard Foundation EdTech Fellowship via Injini,
FNB App of the Year, Google for Startups Black Founders Fund: Africa) plus
5 programs explicitly named in the task order or surfaced in research and
then ruled out on structural grounds (NEF is loans/equity not grants
despite being named as a candidate to check; Standard Bank's fintech
accelerator relationship and Naspers Foundry are equity-based/defunct;
Grindstone is growth-stage/women-focused). NYDA emerged as the
best-evidenced fit on timeline grounds (rolling applications, ~30
working-day disbursement post-approval, sourced from NYDA's own
materials) and on award-size proportionality (grants start at R1,000, not
just capped at R200,000-250,000), but is entirely gated on the founder's
age (18-35 band), which this research does not know and did not assume.
Two programs were flagged as hard eligibility exclusions on their own
stated terms regardless of founder facts: the Mastercard Foundation
Fellowship (requires post-revenue, >R1m turnover, 8,000-learner reach)
and Google's Black Founders Fund (requires a live in-market product,
separately from its founder-demographic requirement). SAB Foundation's
current cycle was found already closed for 2026 (deadline 16 March 2026,
past as of this engagement), making it a next-year option only. FNB App
of the Year was found to be structurally a recognition competition for
already-launched, traction-proven apps rather than pre-launch seed
capital, based on the profile of its most recent (2025) winner.

**Could not resolve / flagged as genuine gaps:** No confirmed 2026 entry-
window dates for FNB App of the Year — the program's own site could not
be successfully loaded across repeated attempts in this engagement
(tooling timeouts), so current-cycle dates and total prize figure rest on
a pattern inference from the 2025 cycle, not a direct confirmation. No
confirmed open 2026 cohort for Injini's earlier-stage (smaller-grant)
track, as distinct from the eligibility-excluded Mastercard Fellowship
cohort, which was confirmed closed. Whether TIA's Technology Readiness
Level-based, historically research/TTO-oriented funding instruments would
even consider a solo, non-research-affiliated consumer mobile-app founder
eligible remains a genuine open question, not resolved either way by
public material. SEDA Technology Programme's own timeline (as distinct
from SEDA's general programme timelines) could not be pinned down
specifically. Three founder-specific facts this research does not have
and did not assume in either direction — age, race/gender, and current
company-registration status — gate NYDA, Google's Black Founders Fund,
several women-focused 22 On Sloane/Grindstone programmes, and SEDA
respectively, and would need direct founder confirmation before any of
these are pursued.

(Longer entry — a genre shift from this case's first three engagements
(legal/regulatory/market gaps) into funding-structure research, so more
programs to canvas than usual; flagging in particular that Item 2
(timelines) came out as the weakest-evidenced of the four flagged items
this round — mirroring, in a different domain, the same "SA-specific
precedent/data is thin" pattern already noted in Engagements 1-3, this
time as "SA program-level administrative timelines are thin and mostly
unpublished" rather than legal precedent specifically.)
