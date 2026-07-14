package com.minimoney.app.domain.dispute

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class DisputeSlaTest {

    private val hour = 60L * 60 * 1000

    @Test
    fun `48 hours exactly is inside the window - past means strictly beyond`() {
        assertFalse(DisputeSla.isPastWindow(0, 48 * hour))
        assertTrue(DisputeSla.isPastWindow(0, 48 * hour + 1))
    }

    @Test
    fun `capacity threshold trips on more than 5 concurrent past-window disputes`() {
        assertFalse(DisputeSla.capacityThresholdCrossed(5, null))
        assertTrue(DisputeSla.capacityThresholdCrossed(6, null))
    }

    @Test
    fun `capacity threshold trips on average response beyond 5 business days`() {
        assertFalse(DisputeSla.capacityThresholdCrossed(0, 5.0))
        assertTrue(DisputeSla.capacityThresholdCrossed(0, 5.1))
    }

    @Test
    fun `business days skip weekends`() {
        // Fri 2026-07-10 -> Tue 2026-07-14: Sat+Sun skipped = 2 business days.
        val zone = java.time.ZoneId.of("Africa/Johannesburg")
        val fri = java.time.ZonedDateTime.of(2026, 7, 10, 9, 0, 0, 0, zone).toInstant().toEpochMilli()
        val tue = java.time.ZonedDateTime.of(2026, 7, 14, 9, 0, 0, 0, zone).toInstant().toEpochMilli()
        assertEquals(2, DisputeSla.businessDaysBetween(fri, tue))
    }

    @Test
    fun `zero or negative span is zero business days`() {
        assertEquals(0, DisputeSla.businessDaysBetween(1000, 1000))
        assertEquals(0, DisputeSla.businessDaysBetween(2000, 1000))
    }
}
