package com.minimoney.app.data.tasks

import com.minimoney.app.data.db.ChildDao
import com.minimoney.app.data.db.LedgerDao
import com.minimoney.app.data.db.MbuckLedgerEntryEntity
import com.minimoney.app.data.db.MpointLedgerEntryEntity
import com.minimoney.app.data.db.TaskDao
import com.minimoney.app.data.db.TaskEntity
import com.minimoney.app.domain.core.AppError
import com.minimoney.app.domain.core.AppResult
import com.minimoney.app.domain.core.Clock
import com.minimoney.app.domain.core.MbuckCalculator
import com.minimoney.app.domain.flags.FeatureFlags
import com.minimoney.app.domain.child.AgeBand
import com.minimoney.app.domain.tasks.ChildTask
import com.minimoney.app.domain.tasks.EarnMode
import com.minimoney.app.domain.tasks.Frequency
import com.minimoney.app.domain.tasks.TaskRepository
import com.minimoney.app.domain.tasks.TaskStatus
import com.minimoney.app.domain.tasks.totalWeightFor
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

const val MPOINTS_PER_TASK = 10

@Singleton
class TaskRepositoryImpl @Inject constructor(
    private val taskDao: TaskDao,
    private val childDao: ChildDao,
    private val ledgerDao: LedgerDao,
    private val featureFlags: FeatureFlags,
    private val clock: Clock,
) : TaskRepository {

    override fun tasksFor(childId: Long): Flow<List<ChildTask>> =
        taskDao.forChild(childId).map { list -> list.map { it.toDomain() } }

    override suspend fun createTask(
        childId: Long,
        title: String,
        earnMode: EarnMode,
        earnValue: Int,
        frequency: Frequency,
    ): AppResult<Long> {
        if (title.isBlank()) return AppResult.Failure(AppError.Unknown())
        val child = childDao.get(childId) ?: return AppResult.Failure(AppError.Unknown())
        val occurrences = frequency.occurrencesPerMonth

        val mbuckValue = when (earnMode) {
            // FIXED: earnValue is the TOTAL monthly Mbucks; frequency spreads
            // it across occurrences (truncate, then floor 0 -> 1). The
            // 1-Mbuck minimum is enforced on the pre-split total: 0 is
            // rejected, not floored.
            EarnMode.FIXED -> {
                if (earnValue < 1) return AppResult.Failure(AppError.Unknown())
                MbuckCalculator.taskEarnValueFixed(earnValue, occurrences)
            }
            // PERCENTAGE: whole-number percent of the budget in effect NOW —
            // the value is snapshotted; later budget changes never re-price
            // this task. Truncate the monthly total, truncate the per-
            // occurrence split, then floor 0 -> 1.
            EarnMode.PERCENTAGE -> {
                if (earnValue !in 1..100) return AppResult.Failure(AppError.Unknown())
                val budget = child.budgetRand ?: return AppResult.Failure(AppError.Conflict)
                MbuckCalculator.taskEarnValue(budget, earnValue, occurrences)
            }
            // TIER: earnValue is the preset's relative weight within its
            // (ageBand, frequency) pool (Task Tier model). The pool's total
            // weight is summed from the current template catalog — if a
            // template later changes, only NEW tasks are affected; this
            // task's snapshot never re-prices.
            EarnMode.TIER -> {
                if (earnValue < 1) return AppResult.Failure(AppError.Unknown())
                val budget = child.budgetRand ?: return AppResult.Failure(AppError.Conflict)
                val ageBand = AgeBand.valueOf(child.ageBand)
                val totalWeight = totalWeightFor(ageBand, frequency)
                if (totalWeight < earnValue) return AppResult.Failure(AppError.Unknown())
                MbuckCalculator.tieredTaskEarnValue(
                    budget, frequency.tierBudgetSharePercent, earnValue, totalWeight, occurrences,
                )
            }
        }

        val id = taskDao.insert(
            TaskEntity(
                childId = childId,
                title = title.trim(),
                earnMode = earnMode.name,
                earnValue = earnValue,
                frequency = frequency.name,
                mbuckValue = mbuckValue,
                status = TaskStatus.ASSIGNED.name,
                createdAtMillis = clock.nowMillis(),
            ),
        )
        return AppResult.Success(id)
    }

    override suspend fun markCompleted(taskId: Long): AppResult<Unit> {
        val task = taskDao.get(taskId) ?: return AppResult.Failure(AppError.Unknown())
        if (task.status != TaskStatus.ASSIGNED.name) return AppResult.Failure(AppError.Conflict)
        taskDao.setCompleted(taskId, TaskStatus.COMPLETED.name, clock.nowMillis())
        return AppResult.Success(Unit)
    }

    override suspend fun verify(taskId: Long): AppResult<Unit> {
        val task = taskDao.get(taskId) ?: return AppResult.Failure(AppError.Unknown())
        if (task.status != TaskStatus.COMPLETED.name) return AppResult.Failure(AppError.Conflict)

        // Ledger-write-level minimum: a zero/negative Mbuck earning can never
        // be written, regardless of what upstream produced.
        check(task.mbuckValue >= 1) { "Mbuck earning below the 1-Mbuck minimum" }

        val now = clock.nowMillis()
        taskDao.setVerified(taskId, TaskStatus.VERIFIED.name, now)
        ledgerDao.insertMbuck(
            MbuckLedgerEntryEntity(
                childId = task.childId,
                taskId = task.id,
                amountMbucks = task.mbuckValue,
                earnedAtMillis = now,
            ),
        )
        // Flat 10 Mpoints per task — separate ledger, written only while the
        // FPB-gated flag is on (OFF at launch).
        if (featureFlags.mpointsEnabled.first()) {
            ledgerDao.insertMpoint(
                MpointLedgerEntryEntity(
                    childId = task.childId,
                    taskId = task.id,
                    amountMpoints = MPOINTS_PER_TASK,
                    earnedAtMillis = now,
                ),
            )
        }
        return AppResult.Success(Unit)
    }

    override suspend fun markDisputed(taskId: Long): AppResult<Unit> {
        taskDao.get(taskId) ?: return AppResult.Failure(AppError.Unknown())
        taskDao.setStatus(taskId, TaskStatus.DISPUTED.name)
        return AppResult.Success(Unit)
    }
}

private fun TaskEntity.toDomain() = ChildTask(
    id = id,
    childId = childId,
    title = title,
    earnMode = EarnMode.valueOf(earnMode),
    earnValue = earnValue,
    frequency = Frequency.valueOf(frequency),
    mbuckValue = mbuckValue,
    status = TaskStatus.valueOf(status),
    createdAtMillis = createdAtMillis,
    completedAtMillis = completedAtMillis,
    verifiedAtMillis = verifiedAtMillis,
)
