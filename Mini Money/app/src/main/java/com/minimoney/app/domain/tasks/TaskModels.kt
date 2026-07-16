package com.minimoney.app.domain.tasks

/**
 * Per-task choice, not account-wide (BuildSpec §Data Model, Task — restored
 * 2026-07-14). TIER is a preset chosen from the Task Tier catalog
 * (TaskTemplates.kt): its rate is a relative weight inside a shared
 * daily/weekly/monthly budget pool, not a directly-editable percent — see
 * MbuckCalculator.tieredTaskEarnValue.
 */
enum class EarnMode { FIXED, PERCENTAGE, TIER }

enum class TaskStatus { ASSIGNED, COMPLETED, VERIFIED, DISPUTED }

/**
 * How often a task recurs, and which budget tier it draws from (Task Tier
 * doc, uploaded 2026-07-15). The entered rate — a total monthly percent for
 * FIXED/PERCENTAGE, or a relative weight for TIER — is spread across
 * `occurrencesPerMonth` to price a single instance (see MbuckCalculator).
 * Occurrence counts are fixed, calendar-approximate constants (30/4.3/1),
 * not exact day counts — an explicit open decision in the source doc, kept
 * as-is for simplicity. WEEKLY's 4.3 is why occurrencesPerMonth is a Double.
 */
enum class Frequency(val occurrencesPerMonth: Double, val tierBudgetSharePercent: Int) {
    DAILY(30.0, 40), WEEKLY(4.3, 35), MONTHLY(1.0, 25),
}

data class ChildTask(
    val id: Long,
    val childId: Long,
    val title: String,
    val earnMode: EarnMode,
    /** FIXED: whole Mbucks entered by parent. PERCENTAGE: whole-number percent 1..100. */
    val earnValue: Int,
    val frequency: Frequency,
    /**
     * The Mbuck amount, computed once at task-creation time from the budget
     * then in effect (PERCENTAGE mode, truncate-then-floor, frequency-divided)
     * or the frequency-divided earnValue (FIXED). A later budget change never
     * re-prices an existing task.
     */
    val mbuckValue: Int,
    val status: TaskStatus,
    val createdAtMillis: Long,
    val completedAtMillis: Long?,
    val verifiedAtMillis: Long?,
)
