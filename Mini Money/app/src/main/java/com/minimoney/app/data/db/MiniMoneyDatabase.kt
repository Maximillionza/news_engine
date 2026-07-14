package com.minimoney.app.data.db

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    entities = [
        ConsentRecordEntity::class,
        ChildProfileEntity::class,
        TaskEntity::class,
        MbuckLedgerEntryEntity::class,
        MpointLedgerEntryEntity::class,
        PayslipEntity::class,
        PaymentConfirmationEntity::class,
        LatePenaltyEventEntity::class,
        DisputeEntity::class,
        ExamBonusRecordEntity::class,
    ],
    version = 2,
    exportSchema = true,
)
abstract class MiniMoneyDatabase : RoomDatabase() {
    abstract fun consentDao(): ConsentDao
    abstract fun childDao(): ChildDao
    abstract fun taskDao(): TaskDao
    abstract fun ledgerDao(): LedgerDao
    abstract fun payslipDao(): PayslipDao
    abstract fun disputeDao(): DisputeDao
    abstract fun examBonusDao(): ExamBonusDao
}
