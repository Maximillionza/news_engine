package com.minimoney.app.domain.dispute

import java.time.DayOfWeek
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId

enum class DisputeStatus { OPEN, ACCEPTED, DECLINED, ESCALATED }

data class Dispute(
    val id: Long,
    val taskId: Long,
    val openedAtMillis: Long,
    val status: DisputeStatus,
    val resolvedAtMillis: Long?,
)

/**
 * Dispute SLA and the interim manual founder-review capacity threshold —
 * computed fields, not hardcoded UI copy (BuildSpec §Data Model, Dispute;
 * §Operations). Threshold resolved by the Developing Committee, closing
 * TraceabilityMatrix row 22.
 */
object DisputeSla {

    const val DECISION_WINDOW_MILLIS: Long = 48L * 60 * 60 * 1000
    const val MAX_CONCURRENT_ESCALATED = 5
    const val MAX_AVG_RESPONSE_BUSINESS_DAYS = 5.0

    private val ZONE: ZoneId = ZoneId.of("Africa/Johannesburg")

    fun isPastWindow(openedAtMillis: Long, nowMillis: Long): Boolean =
        nowMillis - openedAtMillis > DECISION_WINDOW_MILLIS

    /**
     * The interim manual mechanism is deemed FAILED when either arm trips;
     * crossing it must trigger a logged founder-capacity review.
     */
    fun capacityThresholdCrossed(
        concurrentOpenPastWindow: Int,
        avgFounderResponseBusinessDays: Double?,
    ): Boolean =
        concurrentOpenPastWindow > MAX_CONCURRENT_ESCALATED ||
            (avgFounderResponseBusinessDays ?: 0.0) > MAX_AVG_RESPONSE_BUSINESS_DAYS

    /** Whole business days (Mon-Fri, SAST) between two instants, for the response-time arm. */
    fun businessDaysBetween(startMillis: Long, endMillis: Long): Int {
        if (endMillis <= startMillis) return 0
        var date: LocalDate = Instant.ofEpochMilli(startMillis).atZone(ZONE).toLocalDate()
        val end: LocalDate = Instant.ofEpochMilli(endMillis).atZone(ZONE).toLocalDate()
        var days = 0
        while (date.isBefore(end)) {
            date = date.plusDays(1)
            if (date.dayOfWeek != DayOfWeek.SATURDAY && date.dayOfWeek != DayOfWeek.SUNDAY) days++
        }
        return days
    }
}
