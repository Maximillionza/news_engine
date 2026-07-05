# Expert Roster: MiniMoney — v1

> Each entry names a specific assumption or gap drawn from the actual
> case study content (not a generic domain concern), and explains why
> that expert's input is needed before this case can be validated.

---

### 1. Payments & Financial Services Compliance Counsel

The case study states the parent "is then required to make the payment
via their registered bank to the kid for the expected value," which the
Incubator has assumed means MiniMoney never itself holds or transmits
funds — but this is an assumption, not a stated architectural decision,
and the whole regulatory posture of the product hinges on which is true.
A payments compliance expert is needed to determine whether generating
an "invoice" that triggers a mandated bank transfer, even one executed
entirely outside the app, constitutes payment facilitation requiring a
money-transmitter or e-money license in the target jurisdiction. This
person should also assess whether the "payslip"/"overtime"/"expenses"
terminology carries any unintended regulatory or contractual implication,
since the case study uses employment-style language for what is
functionally a parent-child allowance arrangement.

### 2. Child Data Privacy & Consent Specialist

The case study explicitly sets the lower age bound at 6 years old, and
describes automated data flows (task assignment, earnings calculation,
invoice/payslip generation) that necessarily involve collecting and
processing a young child's activity data — none of which is addressed
for consent or data-minimization purposes anywhere in the source. This
expert is needed to design a verifiable parental consent flow before any
data collection begins, determine whether the 6–9 age band can interact
with the app directly at all versus only through a parent-mediated
interface, and confirm how the product would need to be restructured to
comply with children's-category rules on both the Apple App Store and
Google Play, which the case study does not mention having considered.

### 3. Financial Literacy Curriculum Designer (K-12 age-band specialist)

The case study's only instruction on the education component is that it
"needs to be incorporated and designed to appeal to the respective age
demographic" — a 12-year span (6–18) with no proposed sub-band
breakdown, learning objectives, or content format. A curriculum designer
with experience spanning early-childhood through late-teen financial
literacy is needed to translate this single sentence into an actual
scope of work: how many age bands, what concepts map to each (e.g. basic
counting/saving for 6–9 vs. taxation/investing concepts for 14–18), and
whether the "expense" and "overtime" mechanics described by the user are
pedagogically sound analogues for the concepts MiniMoney intends to
teach, or whether they risk teaching a distorted model of employment to
young children.

### 4. Parent-Facing Fintech UX / Family Product Designer

The case study assumes parents will engage with a recurring
invoice-and-payment loop ("the parent is automatically issued an
invoice... the parent is then required to make the payment") but
provides no description of what happens if a parent does not pay, nor
how disputes over task completion are resolved between parent and
child. A family-product UX expert is needed to design the trust and
enforcement mechanics that keep the "real money" promise credible to the
child even when the actual payment step happens outside the app's
direct control, since a broken promise here (parent doesn't pay) would
undermine the entire educational premise of the product.

### 5. Competitive/Market Analyst — Kids' Fintech Category

The case study contains no reference to any competing product,
pricing benchmark, or market sizing, despite describing a mechanic
(task-based earning tied to real bank payments, aimed at minors) that
sits in a category with existing, named competitors in the broader
market (debit-card-for-kids apps and family finance apps). A market
analyst is needed to establish where MiniMoney's payroll-simulation
mechanic (payslip, overtime, invoice) actually differs from and
improves upon whatever else exists in this space, since the case study
itself makes no differentiation claim and none can currently be
verified.
