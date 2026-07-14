package com.minimoney.app.domain.payslip

import com.minimoney.app.domain.core.AppResult
import kotlinx.coroutines.flow.Flow

interface PayslipRepository {

    fun payslipsFor(childId: Long): Flow<List<Payslip>>

    /**
     * Gathers all verified, not-yet-invoiced ledger entries for the child into
     * a new payslip. Fails if there is nothing to invoice.
     */
    suspend fun generate(childId: Long): AppResult<Long>

    /**
     * Parent-entered confirmation only — the actual payment happens entirely
     * outside MiniMoney via the parent's own banking app; no payment or
     * payment-instrument data is ever captured (BuildSpec §Data Model).
     */
    suspend fun confirmPaid(payslipId: Long): AppResult<Unit>

    /**
     * Applies a late-penalty step. The pilot/production cap is enforced HERE,
     * at the write level: a step that would push the payslip's penalty total
     * past the cap is clamped to the cap remainder, and rejected outright once
     * the cap is reached.
     */
    suspend fun applyLatePenalty(payslipId: Long, stepMbucks: Int): AppResult<Unit>
}
