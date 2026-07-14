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
}
