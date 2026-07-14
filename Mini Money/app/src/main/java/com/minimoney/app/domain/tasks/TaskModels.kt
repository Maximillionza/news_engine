package com.minimoney.app.domain.tasks

/** Per-task choice, not account-wide (BuildSpec §Data Model, Task — restored 2026-07-14). */
enum class EarnMode { FIXED, PERCENTAGE }

enum class TaskStatus { ASSIGNED, COMPLETED, VERIFIED, DISPUTED }

data class ChildTask(
    val id: Long,
    val childId: Long,
    val title: String,
    val earnMode: EarnMode,
    /** FIXED: whole Mbucks entered by parent. PERCENTAGE: whole-number percent 1..100. */
    val earnValue: Int,
    /**
     * The Mbuck amount, computed once at task-creation time from the budget
     * then in effect (PERCENTAGE mode, truncate-then-floor) or equal to
     * earnValue (FIXED). A later budget change never re-prices an existing task.
     */
    val mbuckValue: Int,
    val status: TaskStatus,
    val createdAtMillis: Long,
    val completedAtMillis: Long?,
    val verifiedAtMillis: Long?,
)
