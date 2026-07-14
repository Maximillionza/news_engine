package com.minimoney.app.data.dispute

import com.minimoney.app.data.db.DisputeDao
import com.minimoney.app.data.db.DisputeEntity
import com.minimoney.app.data.db.TaskDao
import com.minimoney.app.domain.core.AppError
import com.minimoney.app.domain.core.AppResult
import com.minimoney.app.domain.core.Clock
import com.minimoney.app.domain.dispute.Dispute
import com.minimoney.app.domain.dispute.DisputeRepository
import com.minimoney.app.domain.dispute.DisputeSla
import com.minimoney.app.domain.dispute.DisputeStatus
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class DisputeRepositoryImpl @Inject constructor(
    private val disputeDao: DisputeDao,
    private val taskDao: TaskDao,
    private val clock: Clock,
) : DisputeRepository {

    override fun disputesFor(childId: Long): Flow<List<Dispute>> =
        disputeDao.forChild(childId).map { list -> list.map { it.toDomain() } }

    override suspend fun open(taskId: Long): AppResult<Long> {
        val task = taskDao.get(taskId) ?: return AppResult.Failure(AppError.Unknown())
        val id = disputeDao.insert(
            DisputeEntity(
                taskId = taskId,
                childId = task.childId,
                openedAtMillis = clock.nowMillis(),
                status = DisputeStatus.OPEN.name,
            ),
        )
        return AppResult.Success(id)
    }

    override suspend fun accept(disputeId: Long): AppResult<Unit> = resolve(disputeId, DisputeStatus.ACCEPTED)

    override suspend fun decline(disputeId: Long): AppResult<Unit> = resolve(disputeId, DisputeStatus.DECLINED)

    override suspend fun escalate(disputeId: Long): AppResult<Unit> {
        val dispute = disputeDao.get(disputeId) ?: return AppResult.Failure(AppError.Unknown())
        if (dispute.status != DisputeStatus.OPEN.name) return AppResult.Failure(AppError.Conflict)
        // Escalation is only valid past the 48h window — inside it, the
        // parent decision path (accept/decline) applies.
        if (!DisputeSla.isPastWindow(dispute.openedAtMillis, clock.nowMillis())) {
            return AppResult.Failure(AppError.Conflict)
        }
        disputeDao.resolve(disputeId, DisputeStatus.ESCALATED.name, null)
        return AppResult.Success(Unit)
    }

    override fun openPastWindowCount(nowMillis: Long): Flow<Int> =
        disputeDao.openOlderThanCount(nowMillis - DisputeSla.DECISION_WINDOW_MILLIS)

    private suspend fun resolve(disputeId: Long, status: DisputeStatus): AppResult<Unit> {
        val dispute = disputeDao.get(disputeId) ?: return AppResult.Failure(AppError.Unknown())
        if (dispute.status != DisputeStatus.OPEN.name) return AppResult.Failure(AppError.Conflict)
        disputeDao.resolve(disputeId, status.name, clock.nowMillis())
        return AppResult.Success(Unit)
    }
}

private fun DisputeEntity.toDomain() = Dispute(
    id = id,
    taskId = taskId,
    openedAtMillis = openedAtMillis,
    status = DisputeStatus.valueOf(status),
    resolvedAtMillis = resolvedAtMillis,
)
