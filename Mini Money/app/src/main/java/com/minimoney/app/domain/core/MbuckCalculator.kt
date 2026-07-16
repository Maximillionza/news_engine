package com.minimoney.app.domain.core

/**
 * Mbuck Precision & Truncation Rule (BuildSpec §Mbuck Precision & Truncation
 * Rule, corrections 2026-07-13/14). Mbuck amounts are whole integers
 * everywhere; percentage-derived values are TRUNCATED toward zero — never
 * rounded, never carried forward, no remainder tracking. The task earn-rate
 * is the single stated exception: after truncation, 0 is floored to 1.
 * That floor is NOT a general license to round up elsewhere.
 */
object MbuckCalculator {

    /** General rule: budget × percent / 100, fractional remainder dropped. */
    fun percentageOfBudget(budgetRand: Int, percent: Int): Int {
        require(budgetRand >= 0) { "budget must be non-negative" }
        require(percent >= 0) { "percent must be non-negative" }
        // Integer division IS the truncation — do not replace with any rounding call.
        return (budgetRand * percent) / 100
    }

    /**
     * Task earn-rate (PERCENTAGE mode) only. Order of operations per BuildSpec:
     * (1) truncate toward zero; (2) if the truncated result is 0, set it to 1.
     */
    fun taskEarnValue(budgetRand: Int, percent: Int): Int {
        require(percent in 1..100) { "task percentage must be a whole number 1..100" }
        return distributeAcrossOccurrences(percentageOfBudget(budgetRand, percent), occurrencesPerMonth = 1.0)
    }

    /**
     * Frequency-adjusted task earn-rate (PERCENTAGE mode). `percent` is the
     * task's TOTAL intended share of the monthly budget; occurrencesPerMonth
     * spreads that total across each instance. With occurrencesPerMonth == 1.0
     * this is identical to the two-argument overload above.
     */
    fun taskEarnValue(budgetRand: Int, percent: Int, occurrencesPerMonth: Double): Int {
        require(percent in 1..100) { "task percentage must be a whole number 1..100" }
        return distributeAcrossOccurrences(percentageOfBudget(budgetRand, percent), occurrencesPerMonth)
    }

    /**
     * Frequency-adjusted task earn-rate (FIXED mode). `totalMbucks` is the
     * parent's stated TOTAL intended payout per month; occurrencesPerMonth
     * spreads it across each instance. Same truncate-then-floor discipline
     * as the percentage path, since this is now a computed rate rather than
     * a direct pass-through of the parent's input.
     */
    fun taskEarnValueFixed(totalMbucks: Int, occurrencesPerMonth: Double): Int {
        require(totalMbucks >= 0) { "total must be non-negative" }
        return distributeAcrossOccurrences(totalMbucks, occurrencesPerMonth)
    }

    /**
     * Task Tier model (Task Tier.md, uploaded 2026-07-15): a preset's rate is
     * its relative weight within a shared tier pool, not a directly-entered
     * percent. `tierBudgetSharePercent` is the tier's whole-percent slice of
     * the monthly budget (Frequency.tierBudgetSharePercent — 40/35/25);
     * `relativeWeight`/`totalTierWeight` splits that slice among the tier's
     * tasks; `occurrencesPerMonth` then spreads one task's monthly share
     * across its instances. This composes into a single fraction with no
     * meaningful intermediate whole-Mbuck checkpoint (the weight share alone
     * is a percent of a percent, generally sub-1%), so — unlike the two
     * functions above — it is truncated exactly ONCE, at the final whole-
     * Mbuck conversion, then floored 0->1 like any other task earn-rate.
     */
    fun tieredTaskEarnValue(
        budgetRand: Int,
        tierBudgetSharePercent: Int,
        relativeWeight: Int,
        totalTierWeight: Int,
        occurrencesPerMonth: Double,
    ): Int {
        require(budgetRand >= 0) { "budget must be non-negative" }
        require(tierBudgetSharePercent in 0..100) { "tier share must be 0..100" }
        require(relativeWeight >= 1) { "relative weight must be at least 1" }
        require(totalTierWeight >= relativeWeight) { "total tier weight must be at least this task's weight" }
        require(occurrencesPerMonth >= 1.0) { "occurrencesPerMonth must be at least 1" }

        val exact = budgetRand.toDouble() *
            (tierBudgetSharePercent / 100.0) *
            (relativeWeight.toDouble() / totalTierWeight) /
            occurrencesPerMonth
        val truncated = exact.toInt() // toInt() truncates toward zero for non-negative values
        return if (truncated == 0) 1 else truncated
    }

    /**
     * Single truncation via Double division, then the 0->1 floor. Equivalent
     * to truncating the monthly total first and dividing that truncated
     * integer by occurrencesPerMonth WHEN occurrencesPerMonth is a whole
     * number (floor(floor(x)/n) == floor(x/n) for positive integer n) — but
     * this form is also correct for WEEKLY's fractional 4.3 divisor, which
     * plain integer division cannot express.
     */
    private fun distributeAcrossOccurrences(monthlyTotal: Int, occurrencesPerMonth: Double): Int {
        require(occurrencesPerMonth >= 1.0) { "occurrencesPerMonth must be at least 1" }
        val perOccurrence = (monthlyTotal / occurrencesPerMonth).toInt()
        return if (perOccurrence == 0) 1 else perOccurrence
    }
}
