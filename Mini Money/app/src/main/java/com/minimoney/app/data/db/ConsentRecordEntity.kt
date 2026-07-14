package com.minimoney.app.data.db

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Versioned, timestamped consent acceptance record — its own table, deliberately
 * not a column on any account entity (BuildSpec §Data Model: ConsentRecord is
 * "structurally separate ... from ParentAccount creation"). Append-only:
 * re-consent on a new document version inserts a new row, never updates one.
 * This is also one of the PII tables named for access-logging in the
 * incident-response constraint.
 */
@Entity(tableName = "consent_records")
data class ConsentRecordEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "parent_account_id") val parentAccountId: String,
    @ColumnInfo(name = "document_version") val documentVersion: String,
    @ColumnInfo(name = "accepted_at_epoch_millis") val acceptedAtEpochMillis: Long,
)
