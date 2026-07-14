package com.minimoney.app.domain.payslip

enum class PayslipStatus { GENERATED, PAID }

data class Payslip(
    val id: Long,
    val childId: Long,
    val generatedAtMillis: Long,
    /** Sum of the earning entries attached to this payslip. Whole Mbucks. */
    val earnedMbucks: Int,
    /** Sum of late-penalty events. Whole Mbucks, capped — see LatePenaltyPolicy. */
    val penaltyMbucks: Int,
    val status: PayslipStatus,
    val paidConfirmedAtMillis: Long?,
) {
    val totalOwedMbucks: Int get() = earnedMbucks + penaltyMbucks
}

/**
 * Late-penalty caps, enforced at the ledger-write level, not just UI
 * (BuildSpec §Data Model, LatePenaltyEvent). Penalty step values are set
 * directly as whole Mbucks — confirmed NOT derived from any percentage, so
 * the truncation rule does not apply here.
 */
object LatePenaltyPolicy {
    const val PILOT_CAP_MBUCKS = 3
    const val PRODUCTION_CAP_MBUCKS = 7

    fun capMbucks(isPilot: Boolean): Int =
        if (isPilot) PILOT_CAP_MBUCKS else PRODUCTION_CAP_MBUCKS
}
