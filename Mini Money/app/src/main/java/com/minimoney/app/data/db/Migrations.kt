package com.minimoney.app.data.db

import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

/**
 * Explicit migrations — destructive fallback removed before any pilot family
 * enrolls, so no real household's ledger or consent history can ever be
 * dropped by a schema bump. SQL must match the exported schema JSONs in
 * app/schemas/ exactly.
 */

/** v1 (consent_records only) -> v2 (core mechanic tables). */
val MIGRATION_1_2 = object : Migration(1, 2) {
    override fun migrate(db: SupportSQLiteDatabase) {
        db.execSQL(
            "CREATE TABLE IF NOT EXISTS `child_profiles` (" +
                "`id` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, " +
                "`parent_account_id` TEXT NOT NULL, `display_name` TEXT NOT NULL, " +
                "`age_band` TEXT NOT NULL, `budget_rand` INTEGER, `created_at` INTEGER NOT NULL)",
        )
        db.execSQL(
            "CREATE TABLE IF NOT EXISTS `tasks` (" +
                "`id` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, `child_id` INTEGER NOT NULL, " +
                "`title` TEXT NOT NULL, `earn_mode` TEXT NOT NULL, `earn_value` INTEGER NOT NULL, " +
                "`mbuck_value` INTEGER NOT NULL, `status` TEXT NOT NULL, " +
                "`created_at` INTEGER NOT NULL, `completed_at` INTEGER, `verified_at` INTEGER)",
        )
        db.execSQL("CREATE INDEX IF NOT EXISTS `index_tasks_child_id` ON `tasks` (`child_id`)")
        db.execSQL(
            "CREATE TABLE IF NOT EXISTS `mbuck_ledger` (" +
                "`id` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, `child_id` INTEGER NOT NULL, " +
                "`task_id` INTEGER NOT NULL, `amount_mbucks` INTEGER NOT NULL, " +
                "`earned_at` INTEGER NOT NULL, `payslip_id` INTEGER)",
        )
        db.execSQL("CREATE INDEX IF NOT EXISTS `index_mbuck_ledger_child_id` ON `mbuck_ledger` (`child_id`)")
        db.execSQL("CREATE INDEX IF NOT EXISTS `index_mbuck_ledger_payslip_id` ON `mbuck_ledger` (`payslip_id`)")
        db.execSQL(
            "CREATE TABLE IF NOT EXISTS `mpoint_ledger` (" +
                "`id` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, `child_id` INTEGER NOT NULL, " +
                "`task_id` INTEGER NOT NULL, `amount_mpoints` INTEGER NOT NULL, `earned_at` INTEGER NOT NULL)",
        )
        db.execSQL("CREATE INDEX IF NOT EXISTS `index_mpoint_ledger_child_id` ON `mpoint_ledger` (`child_id`)")
        db.execSQL(
            "CREATE TABLE IF NOT EXISTS `payslips` (" +
                "`id` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, `child_id` INTEGER NOT NULL, " +
                "`generated_at` INTEGER NOT NULL, `earned_mbucks` INTEGER NOT NULL, " +
                "`status` TEXT NOT NULL, `paid_confirmed_at` INTEGER)",
        )
        db.execSQL("CREATE INDEX IF NOT EXISTS `index_payslips_child_id` ON `payslips` (`child_id`)")
        db.execSQL(
            "CREATE TABLE IF NOT EXISTS `payment_confirmations` (" +
                "`id` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, " +
                "`payslip_id` INTEGER NOT NULL, `confirmed_at` INTEGER NOT NULL)",
        )
        db.execSQL("CREATE INDEX IF NOT EXISTS `index_payment_confirmations_payslip_id` ON `payment_confirmations` (`payslip_id`)")
        db.execSQL(
            "CREATE TABLE IF NOT EXISTS `late_penalty_events` (" +
                "`id` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, " +
                "`payslip_id` INTEGER NOT NULL, `amount_mbucks` INTEGER NOT NULL, `applied_at` INTEGER NOT NULL)",
        )
        db.execSQL("CREATE INDEX IF NOT EXISTS `index_late_penalty_events_payslip_id` ON `late_penalty_events` (`payslip_id`)")
        db.execSQL(
            "CREATE TABLE IF NOT EXISTS `disputes` (" +
                "`id` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, `task_id` INTEGER NOT NULL, " +
                "`child_id` INTEGER NOT NULL, `opened_at` INTEGER NOT NULL, " +
                "`status` TEXT NOT NULL, `resolved_at` INTEGER)",
        )
        db.execSQL("CREATE INDEX IF NOT EXISTS `index_disputes_task_id` ON `disputes` (`task_id`)")
        db.execSQL(
            "CREATE TABLE IF NOT EXISTS `exam_bonus_records` (" +
                "`id` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, `child_id` INTEGER NOT NULL, " +
                "`behavior_checklist_json` TEXT NOT NULL, `grade_input` TEXT, `recorded_at` INTEGER NOT NULL)",
        )
        db.execSQL("CREATE INDEX IF NOT EXISTS `index_exam_bonus_records_child_id` ON `exam_bonus_records` (`child_id`)")
    }
}

/** v2 -> v3: PII access log (incident-response constraint, BuildSpec §Compliance). */
val MIGRATION_2_3 = object : Migration(2, 3) {
    override fun migrate(db: SupportSQLiteDatabase) {
        db.execSQL(
            "CREATE TABLE IF NOT EXISTS `access_log` (" +
                "`id` INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, " +
                "`table_name` TEXT NOT NULL, `row_ref` TEXT, " +
                "`action` TEXT NOT NULL, `at` INTEGER NOT NULL)",
        )
    }
}
