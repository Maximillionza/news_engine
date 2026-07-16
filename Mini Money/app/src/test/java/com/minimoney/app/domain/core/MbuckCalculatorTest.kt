package com.minimoney.app.domain.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

/**
 * Pins the Mbuck Precision & Truncation Rule (BuildSpec). If any of these
 * fail after a refactor, the change violates a compliance-corrected spec —
 * do not "fix" the test.
 */
class MbuckCalculatorTest {

    // --- General rule: truncate, never round ---

    @Test
    fun `the BuildSpec worked example - 1 percent of R120 is 1 Mbuck, R0-20 dropped`() =
        assertEquals(1, MbuckCalculator.percentageOfBudget(120, 1))

    @Test
    fun `remainder just below the next whole Mbuck still truncates - never rounds up`() {
        assertEquals(1, MbuckCalculator.percentageOfBudget(199, 1)) // 1.99 -> 1
        assertEquals(3, MbuckCalculator.percentageOfBudget(79, 5)) // 3.95 -> 3
    }

    @Test
    fun `exact result passes through unchanged`() {
        assertEquals(2, MbuckCalculator.percentageOfBudget(200, 1))
        assertEquals(25, MbuckCalculator.percentageOfBudget(500, 5))
    }

    @Test
    fun `general rule has NO floor - sub-1 results truncate to zero`() =
        assertEquals(0, MbuckCalculator.percentageOfBudget(50, 1)) // 0.5 -> 0

    @Test
    fun `negative inputs rejected`() {
        assertThrows(IllegalArgumentException::class.java) {
            MbuckCalculator.percentageOfBudget(-1, 5)
        }
        assertThrows(IllegalArgumentException::class.java) {
            MbuckCalculator.percentageOfBudget(100, -1)
        }
    }

    // --- Task earn-rate: truncate THEN floor 0 -> 1 (the single exception) ---

    @Test
    fun `task earn-rate floors a zero truncation to 1`() =
        assertEquals(1, MbuckCalculator.taskEarnValue(50, 1)) // 0.5 -> 0 -> 1

    @Test
    fun `task earn-rate does not lift a non-zero truncation`() {
        assertEquals(1, MbuckCalculator.taskEarnValue(199, 1)) // 1.99 -> 1, floor moot
        assertEquals(3, MbuckCalculator.taskEarnValue(79, 5)) // 3.95 -> 3, not 4
    }

    @Test
    fun `task earn-rate rejects percent outside 1-100`() {
        assertThrows(IllegalArgumentException::class.java) {
            MbuckCalculator.taskEarnValue(100, 0)
        }
        assertThrows(IllegalArgumentException::class.java) {
            MbuckCalculator.taskEarnValue(100, 101)
        }
    }

    @Test
    fun `100 percent of budget equals budget - peg is 1 Mbuck per Rand`() =
        assertEquals(120, MbuckCalculator.taskEarnValue(120, 100))

    // --- Frequency-adjusted task earn-rate (PERCENTAGE): spreads the total across occurrences ---

    @Test
    fun `monthly occurrence count of 1 matches the two-argument overload exactly`() {
        assertEquals(
            MbuckCalculator.taskEarnValue(199, 1),
            MbuckCalculator.taskEarnValue(199, 1, occurrencesPerMonth = 1.0),
        )
        assertEquals(
            MbuckCalculator.taskEarnValue(50, 1),
            MbuckCalculator.taskEarnValue(50, 1, occurrencesPerMonth = 1.0),
        )
    }

    @Test
    fun `daily frequency divides the monthly total across 30 occurrences`() =
        // 30% of 3000 = 900 monthly total; 900 / 30 days = 30 per day, exact
        assertEquals(30, MbuckCalculator.taskEarnValue(3000, 30, occurrencesPerMonth = 30.0))

    @Test
    fun `frequency division that truncates to zero still floors to 1`() =
        // 1% of 100 = 1 monthly total; 1 / 30 days truncates to 0 -> floored to 1
        assertEquals(1, MbuckCalculator.taskEarnValue(100, 1, occurrencesPerMonth = 30.0))

    @Test
    fun `frequency division never rounds up - only the final zero is floored`() =
        // 10% of 1000 = 100 monthly total; 100 / 4 = 25 exact, no rounding involved
        assertEquals(25, MbuckCalculator.taskEarnValue(1000, 10, occurrencesPerMonth = 4.0))

    @Test
    fun `weekly's fractional 4point3 divisor truncates - the real-world reason occurrences is a Double`() =
        // 20% of 1000 = 200 monthly total; 200 / 4.3 = 46.5... -> truncates to 46
        assertEquals(46, MbuckCalculator.taskEarnValue(1000, 20, occurrencesPerMonth = 4.3))

    @Test
    fun `occurrencesPerMonth below 1 is rejected`() {
        assertThrows(IllegalArgumentException::class.java) {
            MbuckCalculator.taskEarnValue(100, 10, occurrencesPerMonth = 0.0)
        }
    }

    // --- Frequency-adjusted task earn-rate (FIXED): same truncate-then-floor discipline ---

    @Test
    fun `fixed-mode total divides evenly across occurrences`() =
        assertEquals(25, MbuckCalculator.taskEarnValueFixed(100, occurrencesPerMonth = 4.0))

    @Test
    fun `fixed-mode division truncates rather than rounds`() =
        // 100 / 30 = 3.33 -> truncates to 3
        assertEquals(3, MbuckCalculator.taskEarnValueFixed(100, occurrencesPerMonth = 30.0))

    @Test
    fun `fixed-mode division that truncates to zero still floors to 1`() =
        assertEquals(1, MbuckCalculator.taskEarnValueFixed(5, occurrencesPerMonth = 30.0))

    @Test
    fun `fixed-mode monthly occurrence count of 1 is a pure pass-through`() =
        assertEquals(100, MbuckCalculator.taskEarnValueFixed(100, occurrencesPerMonth = 1.0))

    @Test
    fun `fixed-mode rejects a negative total`() {
        assertThrows(IllegalArgumentException::class.java) {
            MbuckCalculator.taskEarnValueFixed(-1, occurrencesPerMonth = 1.0)
        }
    }

    // --- Task Tier model: weighted share of a tier pool, single final truncation ---

    @Test
    fun `tiered earn-rate reproduces the source doc's ages 10-13 daily-tier homework example`() =
        // 40% daily tier of a 3000 budget = 1200; weight 5 of totalWeight 10 -> 600 monthly;
        // 600 / 30 daily occurrences = 20 exact
        assertEquals(
            20,
            MbuckCalculator.tieredTaskEarnValue(
                budgetRand = 3000, tierBudgetSharePercent = 40,
                relativeWeight = 5, totalTierWeight = 10, occurrencesPerMonth = 30.0,
            ),
        )

    @Test
    fun `tiered earn-rate for a lone monthly task claims the whole tier`() =
        // 25% monthly tier of 1000, sole task (weight 1 of totalWeight 1) -> 250, /1 occurrence = 250
        assertEquals(
            250,
            MbuckCalculator.tieredTaskEarnValue(
                budgetRand = 1000, tierBudgetSharePercent = 25,
                relativeWeight = 1, totalTierWeight = 1, occurrencesPerMonth = 1.0,
            ),
        )

    @Test
    fun `tiered earn-rate floors a sub-1 result to 1 - small weight, small budget`() =
        // 40% of 100 = 40; weight 1 of 18 -> 2.22 monthly; / 30 daily = 0.074 -> truncates to 0 -> floor 1
        assertEquals(
            1,
            MbuckCalculator.tieredTaskEarnValue(
                budgetRand = 100, tierBudgetSharePercent = 40,
                relativeWeight = 1, totalTierWeight = 18, occurrencesPerMonth = 30.0,
            ),
        )

    @Test
    fun `tiered earn-rate rejects a weight exceeding the tier total`() {
        assertThrows(IllegalArgumentException::class.java) {
            MbuckCalculator.tieredTaskEarnValue(
                budgetRand = 1000, tierBudgetSharePercent = 40,
                relativeWeight = 20, totalTierWeight = 10, occurrencesPerMonth = 30.0,
            )
        }
    }

    @Test
    fun `tiered earn-rate rejects a tier share outside 0-100`() {
        assertThrows(IllegalArgumentException::class.java) {
            MbuckCalculator.tieredTaskEarnValue(
                budgetRand = 1000, tierBudgetSharePercent = 101,
                relativeWeight = 1, totalTierWeight = 1, occurrencesPerMonth = 1.0,
            )
        }
    }
}
