package com.minimoney.app.data.db

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Transaction
import kotlinx.coroutines.flow.Flow

/** Result row for per-child GROUP BY aggregations (totals, counts). */
data class ChildCount(val childId: Long, val total: Int)

@Dao
interface ChildDao {
    @Insert
    suspend fun insert(child: ChildProfileEntity): Long

    @Query("SELECT COUNT(*) FROM child_profiles WHERE parent_account_id = :parentAccountId")
    suspend fun countFor(parentAccountId: String): Int

    @Query("SELECT * FROM child_profiles ORDER BY created_at")
    fun all(): Flow<List<ChildProfileEntity>>

    @Query("SELECT * FROM child_profiles WHERE id = :id")
    fun byId(id: Long): Flow<ChildProfileEntity?>

    @Query("SELECT * FROM child_profiles WHERE id = :id")
    suspend fun get(id: Long): ChildProfileEntity?

    @Query("UPDATE child_profiles SET budget_rand = :budgetRand WHERE id = :id")
    suspend fun setBudget(id: Long, budgetRand: Int)
}

@Dao
interface TaskDao {
    @Insert
    suspend fun insert(task: TaskEntity): Long

    @Query("SELECT * FROM tasks WHERE child_id = :childId ORDER BY created_at DESC")
    fun forChild(childId: Long): Flow<List<TaskEntity>>

    @Query("SELECT * FROM tasks WHERE id = :id")
    suspend fun get(id: Long): TaskEntity?

    /** Per-child count of tasks awaiting parent verification — the "{n} to verify" badge on Home. */
    @Query(
        "SELECT child_id AS childId, COUNT(*) AS total FROM tasks " +
            "WHERE status = 'COMPLETED' GROUP BY child_id",
    )
    fun pendingVerificationCounts(): Flow<List<ChildCount>>

    @Query("UPDATE tasks SET status = :status, completed_at = :completedAt WHERE id = :id")
    suspend fun setCompleted(id: Long, status: String, completedAt: Long)

    @Query("UPDATE tasks SET status = :status, verified_at = :verifiedAt WHERE id = :id")
    suspend fun setVerified(id: Long, status: String, verifiedAt: Long)

    @Query("UPDATE tasks SET status = :status WHERE id = :id")
    suspend fun setStatus(id: Long, status: String)
}

@Dao
interface LedgerDao {
    @Insert
    suspend fun insertMbuck(entry: MbuckLedgerEntryEntity): Long

    @Insert
    suspend fun insertMpoint(entry: MpointLedgerEntryEntity): Long

    @Query("SELECT * FROM mbuck_ledger WHERE child_id = :childId AND payslip_id IS NULL")
    suspend fun uninvoicedFor(childId: Long): List<MbuckLedgerEntryEntity>

    @Query("UPDATE mbuck_ledger SET payslip_id = :payslipId WHERE id IN (:entryIds)")
    suspend fun attachToPayslip(entryIds: List<Long>, payslipId: Long)

    @Query("SELECT COALESCE(SUM(amount_mbucks), 0) FROM mbuck_ledger WHERE child_id = :childId")
    fun totalMbucksFor(childId: Long): Flow<Int>

    /** Per-child earned totals since a timestamp — feeds the Home cards' month-to-date figures. */
    @Query(
        "SELECT child_id AS childId, COALESCE(SUM(amount_mbucks), 0) AS total " +
            "FROM mbuck_ledger WHERE earned_at >= :sinceMillis GROUP BY child_id",
    )
    fun mbucksPerChildSince(sinceMillis: Long): Flow<List<ChildCount>>

    @Query("SELECT COALESCE(SUM(amount_mpoints), 0) FROM mpoint_ledger WHERE child_id = :childId")
    fun totalMpointsFor(childId: Long): Flow<Int>
}

@Dao
interface PayslipDao {
    @Insert
    suspend fun insert(payslip: PayslipEntity): Long

    @Query("SELECT * FROM payslips WHERE child_id = :childId ORDER BY generated_at DESC")
    fun forChild(childId: Long): Flow<List<PayslipEntity>>

    @Query("SELECT * FROM payslips WHERE id = :id")
    suspend fun get(id: Long): PayslipEntity?

    @Query("UPDATE payslips SET status = :status, paid_confirmed_at = :confirmedAt WHERE id = :id")
    suspend fun setPaid(id: Long, status: String, confirmedAt: Long)

    @Insert
    suspend fun insertConfirmation(confirmation: PaymentConfirmationEntity)

    @Insert
    suspend fun insertPenalty(event: LatePenaltyEventEntity)

    @Query("SELECT COALESCE(SUM(amount_mbucks), 0) FROM late_penalty_events WHERE payslip_id = :payslipId")
    suspend fun penaltyTotalFor(payslipId: Long): Int

    @Query("SELECT COALESCE(SUM(amount_mbucks), 0) FROM late_penalty_events WHERE payslip_id = :payslipId")
    fun penaltyTotalFlowFor(payslipId: Long): Flow<Int>

    @Query("SELECT * FROM payslips WHERE status = 'GENERATED' AND generated_at < :cutoffMillis")
    suspend fun generatedOlderThan(cutoffMillis: Long): List<PayslipEntity>

    @Transaction
    @Query(
        "SELECT p.*, COALESCE((SELECT SUM(amount_mbucks) FROM late_penalty_events e " +
            "WHERE e.payslip_id = p.id), 0) AS penalty_mbucks " +
            "FROM payslips p WHERE p.child_id = :childId ORDER BY p.generated_at DESC",
    )
    fun withPenaltiesForChild(childId: Long): Flow<List<PayslipWithPenalty>>
}

data class PayslipWithPenalty(
    val id: Long,
    @androidx.room.ColumnInfo(name = "child_id") val childId: Long,
    @androidx.room.ColumnInfo(name = "generated_at") val generatedAtMillis: Long,
    @androidx.room.ColumnInfo(name = "earned_mbucks") val earnedMbucks: Int,
    val status: String,
    @androidx.room.ColumnInfo(name = "paid_confirmed_at") val paidConfirmedAtMillis: Long?,
    @androidx.room.ColumnInfo(name = "penalty_mbucks") val penaltyMbucks: Int,
)

@Dao
interface DisputeDao {
    @Insert
    suspend fun insert(dispute: DisputeEntity): Long

    @Query("SELECT * FROM disputes WHERE child_id = :childId ORDER BY opened_at DESC")
    fun forChild(childId: Long): Flow<List<DisputeEntity>>

    @Query("SELECT * FROM disputes WHERE id = :id")
    suspend fun get(id: Long): DisputeEntity?

    @Query("UPDATE disputes SET status = :status, resolved_at = :resolvedAt WHERE id = :id")
    suspend fun resolve(id: Long, status: String, resolvedAt: Long?)

    @Query("SELECT COUNT(*) FROM disputes WHERE status = 'OPEN' AND opened_at < :cutoffMillis")
    fun openOlderThanCount(cutoffMillis: Long): Flow<Int>
}

@Dao
interface ExamBonusDao {
    @Insert
    suspend fun insert(record: ExamBonusRecordEntity)

    @Query("SELECT * FROM exam_bonus_records WHERE child_id = :childId ORDER BY recorded_at DESC")
    fun forChild(childId: Long): Flow<List<ExamBonusRecordEntity>>
}
