# Clarifications for MiniMoney — v12

> Three items resolving open questions in BusinessCase_v11.md's Legal &
> Compliance / Critical Gaps. Not a pivot. To be incorporated into
> BusinessCase_v12.md.

## Date
2026-07-09

## 1. Minor contractual capacity (verbatim from user)
"The contractual obligation is against the parent not the child. The
child is a participant in the process and therefor is not forced into
abiding by the contract. The contract itself is the tasks the child
needs to complete in order to be remunerated. if the task is incomplete,
then the child will not be remunerated for the task. based on my
research, there is no law or act that prevents contracts between a
minor and a parent but its is limited in the scope or type of contract
and this app does not fall into any of those categories."

**Relevant to:** Legal & Compliance's "minor contractual capacity"
sub-question, sharpened by Research House Engagement 2 as a required
scope item for the specialist legal opinion. Treat this as a
user-supplied claim/research finding — the Incubator should not present
"no law or act prevents this" as a settled legal conclusion; it remains
subject to the specialist opinion's confirmation, same as every other
legal-interpretation question in this case. The structural point itself
(obligation runs against the parent; the child bears no binding
obligation and receives payment as a condition of task completion, not
as a party to an enforceable contract) is a clear design statement and
can be documented as such.

## 2. Trust/enforcement risk / read-only account-linking (verbatim from
## user)
"This is a deliberate design choice based on the requirements to
facilitate payments on the app set by the NCR. while its design is
intentional today, it may change with further development of the app.
this should close the question regarding Stitch/Mono"

**Relevant to:** the Research House Engagement 2 finding that read-only
account-linking (Stitch/Mono) was a plausible later-stage option. This
is now closed as a present-scope decision, not merely deferred: staying
with honor-system self-reporting is a deliberate choice driven by
National Credit Regulator payment-facilitation requirements the user
wants to avoid triggering, not a resource/timing constraint. Revisiting
this remains possible with further app development, but is not a stated
plan for any near-term version.

## 3. Family-vs-child install/pre-link functionality (verbatim from
## user, across two messages)
First message: "The minor may download, install and register on the app
but functionality will be severely limited to the following until a
parent account has been linked done via the email or Google account
registered by the parent: Accessing the budgeting feature." Second
message, resolving the Chief of Staff's ambiguity question: **"I meant
that the minor will only be able to access a feature called budgeting.
In the case where the parents account is not linked, the minor will
need to capture the Income manually while an account which has been
linked will assume the income based on the amount earned by the
minor. Should I consider additional features to leave unlock i will
reconfirm its impact regarding compliance."**

**Final design:** a minor may download, install, and register an
account independently. Before a parent account is linked (via the
parent's email or Google account), the minor's account can access
exactly **one** feature: a "budgeting" tool, in which the minor manually
captures/enters their own income data for practice purposes. Once a
parent account is linked, this same feature auto-populates income based
on the minor's actual Mbuck earnings rather than manual entry. No other
feature is accessible pre-link. The user is deliberately not unlocking
additional pre-link features at this time, and has stated any future
expansion of pre-link functionality will be evaluated for compliance
impact individually before being added — this is not a blanket policy
decision to relax the consent gate further, only a narrow, single-feature
exception as currently designed.

**Relevant to:** this reopens, in narrow form, the same class of
question the case resolved in `Clarifications_v5.md` when the
education-only direct-signup carve-out was dropped in favor of
collapsing everything behind parental consent. The Incubator should
apply the same directional compliance assessment it applied to that
earlier carve-out: does a minor manually entering practice income data
into a "budgeting" feature, before any parent consent-link exists,
constitute processing of the minor's personal information under POPIA
(Sections 34-35, competent-person consent) requiring prior consent —
even though (a) no real money or task-earnings data is involved
pre-link, and (b) the data may be practice/hypothetical rather than
reflecting the minor's actual circumstances? This is a narrower
carve-out than the one previously closed (a single non-monetary
practice feature, not full app access), but the Incubator should not
assume it is automatically compliant merely because it is narrower — it
should characterize the risk with the same rigor as before, flagged for
the specialist legal opinion like every other open compliance question
in this case, not resolved as safe by inference.

## Process note (not case content, for the Chief of Staff Log only)
Separately, the user has confirmed the Business Case document should
remain in its current unified format (inline Status/Confidence/Evidence
tags, provenance citations, and per-version changelog blocks together in
one document) rather than being split into a clean business document
plus a separate assessment/provenance document. No template change to
the Incubator's output format is being made at this time.
