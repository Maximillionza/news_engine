package com.minimoney.app.domain.tasks

import com.minimoney.app.domain.core.AppResult
import kotlinx.coroutines.flow.Flow

interface TaskRepository {

    fun tasksFor(childId: Long): Flow<List<ChildTask>>

    /**
     * Computes and snapshots the Mbuck value at creation time: FIXED mode
     * stores earnValue directly (≥1 enforced); PERCENTAGE mode applies the
     * truncate-then-floor rule against the child's current budget.
     */
    suspend fun createTask(
        childId: Long,
        title: String,
        earnMode: EarnMode,
        earnValue: Int,
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
