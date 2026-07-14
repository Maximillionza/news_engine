package com.minimoney.app.domain.dispute

import com.minimoney.app.domain.core.AppResult
import kotlinx.coroutines.flow.Flow

interface DisputeRepository {

    fun disputesFor(childId: Long): Flow<List<Dispute>>

    suspend fun open(taskId: Long): AppResult<Long>

    /** Parent decision inside the 48-hour window. */
    suspend fun accept(disputeId: Long): AppResult<Unit>
    suspend fun decline(disputeId: Long): AppResult<Unit>

    /** Past the window: moves to the interim manual founder-review queue. */
    suspend fun escalate(disputeId: Long): AppResult<Unit>

    /** Count of disputes currently open past the 48h window — capacity-threshold input. */
    fun openPastWindowCount(nowMillis: Long): Flow<Int>
}
