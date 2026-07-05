# Developing Committee — Templates

> Activates only on Verdict = Proceed or Proceed with Changes.

---

## TraceabilityMatrix.md
Every risk/assumption from Verdict.md must appear here exactly once.

| Investment Committee item | Addressed in spec section | OR: Accepted risk, not addressed, because... |
|---|---|---|
| | | |

Rule: a row with neither column filled is a process violation. This file
is checked BEFORE PRD.md is considered final.

---

## PRD.md
- Product summary (one paragraph, no ambiguity)
- User personas and age/context bands (if applicable — do not merge
  distinct user cohorts into one persona)
- Core features (prioritized, MVP vs later)
- Explicit non-goals (what this build deliberately does NOT do yet)
- Success metrics (numeric, falsifiable)
- Open technical decisions: NONE remaining — if any exist, resolve them
  here before handoff, do not defer to Claude Code

---

## BuildSpec.md
- Architecture overview
- Data model
- Screens/flows (if applicable)
- Third-party dependencies and why each was chosen
- Compliance requirements translated into concrete technical constraints
  (e.g., "child data: no third-party analytics SDK without parental
  consent flow" — not just "comply with COPPA")
- Anything the Incubator over-specified that this Committee has trimmed,
  with a one-line reason per trim

---

## ExecutionInstructions.md
Written directly to the user, plain language:
- What to open (Claude Code / Cowork) and what folder to point it at
- What files it needs (list, with confirmation they exist and are final)
- The exact first instruction to give Claude Code to begin execution
- What the user should check after each major milestone
- What NOT to touch mid-build (files considered locked/final)
