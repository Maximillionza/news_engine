package com.minimoney.app.domain.tasks

import com.minimoney.app.domain.child.AgeBand

/**
 * A preset chore from the Task Tier model (Task Tier.md, uploaded
 * 2026-07-15). `relativeWeight` is this task's share of its (ageBand, tier)
 * pool — NOT a directly-editable percent; the pool's total budget share
 * comes from `tier.tierBudgetSharePercent` (40/35/25) and is split among all
 * templates sharing the same ageBand+tier via their relative weights (see
 * totalWeightFor). A single task alone in its tier (e.g. the Monthly
 * check-in) implicitly claims 100% of that tier by having no siblings.
 *
 * AGE-BAND MAPPING CAVEAT: the source doc uses 6–9 / 10–13 / 14–18. This
 * app's AgeBand is 6–9 / 10–14 / 15–18 (PRD §Personas, three-tier model —
 * not something this feature should silently redefine). The 10–13 and
 * 14–18 tables below are mapped onto TEN_TO_FOURTEEN and FIFTEEN_TO_EIGHTEEN
 * respectively as the closest match; a 14-year-old currently sees the
 * "10–13" task set. Flagged for founder override, not resolved here.
 */
data class TaskTemplate(
    val title: String,
    val ageBand: AgeBand,
    val tier: Frequency,
    val relativeWeight: Int,
)

/**
 * PLACEHOLDER GAP: the source doc's Secondary tasks tier (uncapped extras,
 * e.g. 14–18 errand/babysitting) is deliberately NOT modeled here — it needs
 * its own defined budget base, separate from the primary budget, which the
 * doc itself flags as an open decision. Only the fully-specified Primary
 * (budget-capped) tier system below is implemented.
 */
val TASK_TEMPLATES: List<TaskTemplate> = listOf(
    // --- Ages 6-9 ---
    TaskTemplate("Make bed", AgeBand.SIX_TO_NINE, Frequency.DAILY, relativeWeight = 2),
    TaskTemplate("Brush teeth (both times)", AgeBand.SIX_TO_NINE, Frequency.DAILY, relativeWeight = 1),
    TaskTemplate("Pack school bag", AgeBand.SIX_TO_NINE, Frequency.DAILY, relativeWeight = 2),
    TaskTemplate("Feed pet", AgeBand.SIX_TO_NINE, Frequency.DAILY, relativeWeight = 3),
    TaskTemplate("Tidy toys", AgeBand.SIX_TO_NINE, Frequency.DAILY, relativeWeight = 3),
    TaskTemplate("Set the table", AgeBand.SIX_TO_NINE, Frequency.DAILY, relativeWeight = 2),
    TaskTemplate("Read for 15 min", AgeBand.SIX_TO_NINE, Frequency.DAILY, relativeWeight = 5),
    TaskTemplate("Weekly room tidy (deeper clean)", AgeBand.SIX_TO_NINE, Frequency.WEEKLY, relativeWeight = 1),
    // Monthly tier unclaimed for this age band (25% unassigned per source doc).

    // --- Ages 10-13, mapped onto TEN_TO_FOURTEEN (see class doc above) ---
    TaskTemplate("Homework completed on time", AgeBand.TEN_TO_FOURTEEN, Frequency.DAILY, relativeWeight = 5),
    TaskTemplate("Dishes after dinner", AgeBand.TEN_TO_FOURTEEN, Frequency.DAILY, relativeWeight = 5),
    TaskTemplate("Take out trash", AgeBand.TEN_TO_FOURTEEN, Frequency.WEEKLY, relativeWeight = 8),
    TaskTemplate("Vacuum a room", AgeBand.TEN_TO_FOURTEEN, Frequency.WEEKLY, relativeWeight = 15),
    TaskTemplate("Water plants/garden", AgeBand.TEN_TO_FOURTEEN, Frequency.WEEKLY, relativeWeight = 5),
    TaskTemplate("Laundry (sort + fold own clothes)", AgeBand.TEN_TO_FOURTEEN, Frequency.WEEKLY, relativeWeight = 20),
    TaskTemplate("Help with grocery unpacking", AgeBand.TEN_TO_FOURTEEN, Frequency.WEEKLY, relativeWeight = 10),
    TaskTemplate("Budget check-in with parent", AgeBand.TEN_TO_FOURTEEN, Frequency.MONTHLY, relativeWeight = 1),

    // --- Ages 14-18, mapped onto FIFTEEN_TO_EIGHTEEN (see class doc above) ---
    // Daily tier unclaimed for this age band (40% unassigned per source doc).
    TaskTemplate("Cook a family meal", AgeBand.FIFTEEN_TO_EIGHTEEN, Frequency.WEEKLY, relativeWeight = 40),
    TaskTemplate("Mow lawn/yard work", AgeBand.FIFTEEN_TO_EIGHTEEN, Frequency.WEEKLY, relativeWeight = 50),
    TaskTemplate("Deep clean bathroom", AgeBand.FIFTEEN_TO_EIGHTEEN, Frequency.WEEKLY, relativeWeight = 30),
    TaskTemplate("Car washing", AgeBand.FIFTEEN_TO_EIGHTEEN, Frequency.WEEKLY, relativeWeight = 40),
    TaskTemplate(
        "Tutor/help younger sibling with homework",
        AgeBand.FIFTEEN_TO_EIGHTEEN,
        Frequency.WEEKLY,
        relativeWeight = 30,
    ),
    TaskTemplate(
        "Manage own budget plan / savings goal review",
        AgeBand.FIFTEEN_TO_EIGHTEEN,
        Frequency.MONTHLY,
        relativeWeight = 1,
    ),
)

fun templatesFor(ageBand: AgeBand): List<TaskTemplate> = TASK_TEMPLATES.filter { it.ageBand == ageBand }

/** Sum of relative weights for every template sharing this (ageBand, tier) pool. */
fun totalWeightFor(ageBand: AgeBand, tier: Frequency): Int =
    TASK_TEMPLATES.filter { it.ageBand == ageBand && it.tier == tier }.sumOf { it.relativeWeight }
