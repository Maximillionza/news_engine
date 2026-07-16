package com.minimoney.app.domain.tasks

import com.minimoney.app.domain.core.AppResult
import kotlinx.coroutines.flow.Flow

interface TaskRepository {

    fun tasksFor(childId: Long): Flow<List<ChildTask>>

    /**
     * Computes and snapshots the Mbuck value at creation time. `earnValue` is
     * the TOTAL monthly rate (whole Mbucks for FIXED, whole percent 1..100
     * for PERCENTAGE) or the preset's relative weight (TIER); `frequency`
     * spreads that total across its occurrences per month — and for TIER,
     * also selects which tier pool (daily/weekly/monthly) the weight is
     * shared against — then the truncate-then-floor rule is applied (see
     * MbuckCalculator). MONTHLY frequency (the default) behaves exactly as a
     * one-off task always has for FIXED/PERCENTAGE.
     */
    suspend fun createTask(
        childId: Long,
        title: String,
        earnMode: EarnMode,
        earnValue: Int,
        frequency: Frequency = Frequency.MONTHLY,
    ): AppResult<Long>

    /** Child-side completion marking. */
    suspend fun markCompleted(taskId: Long): AppResult<Unit>

    /**
     * Parent-side verification. Writes the MbuckLedgerEntry (earning events
     * only — the ledger has no transfer/redemption/cash-out path anywhere) and
     * the flat 10-Mpoint entry IF AND ONLY IF MPOINTS_ENABLED is on.
     */
    suspend fun verify(taskId: Long): AppResult<Unit>

    suspend fun markDisputed(taskId: Long): AppResult<Unit>
}
