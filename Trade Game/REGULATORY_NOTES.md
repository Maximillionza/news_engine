# REGULATORY_NOTES.md — TradeWise Regulatory and Compliance Notes

**Version:** 0.2  
**Owner:** Masood  
**Status:** Research-level notes. NOT legal advice. Qualified legal review required per jurisdiction before launch.

---

## Core Product Classification

TradeWise MVP is a **simulated trading education application**:
- No real money
- No real trades
- No live market data
- No broker relationship
- No financial advice

This classification is the legal shield. Every feature is evaluated against whether it preserves this classification.

The removal of ads (vs prior version) slightly simplifies the regulatory picture (no GDPR consent management platform needed for ad tracking). The introduction of IAP and subscriptions is standard for App Store/Play Store apps and is not a regulatory concern.

---

## 1. Features That Require Specific Legal Review

| Feature | Risk | Status |
|---|---|---|
| Competitions with cash prizes | May classify as gambling in multiple jurisdictions | **Build gate — see Section 4** |
| Career Readiness Rating | Could be construed as a qualification | Mitigated by disclaimer on every display |
| Practice Capital balance display | Could be confused for real funds | Mitigated by "Practice Capital" labelling + persistent disclaimer |
| Broker referral (Post-MVP) | May require financial services registration as lead generator | Legal review required per jurisdiction before building |
| Cross-app fund transfers | Simulated funds only — but must never be confused with real money | Clear labelling + ToS explicit on simulated nature |
| PropWise/CompWise mini-games | Simulated investment returns — not real investment advice | Disclaimer required on all return displays |

---

## 2. Jurisdiction Risk Map

### South Africa (FSCA — Financial Sector Conduct Authority)

- **FAIS risk:** If TradeWise is construed as providing financial advice or intermediary services, an FSP licence is required. Mitigated by: not recommending specific trades, not connecting to brokers, purely simulated.
- **Gambling risk:** Cash prize competitions may require a licence under the National Gambling Act depending on structure (element of chance vs pure skill).
- **POPIA:** South African user data must comply with the Protection of Personal Information Act. Privacy policy, Information Officer registration may be required.
- **Action:** Obtain FAIS + gambling legal opinion from SA regulatory attorney before launch.

### United Kingdom (FCA)

- **Financial promotion risk:** Content that encourages people to trade could be classified as a financial promotion under FSMA 2000. Must either be FCA-authorised or fall within an exemption. Education about trading ≠ promotion to trade — but this line needs a legal opinion to confirm.
- **Gambling risk:** Cash prize competitions where outcome has an element of chance require UK Gambling Commission licence.
- **Action:** UK legal opinion required before launch. Cash prize legal opinion before Post-MVP Phase 1.

### European Union (ESMA)

- **MiFID II risk:** ESMA has specifically flagged gamified trading apps as potentially falling under investment services regulation. Key test: is the app providing investment advice or portfolio management?
- **GDPR:** Any EU user data requires GDPR compliance. Privacy policy, lawful basis for processing, right to erasure, data residency (set Supabase region to EU).
- **Action:** EU legal opinion (minimum: Germany and France as largest markets) before launch.

### United States (SEC, CFTC, State regulators)

- **Complexity:** Highest regulatory complexity globally. CFTC has jurisdiction over Forex-adjacent products. SEC over securities-adjacent. Investment Adviser Act may apply if app is construed as advice.
- **Recommendation:** US-specific legal review before launch. Consider delaying US availability until legal is confirmed, or geofencing competitions away from US users.

### Australia (ASIC)

- **AFSL risk:** Australian Financial Services Licence may be required if the app is construed as providing financial product advice.
- **Action:** ASIC legal opinion before launch.

---

## 3. Disclaimer Requirements

Disclaimers are a UX feature, not a legal footnote.

### Required Content (every disclaimer instance)

1. TradeWise is a simulated trading education app. No real money is involved.
2. Simulated performance does not predict or reflect live trading performance.
3. Nothing in this app constitutes financial advice, investment advice, or a recommendation to trade.
4. Trading real financial instruments involves substantial risk of loss.
5. The Career Readiness Rating reflects simulated practice quality only. It is not a qualification, certification, or endorsement of any kind.
6. PropWise and CompWise mini-games are fictional simulations. Returns shown are simulated and do not represent real investment returns.

### Placement Requirements

| Location | Disclaimer type |
|---|---|
| Onboarding | Full disclaimer. Active acceptance (checkbox). Cannot be skipped. |
| Career Mode session screen | Persistent one-liner: "Practice Capital — simulated, not real money" |
| Career Readiness Rating display | One-liner below score: "Simulated practice performance only." |
| PropWise mini-game returns display | One-liner: "Simulated returns — not real investment performance." |
| CompWise mini-game revenue display | Same as PropWise. |
| Any milestone badge implying competence | Contextual: "This badge reflects simulated practice performance." |
| Competition entry (Post-MVP) | Full disclaimer before entry. |
| Broker referral screen (Post-MVP) | Full disclaimer + "TradeWise may receive a referral fee." |

### What Disclaimers Must NOT Do
- Must not be buried in ToS that users scroll past
- Must not appear only at first launch and nowhere else
- Must not use language that implies the disclaimer is optional or irrelevant

---

## 4. Competitions with Cash Prizes — Build Gate

**No technical build of cash prize competitions until ALL of the following are complete:**

- [ ] South Africa: legal opinion received (FAIS + gambling)
- [ ] United Kingdom: legal opinion received (FCA + Gambling Commission)
- [ ] European Union: legal opinion received (Germany + France minimum)
- [ ] United States: legal opinion received OR US users explicitly excluded from cash prize competitions
- [ ] Australia: legal opinion received OR AU users excluded
- [ ] ToS updated with competition-specific terms (entry conditions, prize structure, tax obligations)
- [ ] Prize payment infrastructure confirmed (tax reporting requirements per jurisdiction)
- [ ] Age verification mechanism in place (18+ required for gambling-classified features)

**Safe alternative for MVP competitions:** In-app rewards only (Pro subscription credit, cosmetic items, bonus TradePoints). These carry negligible regulatory risk.

---

## 5. Age Requirements

- Minimum account age: **18 years**
- Self-declared in MVP (honour system)
- If cash prize competitions launch: age verification via third-party service required
- App Store / Play Store age rating: 17+ (simulated financial content)
- All marketing must not target minors

---

## 6. In-App Purchases — App Store Compliance

**Apple App Store:**
- Virtual currency (TradePoints) policy: TradePoints are not purchasable with real money. Confirm this stays true if Monetisation.md changes.
- IAP must use StoreKit. RevenueCat handles this correctly.
- No real-money gambling features without Apple review and appropriate rating.

**Google Play Store:**
- Same principles apply.
- "Real-money gambling" classification: avoided by keeping all in-game economies simulated.
- Policy on simulated gambling: apps that simulate casino or gambling experiences require age 18+ rating.

---

## 7. Data Protection

| Regulation | Jurisdiction | Requirement |
|---|---|---|
| POPIA | South Africa | Privacy policy. Information Officer registration. Lawful basis for processing. |
| GDPR | EU | Privacy policy. Lawful basis. Right to erasure (account deletion must anonymise). Data residency (EU Supabase region). |
| CCPA | California, USA | Privacy policy with opt-out rights. If US users are served. |

**Account deletion:** Must anonymise (not just soft-delete) personal data within 30 days of request. TradeWise-specific: anonymise username, email, country. Retain anonymised gameplay data for analytics (legitimate interest basis — no PII).

**Data retention policy:**
- Personal data: deleted/anonymised 30 days after account deletion request
- Anonymised gameplay data: retained indefinitely for product analytics
- Payment data: never stored in TradeWise (RevenueCat handles; their retention policy applies)

---

## 8. Cross-App Ecosystem — Additional Considerations

The TradeWise → PropWise → CompWise ecosystem shares a single Supabase project and authentication. This creates a data controller question: is each app a separate data controller, or is there one controller for the ecosystem?

**Recommended approach:** One privacy policy covers all three apps (as they share identity and data). The policy discloses that progress and funds may be shared across TradeWise, PropWise, and CompWise apps when using the same account. Users consent to this at TradeWise onboarding.

The simulated fund transfer mechanic (PropFunds/BizFunds to Career Mode) does not constitute real money movement. The ToS must explicitly state this: "All funds, balances, and transfers within the TradeWise, PropWise, and CompWise apps are fictional and hold no real-world monetary value."
