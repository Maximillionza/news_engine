# COSTS.md — TradeWise Cost Baseline (for Price Ratification)

**Version:** 1.0
**Owner:** Masood
**Dated:** 2026-08-29
**Read alongside:** MONETISATION.md, ROADMAP.md, ARCHITECTURE.md

**Purpose:** every priced item in MONETISATION.md and ROADMAP.md Phase 6 was set by feel, not against real vendor cost. This document prices the vendors, prices the store's own cut, and re-runs the existing price points through both — so pricing decisions are made against actual margin, not gross revenue. Vendor figures below are current as of 2026-08-29 web pricing pages; [Certain] = read directly off the vendor's own pricing page this session, [Likely] = strong inference from vendor pages or well-established public figures not directly re-fetched, [Guessing] = usage-pattern-dependent estimate that needs real telemetry to firm up.

---

## 0. The headline finding

**The single biggest correction this document makes: none of the price points in MONETISATION.md or ROADMAP.md Phase 6 account for the Apple/Google store commission.** Every dollar that moves through RevenueCat's in-app purchase or subscription rails gets a cut taken before TradeWise sees it. At TradeWise's projected revenue (well under the $1M/year threshold — see §3), that cut is **15%**, not the headline 30% figure most people default to — but it is not zero, and right now it is priced as zero everywhere in the doc set. [Certain]

This matters most in the Mentor Program, where a second split (the flat $1.00/user Mentor payout) is stacked on top of the store's cut. Worked through in §5, the platform's actual retained margin on a Mentor's discounted-tier member drops from the documented $0.50/user to about **$0.275/user** — a 45% reduction — and the $299 package's assumed ~$50 profit collapses to roughly **$4** once the store's cut is taken off the top. [Certain] on the mechanism, [Likely] on the exact cents (depends on whether the $299 charge and the $1.99/$1.50 subscriptions go through IAP at all, or through a web-based Stripe checkout outside the app stores — see §5's note on this).

---

## 1. Store commission (applies to every dollar sold through RevenueCat/IAP)

| Item | Rate | Source |
|---|---|---|
| Apple App Store Small Business Program | **15%** on all proceeds, for developers under $1M/year in prior-year proceeds | [developer.apple.com](https://developer.apple.com/app-store/small-business-program/) |
| Apple standard rate (if $1M/year threshold is crossed) | 30% | [RevenueCat: The 15% App Store Fee](https://www.revenuecat.com/blog/engineering/small-business-program) |
| Google Play equivalent program | 15% under the same style of small-business threshold, 30% standard | [Appbot: App developers' Apple/Google small business programs](https://appbot.co/blog/app-developers-apple-google-small-business-programs/) |
| Apple Developer Program | $99/year, flat, regardless of revenue | Well-established, stable figure [Likely] |
| Google Play Console registration | $25, one-time, flat | Well-established, stable figure [Likely] |

**Both of TradeWise's revenue projection scenarios in MONETISATION.md §6 (~$1,300/month conservative, ~$12,000/month moderate) are far under the $1M/year proceeds threshold**, so 15% is the correct rate to model against — not 30%. Confirm you've actually enrolled in both small-business programs before launch; it isn't automatic. [Certain]

**Correction to MONETISATION.md §6:** the "Total monthly revenue" row (~$1,300 conservative / ~$12,000 moderate) is gross, pre-commission. Net to TradeWise before any infrastructure cost: **~$1,105/month (conservative)**, **~$10,200/month (moderate)**. Worth relabeling that row "Gross revenue" and adding a "Net of store commission" row underneath.

---

## 2. Payment/subscription infrastructure — RevenueCat

| Tier | Cost |
|---|---|
| Free | $0 up to $2,500/month in tracked revenue |
| Above threshold | 1% of tracked monthly revenue |

Source: [revenuecat.com/pricing](https://www.revenuecat.com/pricing/) [Certain]

- Conservative scenario (~$1,300/month gross): **$0/month** — under the free threshold.
- Moderate scenario (~$12,000/month gross): **roughly $95–120/month**, depending on whether the 1% applies only to the amount above $2,500 or to the whole tracked total once you cross it (RevenueCat's own copy is ambiguous on this point — worth a direct question to their sales team before budgeting it precisely). [Guessing] on the exact mechanic, [Likely] on the order of magnitude.

Either way, RevenueCat is immaterial next to the store commission above.

---

## 3. Backend infrastructure — Supabase

Source: [supabase.com/pricing](https://supabase.com/pricing), fetched 2026-08-29. [Certain] on the figures, [Guessing] on which usage tier TradeWise actually lands in (depends on real telemetry, not yet available pre-launch).

| Plan | Base | DB included | Egress included | Storage included | Edge fn invocations | MAU included |
|---|---|---|---|---|---|---|
| Free | $0 | 500MB | 5GB | 1GB | 500K | 50K |
| Pro | $25/mo | 8GB (then $0.125/GB) | 250GB (then $0.09/GB) | 100GB (then $0.0213/GB) | 2M (then $2/1M) | 100K (then $0.00325/MAU) |
| Team | $599/mo | same as Pro | same as Pro | same as Pro | same as Pro | same as Pro |

**Recommendation:** dev + staging on separate Free-tier projects ($0 total — ARCHITECTURE.md §0.5 already calls for separate dev/staging projects, and neither needs production-scale headroom). Production on Pro ($25/month base).

**Both revenue-projection scenarios (10,000 MAU conservative, 50,000 MAU moderate) fit inside Pro's 100,000-MAU-included ceiling** — MAU overage isn't a near-term concern. [Certain]

**The real cost driver is egress, and it isn't in any existing doc.** ARCHITECTURE.md §5 has each new user downloading ~15 datasets at ~8MB each after the 5 bundled-in-binary ones — **~120MB of Supabase Storage egress per newly-onboarded user**, before any dataset re-download from a reinstall or a new device. At 10,000 new users/month that's ~1.2TB — **~950GB over the 250GB Pro allowance, ≈ $85/month in overage**. At 50,000 new users/month (moderate scenario, assuming most of that MAU figure is net-new rather than returning) that scales roughly linearly toward ~$500+/month. [Guessing] — this depends heavily on how many of the "MAU" figure are new installs vs. returning users with datasets already cached locally in SQLite, which the existing docs don't model. **Worth instrumenting dataset re-download rate in beta before trusting a number here.**

**Estimated total Supabase cost:** ~$25–110/month (conservative scenario), ~$25–500+/month (moderate scenario, wide range pending real egress data).

---

## 4. Observability and build infrastructure

| Service | Free tier | Paid tier | Likely needed at TradeWise's scale? |
|---|---|---|---|
| PostHog (analytics) | 1M events/month | Usage-based above that, rate not published — "talk to sales" | [Guessing] Conservative scenario probably stays free; Moderate scenario (50K MAU × ~4 sessions/week × ~10 tracked events/session ≈ 8–9M events/month) almost certainly exceeds the free tier. Budget an unknown, sales-quoted figure — order-of-magnitude guess: low hundreds of dollars/month. |
| Sentry (crash/error tracking) | 5K errors/month, 1 user | Team: $26/month, 50K errors, unlimited users | [Likely] Team tier needed once the app has any real user base, target crash rate <1% keeps this affordable. |
| Expo EAS (build + OTA updates) | 15 builds/month combined, 1,000 MAU OTA, 60 CI/CD minutes | Starter $19/mo (3,000 MAU OTA) → Production **$199/month** (50,000 MAU OTA, $225 build credit) | **[Certain] on the numbers, and this is a real finding: even the conservative 10,000-MAU scenario blows past the Free and Starter tiers' OTA-update MAU caps, meaning Production tier ($199/month) is required from day one of any real launch, not an eventual upgrade.** This is a previously-undocumented ~$200/month fixed cost. |

Sources: [posthog.com/pricing](https://posthog.com/pricing), [sentry.io/pricing](https://sentry.io/pricing/), [expo.dev/pricing](https://expo.dev/pricing).

---

## 5. Mentor Program economics — recalculated with store commission

This re-runs ROADMAP.md §6.1's numbers with the 15% store commission applied, which is the specific gap ROADMAP.md already flagged as unresolved ("platform fee (15–30%) applies before any split... doesn't yet account for [it]"). This section resolves that flag with real numbers.

**Assumption, stated explicitly:** the Mentor subscription and member subscriptions are sold as in-app subscriptions through RevenueCat/IAP, same as everything else in MONETISATION.md. If instead Mentor billing runs through a web-based Stripe checkout outside the app stores (permitted under recent Apple/Google external-payment-link rulings in some regions, but a materially different build and a policy question worth its own decision), the 15% store cut doesn't apply and Stripe's own ~2.9%+30¢ processing fee applies instead — a very different, much smaller cut. **This is a decision to make, not an assumption to inherit** — flagging it rather than picking one silently, per the open-questions pattern already used in ROADMAP.md.

| Price point | Gross | After 15% store cut | After $1.00 flat Mentor payout | **Platform's real margin** | Currently documented as |
|---|---|---|---|---|---|
| Mentor subscription | $9.99/mo | $8.49 | — (Mentor doesn't get paid from their own sub) | **$8.49/mo** | Not previously netted against store cut |
| Member, standard tier | $1.99/mo | $1.69 | $1.69 − $1.00 | **$0.69/mo** | Documented as $0.99/mo — **30% lower than assumed** |
| Member, 50+ discount tier | $1.50/mo | $1.275 | $1.275 − $1.00 | **$0.275/mo** | Documented as $0.50/mo — **45% lower than assumed** |
| $299 Mentor Package | $299 (cadence TBD) | $254.15 | n/a — the 250 bundled members aren't separately billed, so no per-user split applies to them | **$254.15**, of which ~$250 is earmarked to "cover" the 250 free members' notional value | Masood's math assumed ~$254 remaining margin ($9.99 mentor-fee value + ~$40); after the store cut, only **~$4.15** is left once the $250 bucket is set aside — **the assumed ~$50 margin collapses to ~$4, a >90% reduction** |

**Why the discount-tier margin matters most:** at $0.275/user retained, the platform's margin on a discounted-tier member doesn't even cover the Stripe Connect payout fee for disbursing the Mentor's $1.00 (see below) unless payouts are batched across many members at once. A Mentor with a small cohort could cost more to pay out than the platform retains from that cohort.

**New cost this section surfaces — paying Mentors out.** ROADMAP.md already logs "payment split infrastructure" as an open item without a number. Stripe Connect, the most likely mechanism (source: [stripe.com/connect/pricing](https://stripe.com/connect/pricing), fetched 2026-08-29 — [Certain]):

- **"Stripe handles pricing" model:** no payout fee to the platform — Stripe bills the connected account (the Mentor) directly for processing. Simplest, but means Mentors see Stripe's own cut on their payout, which is a Mentor-experience decision, not just a cost one.
- **"You handle pricing" model:** platform pays **0.25% + $0.25 per payout**, plus **$2.00 per month per active connected account** (i.e., per Mentor who received a payout that month).

At $2.00 + ~$0.25 per Mentor per month in Stripe fees against a payout of $1.00 × (however many members that Mentor has), **a Mentor needs roughly 3+ paying members before the platform isn't losing money just to pay them.** This is a real constraint on the Mentor Program's minimum viable cohort size that doesn't exist in the current docs. [Certain] on the fee structure, [Likely] on the practical threshold (depends on batching frequency and whether payouts are monthly).

---

## 6. Content and data costs (labor-based — not vendor-priceable from here)

- **Historical OHLCV data** (Dukascopy or HistData, per ROADMAP.md §0.3): both are free or near-free for retail-volume historical tick/candle data at the 180-day EURUSD scope specified. [Likely] — no material line item.
- **Trader review and dataset curation** (Phase 0.2/0.3 trader sign-off, ongoing 3–5 datasets/month post-launch per ROADMAP.md's Content Production Pipeline): this is a day-rate or per-dataset contractor cost, not a vendor subscription — I can't web-search a number for what Masood pays a trader for review time. **This needs Masood's own figure**, since it depends on who's doing the reviewing and at what arrangement.
- **South African FAIS + gambling legal opinion** (ROADMAP.md §0.9, "attorney engaged, retainer paid"): a specific-firm retainer, not something to estimate from general web pricing — already in motion per the roadmap, actual figure is whatever the retainer states.

---

## 7. Live Event Hosting (Phase 6 — not urgent, priced here for completeness)

Two modes per ROADMAP.md §6.2, each with a genuinely different cost shape:

**Locked/broadcast mode** (one-to-many, no interaction) — Cloudflare Stream, fetched 2026-08-29, [Certain]:
- Storage: **$5.00 per 1,000 minutes stored**
- Delivery: **$1.00 per 1,000 minutes delivered**
- Worked example: a 60-minute event watched by 50 viewers = 3,000 viewer-minutes delivered ≈ $3.00, plus $5.00 if recorded and stored — **~$8 total for a small event**. Scales cheaply; broadcast delivery cost is dominated by audience size × duration, not complexity.
- Mux is a comparable alternative at a similar per-minute order of magnitude (their pricing page quotes delivery starting around $0.0024/min for on-demand, live simulcast at $0.02/min per simulcast target) — worth a side-by-side quote once event frequency is real, not urgent now.

**Interactive mode** (multi-party, optional video, Q&A chat) — LiveKit Cloud, fetched 2026-08-29, [Certain]:
- Free tier: 1,000 minutes included, no card required.
- Paid (Ship plan): **$50/month minimum**, then **$0.0005/participant-minute**.
- Worked example: a 60-minute interactive session with 20 live participants = 1,200 participant-minutes ≈ $0.60 — **trivial against the $50/month plan minimum**, meaning cost is dominated by the flat monthly fee, not usage, until event volume is significant.
- Agora, Daily.co, and 100ms weren't fetched to the same numeric precision this pass — same order of magnitude expected, worth a direct quote comparison when Phase 6 is actually scheduled, not now.

**Bottom line for Phase 6:** neither mode is expensive at TradeWise's likely event scale. The real cost of Phase 6 is the build (a second client surface, a moderation pipeline, a payout system) — not the streaming vendor bill.

---

## 8. Summary — cost against current price points

| Price point | Gross | Store cut (15%) | Other costs | **Net margin** |
|---|---|---|---|---|
| Advanced Course (one-time) | $6.99 | $1.05 | ~$0 marginal (no incremental infra) | **~$5.94 (85%)** |
| TradeWise Pro (mid-range $9.99/mo) | $9.99 | $1.50 | ~$0–1 allocated infra per user | **~$7.50–8.49 (75–85%)** |
| Mentor subscription | $9.99/mo | $1.50 | — | **~$8.49 (85%)** |
| Mentor's member, standard | $1.99/mo | $0.30 | $1.00 to Mentor | **~$0.69 (35%)** — not $0.99 as documented |
| Mentor's member, 50+ discount | $1.50/mo | $0.225 | $1.00 to Mentor, ~$2/mo Stripe Connect fee shared across cohort | **~$0.275 or less (18%)** — not $0.50 as documented |
| $299 Mentor Package | $299 | $44.85 | ~$250 notionally earmarked for the 250 free members | **~$4.15 realized margin, not ~$50** |

Fixed monthly infrastructure floor (production, before any user-count scaling): **Supabase Pro $25 + Expo EAS Production $199 + Sentry Team $26 ≈ $250/month**, before PostHog and RevenueCat overage, which only appear at real scale.

---

## 9. What this document does NOT resolve

- The RevenueCat-vs-Stripe billing-rail decision for Mentor Program payments (§5) — changes every Mentor-Program number materially and needs a decision, not an assumption.
- Exact PostHog overage pricing (sales-quoted, not published).
- Trader/curator labor rates (Masood's own figures, not web-priceable).
- The legal retainer figure (already committed, not a market rate to research).
- Whether the platform's own 15%-vs-30% store rate stays at 15% as revenue grows — re-check annually against the $1M/year proceeds threshold.

Nothing has been changed in MONETISATION.md's actual price points — this is a cost baseline to ratify against, not a repricing. The clearest candidates for a price change, based on the numbers above, are the Mentor's 50+ discount tier (margin nearly gone once real costs are counted) and the $299 package (assumed profit mostly evaporates) — worth deciding deliberately rather than carrying the old assumptions forward.
