package com.minimoney.app.data.db

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(tableName = "child_profiles")
data class ChildProfileEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "parent_account_id") val parentAccountId: String,
    @ColumnInfo(name = "display_name") val displayName: String,
    /** AgeBand enum name — three-tier model only. */
    @ColumnInfo(name = "age_band") val ageBand: String,
    /** Whole Rand. INTEGER by schema — no decimal column exists (BuildSpec §Data Model). */
    @ColumnInfo(name = "budget_rand") val budgetRand: Int?,
    @ColumnInfo(name = "created_at") val createdAtMillis: Long,
)

@Entity(tableName = "tasks", indices = [Index("child_id")])
data class TaskEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "child_id") val childId: Long,
    @ColumnInfo(name = "title") val title: String,
    @ColumnInfo(name = "earn_mode") val earnMode: String,
    @ColumnInfo(name = "earn_value") val earnValue: Int,
    /** Snapshot computed at creation; a later budget change never re-prices this task. */
    @ColumnInfo(name = "mbuck_value") val mbuckValue: Int,
    @ColumnInfo(name = "status") val status: String,
    @ColumnInfo(name = "created_at") val createdAtMillis: Long,
    @ColumnInfo(name = "completed_at") val completedAtMillis: Long? = null,
    @ColumnInfo(name = "verified_at") val verifiedAtMillis: Long? = null,
)

/**
 * EARNING EVENTS ONLY. There is deliberately no transfer, redemption, or
 * cash-out entity, column, or query anywhere in this schema — the structural
 * enforcement of Mbuck non-transferability the low money-transmitter-risk
 * finding is contingent on (BuildSpec §Data Model; LegalOpinion Q1). Any
 * future change to this REQUIRES the money-transmitter legal analysis to be
 * redone first — hard stop.
 */
@Entity(tableName = "mbuck_ledger", indices = [Index("child_id"), Index("payslip_id")])
data class MbuckLedgerEntryEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "child_id") val childId: Long,
    @ColumnInfo(name = "task_id") val taskId: Long,
    /** Whole-number INTEGER by schema — no decimal/sub-unit field exists on this entity. */
    @ColumnInfo(name = "amount_mbucks") val amountMbucks: Int,
    @ColumnInfo(name = "earned_at") val earnedAtMillis: Long,
    /** Set when swept into a payslip; null = not yet invoiced. */
    @ColumnInfo(name = "payslip_id") val payslipId: Long? = null,
)

/** Entirely separate ledger from Mbucks; written only when MPOINTS_ENABLED. */
@Entity(tableName = "mpoint_ledger", indices = [Index("child_id")])
data class MpointLedgerEntryEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "child_id") val childId: Long,
    @ColumnInfo(name = "task_id") val taskId: Long,
    @ColumnInfo(name = "amount_mpoints") val amountMpoints: Int,
    @ColumnInfo(name = "earned_at") val earnedAtMillis: Long,
)

@Entity(tableName = "payslips", indices = [Index("child_id")])
data class PayslipEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "child_id") val childId: Long,
    @ColumnInfo(name = "generated_at") val generatedAtMillis: Long,
    @ColumnInfo(name = "earned_mbucks") val earnedMbucks: Int,
    @ColumnInfo(name = "status") val status: String,
    @ColumnInfo(name = "paid_confirmed_at") val paidConfirmedAtMillis: Long? = null,
)

/** Parent-entered confirmation only; carries no payment-instrument data by design. */
@Entity(tableName = "payment_confirmations", indices = [Index("payslip_id")])
data class PaymentConfirmationEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "payslip_id") val payslipId: Long,
    @ColumnInfo(name = "confirmed_at") val confirmedAtMillis: Long,
)

/** Whole-Mbuck steps set directly (never percentage-derived); cap enforced at write. */
@Entity(tableName = "late_penalty_events", indices = [Index("payslip_id")])
data class LatePenaltyEventEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "payslip_id") val payslipId: Long,
    @ColumnInfo(name = "amount_mbucks") val amountMbucks: Int,
    @ColumnInfo(name = "applied_at") val appliedAtMillis: Long,
)

@Entity(tableName = "disputes", indices = [Index("task_id")])
data class DisputeEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "task_id") val taskId: Long,
    @ColumnInfo(name = "child_id") val childId: Long,
    @ColumnInfo(name = "opened_at") val openedAtMillis: Long,
    @ColumnInfo(name = "status") val status: String,
    @ColumnInfo(name = "resolved_at") val resolvedAtMillis: Long? = null,
)

/**
 * Exam-bonus hybrid: behavior checklist (primary) + self-reported grade
 * (secondary). NO Mbuck bonus-value calculation is specified for this entity
 * — if one is ever introduced, it must apply the truncation rule (BuildSpec
 * flags this unresolved; founder confirms scope before building). Gated
 * pre-pilot: build/QA with test data only until the child-development
 * specialist's motivation-probe review has occurred.
 */
@Entity(tableName = "exam_bonus_records", indices = [Index("child_id")])
data class ExamBonusRecordEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "child_id") val childId: Long,
    @ColumnInfo(name = "behavior_checklist_json") val behaviorChecklistJson: String,
    @ColumnInfo(name = "grade_input") val gradeInput: String?,
    @ColumnInfo(name = "recorded_at") val recordedAtMillis: Long,
)
