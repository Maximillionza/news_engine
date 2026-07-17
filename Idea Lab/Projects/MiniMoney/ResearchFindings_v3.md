# Research Findings — Engagement 3 — MiniMoney

Task order: `TaskOrder_ResearchHouse_v3.md`. Continuity: this is Research
House's third engagement on this case; see `EngagementLog.md` for
Engagements 1-2. This engagement is self-contained (no Business Case
read) and covers two narrow legal/regulatory research questions.

---

## Flagged Item 1

**Original flagged item (verbatim):** "Does mere account registration by
a minor — independent of what feature they subsequently access —
constitute 'processing' of a minor's personal information under POPIA,
such that competent-person (parental) consent would be required *before*
registration itself, not just before accessing financial features?
Research what is publicly documented about POPIA's application to the
*registration/account-creation step* specifically (as distinct from
in-app feature use) for apps or services directed at children. Also note
whether the practice/hypothetical nature of any data entered afterward
(not real financial information) has any bearing on this specific
question, or whether that is a separate, later consideration."

**What I found:**

POPIA's definition of "processing" (Section 1) is drafted broadly and
explicitly includes "collection, receipt, recording, organisation,
collation, storage, updating or modification" of personal information —
not only use or disclosure. Capturing a minor's name, age/date of birth,
and (possibly) email address at registration falls squarely within this
definition: it is collection and storage of personal information the
moment the account is created, regardless of what the account can
subsequently do.

Section 34 of POPIA states a general prohibition: a responsible party
"may not process personal information concerning a child" except where a
Section 35 exception applies. The dominant exception in practice is prior
consent of a "competent person" (a parent or legal guardian, defined as
someone legally competent to consent to matters concerning the child).
Because Section 34's prohibition attaches to "processing" as a whole —
not to a subset of processing tied to a specific feature or purpose —
and because collection/registration is itself processing, the general
prohibition would on its face apply at the point personal information is
first collected, i.e., at registration, not only once financial features
are unlocked. Multiple secondary legal-commentary sources (VDT Attorneys,
MJ Kotze Inc, POPIApack, ITLawCo) restate this same framework — consent
must be obtained "prior to processing" — without contradicting it, but
none of them explicitly rules on a "registration-only, no financial data
yet" scenario as its own distinct question. One source (VDT Attorneys)
specifically flags that terms-and-conditions clauses stating "minors need
parental consent" are commonly used by platforms but are unlikely, on
their own, to constitute valid POPIA consent — the responsible party
bears the burden of proving actual competent-person consent was
obtained, not just published.

On the practice/hypothetical-data question: no source found draws a
distinction in POPIA between "real" and "hypothetical/practice" data for
purposes of triggering the Section 34/35 framework. The statutory
prohibition is keyed to whether the information is "personal information
concerning a child" (i.e., relates to an identifiable child), not to
whether the substantive content of that information is itself real
financial data. Registration data (name, DOB, email) is personal
information regardless of what the child does afterward with the
practice-budgeting tool; the hypothetical nature of budgeting inputs
entered post-registration looks like a separate, secondary question about
whether *that* data is personal information at all (arguably it may not
identify the child if it's just numbers with no financial reality
attached) — not a reason to treat the registration-stage data
differently. This reading is my own synthesis of the statutory text and
secondary commentary, not a rule I found stated explicitly by any single
source in these terms.

**Source(s):**
- POPIA Section 1 definitions ("processing"), as summarized via [MJ Kotze Inc — POPIA definitions](https://mjkinc.co.za/popia/definitions) and [popiact-compliance.co.za](https://www.popiact-compliance.co.za/popia-information/17-conditions-for-lawful-processing-of-personal-information)
- [Section 34 — Prohibition on processing personal information of children](https://popia.co.za/section-34-prohibition-on-processing-personal-information-of-children/)
- [Section 35 — General authorisation concerning personal information of children](https://popia.co.za/section-35-general-authorisation-concerning-personal-information-of-children/)
- [VDT Attorneys — Processing of children's personal information in the modern age of technology](https://vdt.co.za/consent/south-africa-processing-of-childrens-personal-information-in-the-modern-age-of-technology/) (also mirrored at [DataGuidance](https://www.dataguidance.com/opinion/south-africa-processing-childrens-personal))
- [ITLawCo — Reimagining consent for kids in South Africa's digital economy](https://itlawco.com/reimagining-consent-for-kids-in-south-africas-digital-economy/)
- [POPIApack — Unpacking the Processing of Children's Information in terms of POPI](https://www.popipack.co.za/unpacking-the-processing-of-childrens-information/)

**Confidence:** Medium-High for the statutory reading (the "processing"
definition and Section 34/35 text are primary-source and unambiguous on
their face); Medium for the application to this specific
registration-before-consent scenario, since no source directly addresses
a "registration-only, features locked until parent links" product design
— this is my inference from the statute plus consistent secondary
commentary, not a directly on-point ruling, guidance note, or Information
Regulator statement.

**Evidence tier:** Supported.

**Could not find:** No Information Regulator guidance note, enforcement
action, or court ruling addressing the specific scenario of a
minor-initiated registration gated ahead of a linked parent account
(i.e., no direct South African precedent on "does registration alone
trigger Section 34," as opposed to the general statutory reading above).
No source distinguishes "hypothetical/practice" data from "real"
financial data as a POPIA-relevant category — this appears to be a true
gap in publicly available guidance, not merely hard to find. This
question sits squarely in the territory the task order flags for the
planned specialist legal opinion — the statutory reading above is a
reasonable starting point for that opinion, not a substitute for it.

---

## Flagged Item 2

**Original flagged item (verbatim):** "Does the National Credit Regulator
(NCR), or any other South African regulator, actually treat read-only
bank-account-linking/open-banking-style verification services (of the
kind Stitch or Mono provide) as regulated 'payment facilitation'
requiring NCR registration or similar compliance? Research what NCR
registration actually covers (e.g. credit providers, debt collectors,
payment distribution agents) and whether a read-only, non-custodial
verification integration (one that never moves money, only confirms a
transaction occurred) would plausibly fall within that scope, or whether
this rationale for excluding account-linking may be based on a
misunderstanding of what NCR registration actually requires."

**What I found:**

NCR registration under the National Credit Act (NCA) covers four defined
categories of participant: credit providers (entities extending credit
under credit agreements, registration mandatory above a set threshold),
credit bureaus (entities that store and report consumer credit
information for credit-granting purposes), debt counsellors (registered
individuals providing statutory debt review services), and Payment
Distribution Agents ("PDAs," registered under NCA Section 44A and
Regulation 10A). PDAs specifically exist to collect a single monthly
payment from a consumer under formal debt review and distribute it to
that consumer's credit providers — they are a custodial function created
to solve a specific problem (debt counsellors historically could not
collect consumer payments directly into their own accounts). A fifth
category, Alternative Dispute Resolution Agents, handles credit disputes,
not payments.

None of these four categories describes what a read-only account-data
verification service (Stitch- or Mono-style) does. Such a service does
not extend credit, does not compile or report credit information for
credit-granting decisions, does not conduct statutory debt counselling,
and — critically for the PDA category, which is the closest conceptual
match — does not receive or hold consumer funds for distribution to
creditors; it only reads account data with consumer permission and
confirms whether a transaction occurred. The PDA registration category is
explicitly built around the act of receiving and distributing money,
which a read-only integration by definition does not do.

Separately, sourced legal commentary on South African open banking
(ENS Africa) states plainly that South Africa currently has no equivalent
to the EU's PSD2 regime, and does not identify any South African
regulator — including the NCR — as currently exercising binding oversight
over account information service providers (AISPs) or payment initiation
service providers (PISPs). Other sourced material found in this
engagement identifies the Financial Sector Conduct Authority (FSCA) and
South African Reserve Bank (SARB) — not the NCR — as the bodies
associated with the still-developing Open Finance framework, consistent
with Engagement 2's prior finding that this framework is not yet
mandated (cited effective date January 2026, full compliance target
2028).

Taken together, this is a reasonably strong (though not definitive)
indication that the stated rationale for excluding account-linking — that
it would trigger NCR requirements — does not match what NCR registration
actually covers. The NCR's mandate is anchored to credit extension, debt
review, and credit information, not to read-only, non-custodial data
verification. No source found treats "confirming a transaction occurred"
as itself a regulated credit activity.

**Source(s):**
- [NCR — Requirements for registration as a payment distribution agent](https://www.ncr.org.za/documents/pages/PDA/Requirements%20for%20registration%20as%20a%20payment%20distribution%20agent.pdf)
- [FA News — Court rules that NCR has powers to appoint Payment Distribution Agents](https://www.fanews.co.za/article/credit/57/general/1270/court-rules-that-ncr-has-powers-to-appoint-payment-distribution-agents-and-to-impose-conditions-of-registration-on-debt-counsellors/9086) (context on why PDAs exist — debt counsellors barred from directly collecting consumer payments)
- General NCR registration-category summaries cross-checked across [EvalFin — NCR Registration Guide](https://evalfin.com/blog/ncr-registration-requirements-south-africa/), [Barnard Inc — What is NCR Credit Registration](https://barnardinc.co.za/2024/11/12/what-is-ncr-credit-registration-and-why-is-it-important-in-south-africa/), and the [NCR's own Register of Registrants](https://www.ncr.org.za/register_of_registrants/)
- [ENS Africa — The regulation of open banking in South Africa](https://www.ensafrica.com/news/detail/4801/the-regulation-of-open-banking-in-south-afric)
- Prior Engagement 2 finding (this case's `ResearchFindings_v2.md`) on SARB/FSCA-linked Open Finance framework timing, referenced here as consistent context, not re-verified in this engagement

**Confidence:** Medium. The primary-source material on what PDA/credit
provider/credit bureau/debt counsellor registration actually requires is
solid and directly sourced from the NCR itself. The negative inference —
that a read-only verification service therefore falls outside NCR's
scope — is my own reasoned conclusion from that primary material plus
consistent secondary commentary, not a direct NCR statement, exemption
ruling, or FSCA/SARB guidance note addressing this exact product type by
name. No regulator-issued document explicitly says "account-linking
verification services do not require NCR registration."

**Evidence tier:** Supported.

**Could not find:** No NCR guidance, FAQ, or ruling that names
account-information/read-only verification services explicitly (by
category or example) as inside or outside NCR's registration scope — the
conclusion above is inferential, built from what the four registration
categories actually cover rather than from a direct statement about
Stitch/Mono-type services. No FSCA or SARB publication found that
confirms which body, if any, currently has binding supervisory authority
over AISPs like Stitch or Mono ahead of the Open Finance framework's full
rollout. As with Item 1, this is exactly the kind of question the task
order correctly identifies as needing the specialist legal opinion to
close — the findings here narrow the question and suggest the stated
"NCR risk" rationale may rest on a mistaken premise, but they do not
constitute a legal conclusion that no NCR (or other) exposure exists.

---

## Summary for the Incubator

Both items received Supported-tier findings with Medium-to-Medium-High
confidence. Both are explicitly framed, per the task order's own
instruction, as informing rather than replacing the planned specialist
POPIA/ARB/contract-law legal opinion. Item 1's statutory reading (broad
"processing" definition + Section 34/35's unqualified prohibition)
plausibly supports treating registration itself as consent-triggering,
but no direct precedent confirms this for a registration-before-parent-
link product design specifically. Item 2's finding plausibly undermines
the stated NCR-avoidance rationale for excluding account-linking (none of
the NCR's four registration categories matches a read-only, non-custodial
service), but likewise stops short of a legal conclusion, since no
regulator has spoken to this exact service type directly.
