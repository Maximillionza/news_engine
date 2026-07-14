package com.minimoney.app.data.child

import com.minimoney.app.data.auth.SessionStore
import com.minimoney.app.data.db.ChildDao
import com.minimoney.app.data.db.ChildProfileEntity
import com.minimoney.app.domain.child.AgeBand
import com.minimoney.app.domain.child.ChildProfile
import com.minimoney.app.domain.child.ChildRepository
import com.minimoney.app.domain.child.MAX_CHILDREN_PER_PARENT
import com.minimoney.app.domain.core.AppError
import com.minimoney.app.domain.core.AppResult
import com.minimoney.app.domain.core.Clock
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ChildRepositoryImpl @Inject constructor(
    private val childDao: ChildDao,
    private val sessionStore: SessionStore,
    private val clock: Clock,
    private val accessLogger: com.minimoney.app.data.db.AccessLogger,
) : ChildRepository {

    override fun children(): Flow<List<ChildProfile>> =
        childDao.all().map { list -> list.map { it.toDomain() } }

    override fun child(childId: Long): Flow<ChildProfile?> =
        childDao.byId(childId).map { it?.toDomain() }

    override suspend fun createChild(displayName: String, ageBand: AgeBand): AppResult<Long> {
        val session = sessionStore.session.first()
            ?: return AppResult.Failure(AppError.Unknown())
        if (displayName.isBlank()) return AppResult.Failure(AppError.Unknown())
        // 1 parent : up to 4 children — enforced at write, not just UI.
        if (childDao.countFor(session.parentAccountId) >= MAX_CHILDREN_PER_PARENT) {
            return AppResult.Failure(AppError.Conflict)
        }
        val id = childDao.insert(
            ChildProfileEntity(
                parentAccountId = session.parentAccountId,
                displayName = displayName.trim(),
                ageBand = ageBand.name,
                budgetRand = null,
                createdAtMillis = clock.nowMillis(),
            ),
        )
        // ChildProfile is a named PII table under the incident-response constraint.
        accessLogger.log("child_profiles", com.minimoney.app.data.db.PiiAction.WRITE, id.toString())
        return AppResult.Success(id)
    }

    override suspend fun setBudget(childId: Long, budgetRand: Int): AppResult<Unit> {
        // Whole-Rand, positive. The Int type is itself the schema-level
        // guarantee that no cents value can ever reach storage.
        if (budgetRand <= 0) return AppResult.Failure(AppError.Unknown())
        childDao.get(childId) ?: return AppResult.Failure(AppError.Unknown())
        childDao.setBudget(childId, budgetRand)
        accessLogger.log("child_profiles", com.minimoney.app.data.db.PiiAction.WRITE, childId.toString())
        return AppResult.Success(Unit)
    }
}

private fun ChildProfileEntity.toDomain() = ChildProfile(
    id = id,
    parentAccountId = parentAccountId,
    displayName = displayName,
    ageBand = AgeBand.valueOf(ageBand),
    budgetRand = budgetRand,
)
