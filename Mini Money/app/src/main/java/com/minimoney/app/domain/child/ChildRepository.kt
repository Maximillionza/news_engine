package com.minimoney.app.domain.child

import com.minimoney.app.domain.core.AppResult
import kotlinx.coroutines.flow.Flow

interface ChildRepository {

    fun children(): Flow<List<ChildProfile>>

    fun child(childId: Long): Flow<ChildProfile?>

    /** Fails if the parent already has MAX_CHILDREN_PER_PARENT profiles. */
    suspend fun createChild(displayName: String, ageBand: AgeBand): AppResult<Long>

    /** Whole Rand only; the amount must already be a validated integer. */
    suspend fun setBudget(childId: Long, budgetRand: Int): AppResult<Unit>
}
