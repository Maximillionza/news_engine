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
        val truncated = percentageOfBudget(budgetRand, percent)
        return if (truncated == 0) 1 else truncated
    }
}
